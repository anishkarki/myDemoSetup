#!/usr/bin/env python3
"""
Execute an OpenSearch DSL query from a JSON file against a target OpenSearch instance.
"""

import argparse
import json
import sys
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

def run_query(host: str, port: int, index: str, dsl_path: Path, user: str = None, password: str = None) -> dict:
    """Execute the DSL query."""
    
    url = f"http://{host}:{port}/{index}/_search"
    
    try:
        dsl_query = json.loads(dsl_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading DSL file: {e}", file=sys.stderr)
        sys.exit(1)

    auth = None
    if user and password:
        auth = HTTPBasicAuth(user, password)

    print(f"Executing query against {url}...")
    try:
        response = requests.post(url, json=dsl_query, auth=auth, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error executing query: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run OpenSearch DSL query.")
    parser.add_argument("dsl_file", type=Path, help="Path to the JSON file containing the DSL query")
    parser.add_argument("--host", default="100.80.115.61", help="OpenSearch host IP")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--index", default="postgreslogs", help="Target index pattern")
    parser.add_argument("--user", help="Username")
    parser.add_argument("--password", help="Password")
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports"),
        help="Output directory for results"
    )

    args = parser.parse_args()

    results = run_query(args.host, args.port, args.index, args.dsl_file, args.user, args.password)
    
    args.output.mkdir(parents=True, exist_ok=True)
    output_file = args.output / f"results_{args.dsl_file.stem}.json"
    output_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    
    print(f"Results written to: {output_file}")
    
    # Print a brief summary
    hits = results.get("hits", {}).get("total", {}).get("value", "Unknown")
    print(f"Total hits: {hits}")

if __name__ == "__main__":
    main()
