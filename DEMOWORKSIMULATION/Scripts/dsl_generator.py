#!/usr/bin/env python3
"""DSL generator for OpenSearch Alerting monitors driven by config.ini.

Usage:
  python dsl_generator.py --config config.ini

This script reads monitor definitions from an INI file and writes JSON monitor
payloads into the `output_dir` (default: `monitors/`). It does not call the
OpenSearch API; it only generates and validates the JSON payloads.
"""

import argparse
import configparser
import json
import os
import re
from typing import Dict, Any


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.ini", help="Path to config.ini")
    return p.parse_args()


def build_query(match_field: str, match_value: str, match_type: str, window: str) -> Dict[str, Any]:
    """Build the `query` and `aggs` sections for a monitor input.

    match_type: 'match' (simple match), 'regex_or' (multiple OR regex values separated by |)
    window: e.g. '5m' or '1m' used for range gte: 'now-5m'
    """
    time_range = {"range": {"@timestamp": {"gte": f"now-{window}"}}}

    if match_type == "regex_or":
        # We'll use simple should/match queries for each token split by |.
        tokens = [t for t in match_value.split("|") if t]
        should = [{"match": {match_field: tok}} for tok in tokens]
        q = {"bool": {"must": [time_range], "should": should, "minimum_should_match": 1}}
    else:
        q = {"bool": {"must": [time_range, {"match": {match_field: match_value}}]}}

    # Aggregations: default to count of documents; caller can extend
    aggs = {"count": {"value_count": {"field": "_id"}}}
    return q, aggs


def build_monitor_payload(section: str, options: Dict[str, str]) -> Dict[str, Any]:
    name = options.get("name", section)
    monitor_type = options.get("monitor_type", "query_level_monitor")
    indices = [s.strip() for s in options.get("indices", "postgres*").split(",")]
    interval = int(options.get("interval", "1"))
    interval_unit = options.get("interval_unit", "MINUTES")
    window = options.get("window", "5m")

    match_field = options.get("match_field", "_raw")
    match_value = options.get("match_value", "ERROR")
    match_type = options.get("match_type", "match")

    q, aggs = build_query(match_field, match_value, match_type, window)

    # If by_host requested, add aggregation for host and top_hits
    if options.get("by_host", "false").lower() in ("1", "true", "yes"):
        aggs.update({
            "by_host": {
                "terms": {"field": "host.keyword", "size": int(options.get("by_host_size", "5"))},
                "aggs": {
                    "top_errors": {
                        "top_hits": {
                            "size": int(options.get("top_errors_size", "1")),
                            "_source": ["@timestamp", "_raw", "pid"],
                            "sort": [{"@timestamp": {"order": "desc"}}]
                        }
                    }
                }
            }
        })

    # If sample_size requested, add top_hits aggregation
    if int(options.get("sample_size", "0")) > 0:
        aggs["sample_logs"] = {
            "top_hits": {
                "size": int(options.get("sample_size", "3")),
                "_source": ["@timestamp", "_raw", "host", "pid"],
                "sort": [{"@timestamp": {"order": "desc"}}]
            }
        }

    input_search = {
        "search": {
            "indices": indices,
            "query": {"size": 0, "query": q, "aggs": aggs}
        }
    }

    threshold = int(options.get("threshold", "1"))
    severity = options.get("severity", "1")
    destination_id = options.get("destination_id", "")

    trigger = {
        "name": options.get("trigger_name", f"{name} Trigger"),
        "severity": str(severity),
        "condition": {
            "script": {
                "source": f"ctx.results[0].aggregations.count.value >= {threshold}",
                "lang": "painless",
            }
        },
        "actions": [
            {
                "name": options.get("action_name", "Send Alert"),
                "destination_id": destination_id,
                "subject_template": {"source": options.get("subject_template", name)},
                "message_template": {"source": options.get("message_template", "{{ctx.monitor.name}} triggered")},
            }
        ],
    }

    payload = {
        "type": "monitor",
        "name": name,
        "monitor_type": monitor_type,
        "enabled": options.get("enabled", "true").lower() in ("1", "true", "yes"),
        "schedule": {"period": {"interval": interval, "unit": interval_unit}},
        "inputs": [input_search],
        "triggers": [trigger],
    }

    return payload


def main():
    args = parse_args()
    cfg = configparser.ConfigParser()
    cfg.read(args.config)

    output_dir = cfg.get("general", "output_dir", fallback="monitors")
    os.makedirs(output_dir, exist_ok=True)

    generated = []
    for section in cfg.sections():
        if not section.startswith("monitor:"):
            continue
        name = section.split("monitor:", 1)[1]
        options = {k: v for k, v in cfg.items(section)}
        payload = build_monitor_payload(name, options)
        # Validate JSON serializable
        json_payload = json.dumps(payload, indent=2)

        filename = os.path.join(output_dir, f"monitor_{re.sub(r'[^a-zA-Z0-9_-]', '_', name)}.json")
        with open(filename, "w") as fh:
            fh.write(json_payload)
        print(f"Wrote monitor JSON: {filename}")
        generated.append(filename)

    print(f"Generated {len(generated)} monitor(s) in {output_dir}")


if __name__ == "__main__":
    main()
