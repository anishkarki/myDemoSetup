#!/usr/bin/env python3
"""
Fetch log context around a specific keyword event.
1. Searches for a keyword (e.g., "FATAL", "failover").
2. For each occurrence, fetches all logs from that host within +/- 1 minute.
3. Generates a consolidated report.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import requests
from dateutil import parser as date_parser

# Default OpenSearch config
DEFAULT_HOST = "100.80.115.61"
DEFAULT_PORT = 19200
DEFAULT_INDEX = "patronidata"

def search_triggers(host: str, port: int, index: str, keyword: str, start: str, end: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Find log entries containing the keyword."""
    url = f"http://{host}:{port}/{index}/_search"
    
    query = {
        "query": {
            "bool": {
                "must": [
                    { "match_phrase": { "_raw": keyword } },
                    { "range": { "@timestamp": { "gte": start, "lte": end } } }
                ]
            }
        },
        "size": limit,
        "sort": [{ "@timestamp": { "order": "desc" } }]
    }
    
    # Add host filter if provided and not wildcard
    if "*" not in host and host != "all":
         # This logic might need adjustment depending on how the user passes the host arg for the *search* vs the *filter*
         # For now, we'll assume the user might want to search across all hosts or a specific one.
         pass 

    try:
        resp = requests.post(url, json=query, timeout=10)
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])
    except Exception as e:
        print(f"Error searching triggers: {e}", file=sys.stderr)
        return []

def fetch_context(host_ip: str, port: int, index: str, target_host: str, timestamp_str: str, window_seconds: int = 60) -> List[Dict[str, Any]]:
    """Fetch logs around a specific timestamp for a specific host."""
    url = f"http://{host_ip}:{port}/{index}/_search"
    
    try:
        ts = date_parser.parse(timestamp_str)
        start_ts = (ts - timedelta(seconds=window_seconds)).isoformat()
        end_ts = (ts + timedelta(seconds=window_seconds)).isoformat()
    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}", file=sys.stderr)
        return []

    query = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "host.name": target_host } },
                    { "range": { "@timestamp": { "gte": start_ts, "lte": end_ts } } }
                ]
            }
        },
        "size": 500,
        "sort": [{ "@timestamp": { "order": "asc" } }]
    }

    try:
        resp = requests.post(url, json=query, timeout=10)
        resp.raise_for_status()
        return resp.json().get("hits", {}).get("hits", [])
    except Exception as e:
        print(f"Error fetching context: {e}", file=sys.stderr)
        return []

def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch log context around keywords.")
    parser.add_argument("keyword", help="The keyword to trigger the context fetch (e.g., 'FATAL')")
    parser.add_argument("--host", default=DEFAULT_HOST, help="OpenSearch host IP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="OpenSearch port")
    parser.add_argument("--index", default=DEFAULT_INDEX, help="Index pattern")
    parser.add_argument("--start", default="now-1h", help="Search start time")
    parser.add_argument("--end", default="now", help="Search end time")
    parser.add_argument("--limit", type=int, default=3, help="Max number of trigger events to analyze")
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports/incidents"),
        help="Output directory"
    )

    args = parser.parse_args()
    
    print(f"Searching for '{args.keyword}' in {args.index} ({args.start} to {args.end})...")
    triggers = search_triggers(args.host, args.port, args.index, args.keyword, args.start, args.end, args.limit)
    
    if not triggers:
        print("No triggers found.")
        return

    print(f"Found {len(triggers)} trigger events. Fetching context...")
    
    report_data = []
    
    for i, trigger in enumerate(triggers):
        source = trigger.get("_source", {})
        ts = source.get("@timestamp")
        # Handle nested host.name or top-level
        host_name = source.get("host", {}).get("name")
        if not host_name:
             # Fallback if host is just a string or different structure
             host_name = source.get("host")
        
        if not ts or not host_name:
            print(f"Skipping trigger {trigger.get('_id')}: Missing timestamp or host.name")
            continue
            
        print(f"[{i+1}/{len(triggers)}] Fetching context for host '{host_name}' around {ts}...")
        context_logs = fetch_context(args.host, args.port, args.index, host_name, ts)
        
        incident = {
            "trigger_event": trigger,
            "context_window": "+/- 60 seconds",
            "host": host_name,
            "timestamp": ts,
            "log_count": len(context_logs),
            "logs": [l.get("_source", {}).get("_raw", "") for l in context_logs]
        }
        report_data.append(incident)

    # Save report
    args.output.mkdir(parents=True, exist_ok=True)
    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output / f"incident_{args.keyword}_{timestamp_file}.json"
    
    output_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
    print(f"Incident report written to: {output_file}")

if __name__ == "__main__":
    main()
