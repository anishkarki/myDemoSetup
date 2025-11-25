#!/usr/bin/env python3
"""
Generate OpenSearch DSL query to fetch context logs around a specific timestamp.
Uses a Painless script to filter logs within a +/- N seconds window.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import parser as date_parser

def build_painless_dsl(host: str, center_time_str: str, window_seconds: int) -> dict:
    """Construct the DSL query using Painless."""
    
    try:
        # Parse timestamp to epoch milliseconds for the script
        dt = date_parser.parse(center_time_str)
        center_millis = int(dt.timestamp() * 1000)
        
        # Calculate broad bounds for the range filter (optimization)
        # We add a small buffer to the window for the hard range filter
        # to ensure we don't miss anything due to rounding, while keeping the script efficient.
        buffer = 5  # seconds
        start_dt = dt - timedelta(seconds=window_seconds + buffer)
        end_dt = dt + timedelta(seconds=window_seconds + buffer)
        
    except Exception as e:
        raise ValueError(f"Invalid timestamp format: {e}")

    dsl = {
        "query": {
            "bool": {
                "filter": [
                    # Host Filter
                    { "wildcard": { "host.name": host } } if "*" in host else { "term": { "host.name": host } },
                    
                    # Broad Range Filter (Optimization: Don't scan the whole index)
                    {
                        "range": {
                            "@timestamp": {
                                "gte": start_dt.isoformat(),
                                "lte": end_dt.isoformat()
                            }
                        }
                    },
                    
                    # Painless Script Filter (The requested logic)
                    {
                        "script": {
                            "script": {
                                "lang": "painless",
                                "source": """
                                    long docTime = doc['@timestamp'].value.toInstant().toEpochMilli();
                                    long centerTime = params.center_time;
                                    long window = params.window_ms;
                                    return Math.abs(docTime - centerTime) <= window;
                                """,
                                "params": {
                                    "center_time": center_millis,
                                    "window_ms": window_seconds * 1000
                                }
                            }
                        }
                    }
                ]
            }
        },
        "size": 500,
        "sort": [
            { "@timestamp": { "order": "asc" } }
        ]
    }
    
    return dsl

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Painless DSL for log context.")
    parser.add_argument("timestamp", help="Center timestamp (ISO 8601)")
    parser.add_argument("--host", required=True, help="Target host.name")
    parser.add_argument("--window", type=int, default=60, help="Context window in seconds (default: 60)")
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports/dsl"),
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    try:
        dsl_query = build_painless_dsl(args.host, args.timestamp, args.window)
        
        # Ensure output directory exists
        args.output.mkdir(parents=True, exist_ok=True)
        
        # Create a filename safe timestamp string
        safe_ts = args.timestamp.replace(":", "").replace("-", "").replace(" ", "_")
        output_file = args.output / f"context_query_{args.host}_{safe_ts}.json"
        
        output_file.write_text(json.dumps(dsl_query, indent=2), encoding="utf-8")
        
        print(f"Painless DSL Query written to: {output_file}")
        print(json.dumps(dsl_query, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
