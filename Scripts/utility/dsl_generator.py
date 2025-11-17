#!/usr/bin/env python3
"""Enhanced DSL generator for OpenSearch monitors.

Features:
- Support multiple match values (comma or pipe-separated)
- Support hostname wildcard patterns
- Optional mapping discovery from a local mapping JSON file
- Exception-safe painless trigger scripts (returns false on error)
- Generate HTML table email message templates

Usage:
  python dsl_generator.py --config config.ini

The script outputs monitor JSON files into the configured output directory.
"""

import argparse
import configparser
import json
import os
import re
from typing import Dict, Any, List


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.ini", help="Path to config.ini")
    return p.parse_args()


def load_mapping(mapping_file: str) -> Dict[str, Any]:
    if not mapping_file:
        return {}
    try:
        with open(mapping_file) as fh:
            return json.load(fh)
    except Exception:
        return {}


def find_field_for_raw(mapping: Dict[str, Any]) -> str:
    # Try common candidates
    candidates = ["_raw", "message", "log", "msg"]
    try:
        # mapping structure may vary; search recursively for fields
        props = {}
        def collect_props(m):
            if not isinstance(m, dict):
                return
            if 'properties' in m and isinstance(m['properties'], dict):
                for k, v in m['properties'].items():
                    props[k] = v
                    collect_props(v)
            else:
                for v in m.values():
                    if isinstance(v, dict):
                        collect_props(v)
        collect_props(mapping)
        for c in candidates:
            if c in props:
                return c
    except Exception:
        pass
    return "_raw"


def build_match_clauses(field: str, values: List[str]) -> List[Dict[str, Any]]:
    clauses = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        # If value looks like regex with |, let caller decide, here we use match
        clauses.append({"match": {field: v}})
    return clauses


def hostname_clause(field: str, pattern: str) -> Dict[str, Any]:
    # If pattern contains * or ?, use wildcard on keyword field
    if '*' in pattern or '?' in pattern:
        # prefer keyword
        keyword = f"{field}.keyword" if not field.endswith('.keyword') else field
        return {"wildcard": {keyword: pattern}}
    # exact term
    return {"term": {field: {"value": pattern}}}


def build_query(match_field: str, match_values: List[str], window: str, host_field: str = None, host_pattern: str = None) -> Dict[str, Any]:
    time_range = {"range": {"@timestamp": {"gte": f"now-{window}"}}}

    should = build_match_clauses(match_field, match_values)
    must = [time_range]
    if should:
        bool_q = {"must": must, "should": should, "minimum_should_match": 1}
    else:
        bool_q = {"must": must}

    if host_field and host_pattern:
        must.append(hostname_clause(host_field, host_pattern))

    return {"bool": bool_q}


def build_aggregations(options: Dict[str, str]) -> Dict[str, Any]:
    aggs = {"count": {"value_count": {"field": "_id"}}}
    if options.get("by_host", "false").lower() in ("1", "true", "yes"):
        aggs["by_host"] = {
            "terms": {"field": "host.keyword", "size": int(options.get("by_host_size", "5"))},
            "aggs": {
                "top_errors": {
                    "top_hits": {
                        "size": int(options.get("top_errors_size", "2")),
                        "_source": ["@timestamp", "_raw", "pid"],
                        "sort": [{"@timestamp": {"order": "desc"}}]
                    }
                }
            }
        }

    if int(options.get("sample_size", "0")) > 0:
        aggs["sample_logs"] = {
            "top_hits": {
                "size": int(options.get("sample_size", "3")),
                "_source": ["@timestamp", "_raw", "host", "pid"],
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        }
    return aggs


def build_safe_script(threshold: int, agg_name: str = "count") -> Dict[str, Any]:
    # Return a painless script that returns false on exception and otherwise evaluates the condition
    src = (
        "try {\n"
        f"  def v = ctx.results[0].aggregations.{agg_name}.value;\n"
        f"  return v >= {threshold};\n"
        "} catch (Exception e) {\n"
        "  return false;\n"
        "}"
    )
    return {"script": {"source": src, "lang": "painless"}}


def html_table_template(agg_name: str = "count", include_samples: bool = True) -> str:
    # Build a simple HTML table template using Mustache variables
    header = (
        "<h2>PostgreSQL Alert: {{ctx.monitor.name}}</h2>\n"
        "<table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse'>\n"
        "  <tr><th>Severity</th><th>Count</th><th>Time</th></tr>\n"
        "  <tr>\n"
        "    <td>{{ctx.trigger.severity}}</td>\n"
        f"    <td>{{{{ctx.results[0].aggregations.{agg_name}.value}}}}</td>\n"
        "    <td>{{ctx.trigger.triggered_time}}</td>\n"
        "  </tr>\n"
        "</table>\n"
    )
    if include_samples:
        samples = (
            "<h3>Sample Logs</h3>\n"
            "<ul>\n"
            "{{#ctx.results[0].aggregations.sample_logs.hits.hits}}\n"
            "  <li>[{{_source.@timestamp}}] {{{{_source._raw}}}}</li>\n"
            "{{/ctx.results[0].aggregations.sample_logs.hits.hits}}\n"
            "</ul>\n"
        )
        return header + samples
    return header


def build_monitor_payload(name: str, options: Dict[str, str], mapping: Dict[str, Any]) -> Dict[str, Any]:
    indices = [s.strip() for s in options.get("indices", "postgres*").split(",")]
    interval = int(options.get("interval", "5"))
    interval_unit = options.get("interval_unit", "MINUTES")
    window = options.get("window", "5m")

    # resolve match_field via mapping if requested
    match_field = options.get("match_field") or find_field_for_raw(mapping)

    # parse match values: support comma or pipe
    raw_vals = options.get("match_value", "ERROR")
    if '|' in raw_vals and ',' not in raw_vals:
        match_values = [v for v in raw_vals.split('|') if v]
    else:
        match_values = [v for v in re.split('[,;]', raw_vals) if v]

    host_field = options.get("host_field", "host.name")
    host_pattern = options.get("host_pattern", None)

    q = build_query(match_field, match_values, window, host_field if host_pattern else None, host_pattern)
    aggs = build_aggregations(options)

    input_search = {"search": {"indices": indices, "query": {"size": 0, "query": q, "aggs": aggs}}}

    threshold = int(options.get("threshold", "1"))
    severity = options.get("severity", "1")
    destination_id = options.get("destination_id", "")

    trigger_condition = build_safe_script(threshold, agg_name="count")

    # Build HTML message template
    html_msg = html_table_template(agg_name="count", include_samples=(int(options.get("sample_size", "0")) > 0))

    trigger = {
        "name": options.get("trigger_name", f"{name} trigger"),
        "severity": str(severity),
        "condition": trigger_condition,
        "actions": [
            {
                "name": options.get("action_name", "Send Alert"),
                "destination_id": destination_id,
                "subject_template": {"source": options.get("subject_template", name)},
                "message_template": {"source": html_msg, "lang": "mustache"},
                "throttle_enabled": options.get("throttle_enabled", "false").lower() in ("1", "true", "yes")
            }
        ]
    }

    payload = {
        "type": "monitor",
        "name": name,
        "monitor_type": options.get("monitor_type", "query_level_monitor"),
        "enabled": options.get("enabled", "true").lower() in ("1", "true", "yes"),
        "schedule": {"period": {"interval": interval, "unit": interval_unit}},
        "inputs": [input_search],
        "triggers": [{"query_level_trigger": trigger}]
    }
    return payload


def main():
    args = parse_args()
    cfg = configparser.ConfigParser()
    cfg.read(args.config)

    mapping = load_mapping(cfg.get("general", "mapping_file", fallback=""))

    output_dir = cfg.get("general", "output_dir", fallback="monitors")
    os.makedirs(output_dir, exist_ok=True)

    generated = []
    for section in cfg.sections():
        if not section.startswith("monitor:"):
            continue
        mon_name = section.split("monitor:", 1)[1]
        options = {k: v for k, v in cfg.items(section)}
        payload = build_monitor_payload(mon_name, options, mapping)
        filename = os.path.join(output_dir, f"monitor_{re.sub(r'[^a-zA-Z0-9_-]', '_', mon_name)}.json")
        with open(filename, "w") as fh:
            json.dump(payload, fh, indent=2)
        print(f"Wrote: {filename}")
        generated.append(filename)

    print(f"Generated {len(generated)} monitors in {output_dir}")


if __name__ == '__main__':
    main()
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChannelConfig:
    name: str
    description: str
    channel_type: str
    sender: str
    default_recipients: List[str]
    last_updated: str
    destination_id: Optional[str] = None  # OpenSearch destination identifier (if available)


def _base_action_message(channel: ChannelConfig, index: str) -> str:
    recipients = ", ".join(channel.default_recipients)
    return (
        f"Name: Panic & FATAL Error Monitor\n"
        f"Description: Filters panic/fatal text from error logs and emails the team.\n"
        f"Channel name: {channel.name}\n"
        f"Channel type: {channel.channel_type}\n"
        f"Sender: {channel.sender}\n"
        f"Recipients: {recipients}\n"
        f"Last updated: {channel.last_updated}\n"
        f"Index: {index}\n"
        "Alert fires when any log line contains panic or fatal text.\n"
        "Recent findings:\n"
        "{{#ctx.results.0.hits.hits}}\n"
        "- {{_source.@timestamp}} :: {{_source.message}}"
        "{{/ctx.results.0.hits.hits}}\n"
    )


def build_panic_fatal_email_monitor(
    channel: ChannelConfig,
    index: str,
    schedule_interval_minutes: int = 5,
) -> Dict:
    """
    Create an OpenSearch Alerting monitor DSL for panic/fatal detection routed to the given channel.
    """
    query = {
        "size": 5,
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"message": "panic"}},
                    {"match_phrase": {"message": "PANIC"}},
                    {"match_phrase": {"message": "fatal"}},
                    {"match_phrase": {"message": "FATAL"}},
                ],
                "minimum_should_match": 1,
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": ["@timestamp", "message", "level", "_raw"],
    }

    action = {
        "name": f"Email {channel.name}",
        "destination_id": channel.destination_id or channel.name,
        "throttle_enabled": False,
        "subject_template": {"source": "[Alert] Panic/FATAL errors detected"},
        "message_template": {"source": _base_action_message(channel, index)},
    }

    monitor = {
        "name": "panic_fatal_email_monitor",
        "type": "monitor",
        "enabled": True,
        "enabled_time": 0,
        "schedule": {"period": {"interval": schedule_interval_minutes, "unit": "MINUTES"}},
        "inputs": [{"search": {"indices": [index], "query": query}}],
        "triggers": [
            {
                "name": "panic_fatal_trigger",
                "severity": "1",
                "condition": {
                    "script": {"source": "return ctx.results[0].hits.total.value > 0", "lang": "painless"}
                },
                "actions": [action],
            }
        ],
    }

    return monitor
