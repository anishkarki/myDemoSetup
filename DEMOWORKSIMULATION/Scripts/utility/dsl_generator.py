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
        # Heuristics: if value looks like a regex, use a regexp clause; otherwise use match_phrase
        is_regex = False
        if any(x in v for x in ['.*', '(', ')', '|', '^', '$', '[', ']']):
            is_regex = True
        if is_regex:
            # regexp clause uses the provided pattern
            clauses.append({"regexp": {field: {"value": v}}})
        else:
            # use match_phrase to prefer exact token sequences
            clauses.append({"match_phrase": {field: v}})
    return clauses


def hostname_clause(field: str, pattern: str) -> Dict[str, Any]:
    # If pattern contains * or ?, use wildcard on keyword field
    if '*' in pattern or '?' in pattern:
        # prefer keyword
        keyword = f"{field}.keyword" if not field.endswith('.keyword') else field
        return {"wildcard": {keyword: pattern}}
    # exact term
    return {"term": {field: {"value": pattern}}}


def build_host_filter(field: str, patterns: List[str]) -> Dict[str, Any]:
    """Build a filter for one or more hostname patterns.
    
    If multiple patterns, returns a 'should' clause with wildcards/terms.
    If single pattern, returns the clause directly.
    """
    if not patterns:
        return None
    
    clauses = [hostname_clause(field, p.strip()) for p in patterns if p.strip()]
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    # multiple patterns: use should with minimum_should_match=1
    return {"bool": {"should": clauses, "minimum_should_match": 1}}


def build_query(match_field: str, match_values: List[str], window: str, host_field: str = None, host_patterns: List[str] = None) -> Dict[str, Any]:
    time_range = {"range": {"@timestamp": {"gte": f"now-{window}"}}}

    should = build_match_clauses(match_field, match_values)
    must = [time_range]
    if should:
        bool_q = {"must": must, "should": should, "minimum_should_match": 1}
    else:
        bool_q = {"must": must}

    if host_field and host_patterns:
        host_filter = build_host_filter(host_field, host_patterns)
        if host_filter:
            must.append(host_filter)

    return {"bool": bool_q}


def build_aggregations(options: Dict[str, str]) -> Dict[str, Any]:
    aggs = {"count": {"value_count": {"field": "_id"}}}
    # Helper to interpret sample sizes: allow 'all' to request a large cap
    def parse_sample_size(val: str, default: int) -> int:
        if not val:
            return default
        try:
            if isinstance(val, str) and val.lower() == 'all':
                return 10000
            return int(val)
        except Exception:
            return default

    sample_size_global = parse_sample_size(options.get("sample_size", "0"), 0)
    sample_size_per_host = parse_sample_size(options.get("sample_size_per_host", options.get("sample_size", "0")), 0)

    # by_host aggregation (optional)
    if options.get("by_host", "false").lower() in ("1", "true", "yes") or int(options.get("per_host_threshold", "0")) > 0:
        host_field = options.get("host_field", "host")
        host_keyword = host_field if host_field.endswith('.keyword') else f"{host_field}.keyword"
        by_host = {
            "terms": {"field": host_keyword, "size": int(options.get("by_host_size", "5"))},
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

        # If per-host error threshold is requested, add nested by_error terms aggregation
        if int(options.get("per_host_threshold", "0")) > 0:
            # choose the field to bucket errors on; prefer match_field if passed in options
            match_field = options.get("match_field", "_raw")
            error_field_keyword = match_field if match_field.endswith('.keyword') else f"{match_field}.keyword"
            by_host["aggs"]["by_error"] = {
                "terms": {"field": error_field_keyword, "size": int(options.get("by_error_size", "10"))}
            }

        # If user requested per-host samples (or global samples) add a top_hits under each host bucket
        if sample_size_per_host > 0:
            by_host["aggs"]["host_samples"] = {
                "top_hits": {
                    "size": sample_size_per_host,
                    "_source": ["@timestamp", "_raw", "pid", "host"],
                    "sort": [{"@timestamp": {"order": "desc"}}]
                }
            }

        aggs["by_host"] = by_host

    # global sample logs (not grouped by host)
    if sample_size_global > 0:
        aggs["sample_logs"] = {
            "top_hits": {
                "size": sample_size_global,
                "_source": ["@timestamp", "_raw", "host", "pid"],
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        }
    return aggs


def build_safe_script(threshold: int, agg_name: str = "count", per_host_threshold: int = 0) -> Dict[str, Any]:
    # Return a painless script that returns false on exception and otherwise evaluates the condition.
    # If per_host_threshold > 0, the script scans nested by_host.by_error buckets for counts >= threshold.
    if per_host_threshold and per_host_threshold > 0:
        src = (
            "try {\n"
            "  def hosts = ctx.results[0].aggregations.by_host.buckets;\n"
            "  for (h in hosts) {\n"
            "    if (h.containsKey('by_error')) {\n"
            "      for (e in h.by_error.buckets) {\n"
            f"        if (e.doc_count >= {per_host_threshold}) return true;\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  return false;\n"
            "} catch (Exception e) {\n"
            "  return false;\n"
            "}"
        )
        return {"script": {"source": src, "lang": "painless"}}

    # default path: check single aggregation value
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
            "  <li>[{{_source.@timestamp}}] {{{{_source._raw}}}</li>\n"
            "{{/ctx.results[0].aggregations.sample_logs.hits.hits}}\n"
            "</ul>\n"
        )
        return header + samples
    return header


def html_grouped_by_host_template(include_hosts: bool = True, include_samples_per_host: bool = True) -> str:
    """Build an HTML Mustache template grouping results by host and listing logs per host.

    The template expects `ctx.results[0].aggregations.by_host.buckets` to exist and optionally
    `top_errors` or `host_samples` inside each host bucket.
    """
    tpl = (
        "<h2>PostgreSQL Alert: {{ctx.monitor.name}}</h2>\n"
        "<p>Severity: {{ctx.trigger.severity}} — Time: {{ctx.trigger.triggered_time}}</p>\n"
        "<h3>Summary</h3>\n"
        "<table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse'>\n"
        "  <tr><th>Host</th><th>Count</th></tr>\n"
        "  {{#ctx.results[0].aggregations.by_host.buckets}}\n"
        "    <tr><td>{{key}}</td><td>{{doc_count}}</td></tr>\n"
        "  {{/ctx.results[0].aggregations.by_host.buckets}}\n"
        "</table>\n"
    )

    if include_samples_per_host:
        tpl += (
            "<h3>Logs Grouped By Host</h3>\n"
            "{{#ctx.results[0].aggregations.by_host.buckets}}\n"
            "  <h4>Host: {{key}} ({{doc_count}})</h4>\n"
            "  <table border=1 cellpadding=6 cellspacing=0 style='border-collapse:collapse;width:100%'>\n"
            "    <tr><th>Time</th><th>Log</th></tr>\n"
            "    {{#top_errors.hits.hits}}\n"
            "      <tr><td>{{_source.@timestamp}}</td><td>{{{_source._raw}}}</td></tr>\n"
            "    {{/top_errors.hits.hits}}\n"
            "    {{#host_samples.hits.hits}}\n"
            "      <tr><td>{{_source.@timestamp}}</td><td>{{{_source._raw}}}</td></tr>\n"
            "    {{/host_samples.hits.hits}}\n"
            "  </table>\n"
            "{{/ctx.results[0].aggregations.by_host.buckets}}\n"
        )

    return tpl


def build_monitor_payload(name: str, options: Dict[str, str], mapping: Dict[str, Any]) -> Dict[str, Any]:
    indices = [s.strip() for s in options.get("indices", "postgres*").split(",")]
    interval = int(options.get("interval", "5"))
    interval_unit = options.get("interval_unit", "MINUTES")
    window = options.get("window", "5m")

    # resolve match_field via mapping if requested
    # If user prefers structured error code fields, allow opting into `error.code` (or similar)
    if options.get("use_structured_code", "false").lower() in ("1", "true", "yes"):
        # prefer a standard structured field name for SQLSTATE-like codes
        # common names: error.code, sqlstate, sql_state, code
        # We default to `error.code` but this can be overridden explicitly with match_field
        match_field = options.get("match_field") or "error.code"
    else:
        match_field = options.get("match_field") or find_field_for_raw(mapping)

    # parse match values: support comma or pipe, but preserve regex patterns as single value
    raw_vals = options.get("match_value", "ERROR")

    # Allow shorthand expansion: `match_value = highest|medium|normal` will load
    # precomputed regexes from `Scripts/utility/pgsql_errcode_regexes.json`.
    shorthand = raw_vals.strip().lower()
    if shorthand in ("highest", "medium", "normal"):
        try:
            with open('Scripts/utility/pgsql_errcode_regexes.json', 'r', encoding='utf-8') as fh:
                jr = json.load(fh)
            if shorthand in jr and jr[shorthand]:
                raw_vals = jr[shorthand]
                match_type_opt = 'regex'
            else:
                match_type_opt = options.get('match_type', '').lower()
        except Exception:
            match_type_opt = options.get('match_type', '').lower()
    else:
        match_type_opt = options.get('match_type', '').lower()

    # Heuristic: detect if the value is a regex pattern by presence of regex metacharacters
    has_regex_marker = bool(re.search(r'[.*()|\[\]^$\\]', raw_vals))
    if match_type_opt.startswith("regex") or has_regex_marker:
        # Single regex pattern
        match_values = [raw_vals.strip()]
    elif ',' in raw_vals:
        # Comma-separated list of literals (or regexes, but not combined)
        match_values = [v.strip() for v in raw_vals.split(',') if v.strip()]
    elif '|' in raw_vals:
        # Pipe-separated (for literals like FATAL|PANIC without ())
        match_values = [v.strip() for v in raw_vals.split('|') if v.strip()]
    else:
        match_values = [raw_vals.strip()]

    host_field = options.get("host_field", "host.name")
    host_pattern_str = options.get("host_pattern", None)
    # Parse host patterns (comma or semicolon separated)
    # allow comma, semicolon or pipe as separators for multiple host patterns
    host_patterns = [p.strip() for p in re.split('[,;|]', host_pattern_str) if p.strip()] if host_pattern_str else None

    q = build_query(match_field, match_values, window, host_field if host_patterns else None, host_patterns)
    # determine if per-host error threshold behavior is requested
    per_host_threshold = int(options.get("per_host_threshold", "0"))
    aggs = build_aggregations(options)

    input_search = {"search": {"indices": indices, "query": {"size": 0, "query": q, "aggs": aggs}}}

    threshold = int(options.get("threshold", "1"))
    severity = options.get("severity", "1")
    destination_id = options.get("destination_id", "")

    # Build trigger condition: if per_host_threshold set, generate script to scan nested buckets
    if per_host_threshold > 0:
        trigger_condition = build_safe_script(threshold=threshold, agg_name="count", per_host_threshold=per_host_threshold)
    else:
        trigger_condition = build_safe_script(threshold, agg_name="count")

    # Build HTML message template
    by_host_enabled = options.get("by_host", "false").lower() in ("1", "true", "yes") or per_host_threshold > 0
    include_samples_global = (options.get("sample_size", "0").lower() == 'all') or (int(options.get("sample_size", "0")) > 0)
    include_samples_per_host = (options.get("sample_size_per_host") and options.get("sample_size_per_host").lower() == 'all') or (int(options.get("sample_size_per_host", options.get("sample_size", "0"))) > 0)

    if by_host_enabled:
        # Use grouped-by-host template when results are bucketed by host
        html_msg = html_grouped_by_host_template(include_hosts=True, include_samples_per_host=include_samples_per_host)
    else:
        html_msg = html_table_template(agg_name="count", include_samples=include_samples_global)

    # Build throttle settings if enabled
    throttle_enabled = options.get("throttle_enabled", "false").lower() in ("1", "true", "yes")
    throttle_duration_mins = int(options.get("throttle_duration_minutes", "10"))

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
                "throttle_enabled": throttle_enabled,
                "throttle": {
                    "value": throttle_duration_mins,
                    "unit": "MINUTES"
                } if throttle_enabled else None
            }
        ]
    }
    # Remove throttle key if not enabled
    if not throttle_enabled:
        trigger["actions"][0].pop("throttle", None)

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
