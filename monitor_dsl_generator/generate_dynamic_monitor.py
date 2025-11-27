#!/usr/bin/env python3
"""
Dynamic OpenSearch Monitor Generator
Generates a monitor JSON based on CLI arguments for host, index, and dynamic filters.
"""

import argparse
import json
import sys

def create_monitor(name, indices, host_name, filters, field="message", schedule_interval=1):
    # Base Monitor Structure
    monitor = {
        "type": "monitor",
        "name": name,
        "enabled": True,
        "schedule": {
            "period": {
                "interval": schedule_interval,
                "unit": "MINUTES"
            }
        },
        "inputs": [{
            "search": {
                "indices": indices,
                "query": {
                    "size": 0,
                    "query": {
                        "bool": {
                            "filter": [],
                            "should": [],
                            "minimum_should_match": 1
                        }
                    }
                }
            }
        }],
        "triggers": [
            {
                "name": "Pattern Detected",
                "severity": "1",
                "condition": {
                    "script": {
                        "source": "ctx.results[0].hits.total.value > 0",
                        "lang": "painless"
                    }
                },
                "actions": []
            }
        ]
    }

    # 1. Add Time Range Filter (Look back 'interval' minutes)
    monitor["inputs"][0]["search"]["query"]["query"]["bool"]["filter"].append({
        "range": {
            "@timestamp": {
                "gte": f"now-{schedule_interval}m",
                "lte": "now"
            }
        }
    })

    # 2. Add Host Filter (if provided)
    if host_name:
        monitor["inputs"][0]["search"]["query"]["query"]["bool"]["filter"].append({
            "term": {
                "host.name.keyword": host_name
            }
        })

    # 3. Add Dynamic Filters
    # These are added to 'should' clause. At least one must match (minimum_should_match=1).
    for f in filters:
        # Check if the filter looks like a raw JSON object (advanced usage)
        if f.strip().startswith("{") and f.strip().endswith("}"):
            try:
                custom_query = json.loads(f)
                monitor["inputs"][0]["search"]["query"]["query"]["bool"]["should"].append(custom_query)
                continue
            except json.JSONDecodeError:
                pass # Not valid JSON, treat as string

        # Heuristic: If it contains wildcards (* or ?), use wildcard query
        if "*" in f or "?" in f:
            monitor["inputs"][0]["search"]["query"]["query"]["bool"]["should"].append({
                "wildcard": {
                    field: {
                        "value": f,
                        "case_insensitive": True
                    }
                }
            })
        else:
            # Default: Match Phrase (exact sequence of words)
            monitor["inputs"][0]["search"]["query"]["query"]["bool"]["should"].append({
                "match_phrase": {
                    field: f
                }
            })

    return monitor

def main():
    parser = argparse.ArgumentParser(
        description="Generate an OpenSearch Monitor JSON with dynamic filters.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("--name", required=True, help="Name of the monitor")
    parser.add_argument("--index", required=True, nargs='+', help="Index pattern(s) to query (e.g. patronidata)")
    parser.add_argument("--host", help="Hostname to filter by (host.name.keyword)")
    parser.add_argument("--filter", action='append', required=True, 
                        help="Log pattern to search for.\n"
                             " - Supports wildcards: 'Error*'\n"
                             " - Supports phrases: 'I am the Leader'\n"
                             " - Supports raw JSON DSL: '{\"term\": ...}'")
    parser.add_argument("--field", default="message", help="Field to search in (default: message)")
    parser.add_argument("--interval", type=int, default=1, help="Schedule interval in minutes (default: 1)")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    try:
        monitor_json = create_monitor(
            name=args.name,
            indices=args.index,
            host_name=args.host,
            filters=args.filter,
            field=args.field,
            schedule_interval=args.interval
        )

        output_str = json.dumps(monitor_json, indent=2)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_str)
            print(f"Successfully generated monitor: {args.output}")
        else:
            print(output_str)

    except Exception as e:
        print(f"Error generating monitor: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
