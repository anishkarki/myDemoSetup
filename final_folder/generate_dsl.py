#!/usr/bin/env python3
"""
Generate OpenSearch DSL query for log filtering.
Filters by host.name, time range, and _raw content.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

def build_dsl(host: str, start_time: str, end_time: str, raw_filter: str) -> dict:
    """Construct the OpenSearch DSL query."""
    
    # Base query structure
    dsl = {
        "query": {
            "bool": {
                "must": [
                    # Filter by host.name (use wildcard if * is present, else term)
                    # Note: host.name is a keyword field inside the 'host' object
                    { "wildcard": { "host.name": host } } if "*" in host else { "term": { "host.name": host } },
                    # Filter by time range
                    { 
                        "range": { 
                            "@timestamp": { 
                                "gte": start_time, 
                                "lte": end_time 
                            } 
                        } 
                    }
                ]
            }
        },
        # Standard pagination/sorting
        "from": 0,
        "size": 100,
        "sort": [
            { "@timestamp": { "order": "desc" } }
        ]
    }

    # Add _raw filter if provided
    if raw_filter:
        # Check if multiple keywords are provided (comma-separated)
        keywords = [k.strip() for k in raw_filter.split(",") if k.strip()]
        
        if len(keywords) > 1:
            # Use 'should' clause (OR logic) for multiple keywords
            should_clause = []
            for keyword in keywords:
                should_clause.append({
                    "match_phrase": { "_raw": keyword }
                })
            
            dsl["query"]["bool"]["must"].append({
                "bool": {
                    "should": should_clause,
                    "minimum_should_match": 1
                }
            })
        elif len(keywords) == 1:
            # Single keyword
            dsl["query"]["bool"]["must"].append({
                "match_phrase": { "_raw": keywords[0] }
            })
        
    return dsl

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenSearch DSL for log filtering.")
    parser.add_argument("hostname", help="Target host.name")
    parser.add_argument("--start", required=True, help="Start time (ISO 8601, e.g., 'now-1h' or '2023-01-01T00:00:00Z')")
    parser.add_argument("--end", required=True, help="End time (ISO 8601, e.g., 'now' or '2023-01-01T01:00:00Z')")
    parser.add_argument("--filter", help="Text to filter in _raw field", default="")
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports/dsl"),
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    dsl_query = build_dsl(args.hostname, args.start, args.end, args.filter)
    
    # Ensure output directory exists
    args.output.mkdir(parents=True, exist_ok=True)
    
    output_file = args.output / f"log_query_{args.hostname}.json"
    output_file.write_text(json.dumps(dsl_query, indent=2), encoding="utf-8")
    
    print(f"DSL Query written to: {output_file}")
    print(json.dumps(dsl_query, indent=2))

if __name__ == "__main__":
    main()
