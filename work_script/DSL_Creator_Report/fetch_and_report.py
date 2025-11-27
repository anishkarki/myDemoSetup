#!/usr/bin/env python3
"""
Log Fetcher & Reporter
Fetches logs from OpenSearch based on dynamic keywords/wildcards and generates a beautiful HTML report.
"""

import argparse
import json
import sys
import ssl
import os
from datetime import datetime
from urllib import request, error

# --- Configuration ---
DEFAULT_OPENSEARCH_URL = "http://100.80.115.61:19200"
DEFAULT_INDEX = "patronidata"

# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Report - {hostname}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background-color: #f8f9fa; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .summary {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; justify-content: space-between; }}
        .summary-item {{ font-weight: bold; }}
        .badge {{ padding: 5px 10px; border-radius: 4px; font-size: 0.9em; color: white; }}
        .badge-info {{ background-color: #17a2b8; }}
        .badge-danger {{ background-color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f1f3f5; font-weight: 600; }}
        tr:hover {{ background-color: #f8f9fa; }}
        .timestamp {{ white-space: nowrap; color: #666; font-family: monospace; }}
        .message {{ font-family: monospace; font-size: 0.95em; }}
        .no-results {{ text-align: center; padding: 40px; color: #666; font-style: italic; }}
        .filters {{ margin-bottom: 20px; font-size: 0.9em; color: #555; }}
        .keyword-tag {{ background: #e2e6ea; padding: 2px 6px; border-radius: 3px; margin-right: 5px; border: 1px solid #d6d8db; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Log Analysis Report</h1>
        
        <div class="summary">
            <div class="summary-item">Host: <span class="badge badge-info">{hostname}</span></div>
            <div class="summary-item">Total Hits: <span class="badge badge-danger">{total_hits}</span></div>
            <div class="summary-item">Generated: {generated_at}</div>
        </div>

        <div class="filters">
            <strong>Filters Applied:</strong> 
            {filter_tags}
        </div>

        <table>
            <thead>
                <tr>
                    <th width="200">Timestamp</th>
                    <th>Log Message</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def generate_dsl(host, keywords, exclude_keywords=None, time_range=None, start_time=None, end_time=None, size=1000):
    """Generates the OpenSearch DSL query."""
    
    should_clauses = []
    for kw in keywords:
        if "*" in kw or "?" in kw:
            should_clauses.append({
                "wildcard": {
                    "message": {
                        "value": kw,
                        "case_insensitive": True
                    }
                }
            })
            # Also try matching against _raw if message field is missing
            should_clauses.append({
                "wildcard": {
                    "_raw": {
                        "value": kw,
                        "case_insensitive": True
                    }
                }
            })
        else:
            should_clauses.append({
                "match_phrase": {
                    "message": kw
                }
            })
            # Also try matching against _raw
            should_clauses.append({
                "match_phrase": {
                    "_raw": kw
                }
            })

    must_not_clauses = []
    if exclude_keywords:
        for kw in exclude_keywords:
            must_not_clauses.append({
                "match_phrase": {
                    "message": kw
                }
            })
            must_not_clauses.append({
                "match_phrase": {
                    "_raw": kw
                }
            })

    # Determine time range
    if start_time and end_time:
        time_filter = {"range": {"@timestamp": {"gte": start_time, "lte": end_time}}}
    elif time_range:
        time_filter = {"range": {"@timestamp": {"gte": f"now-{time_range}", "lte": "now"}}}
    else:
        # Default to 1h if nothing specified
        time_filter = {"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}}

    query = {
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "filter": [
                    time_filter
                ],
                "must": [
                    {
                        "bool": {
                            "should": [
                                {"term": {"host.name.keyword": host}},
                                {"wildcard": {"source": {"value": f"*{host}*"}}}
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ],
                "must_not": must_not_clauses,
                "minimum_should_match": 1,
                "should": should_clauses
            }
        }
    }
    return query

def fetch_logs(url, index, query, username=None, password=None, token=None, verify_ssl=False):
    """Executes the query against OpenSearch."""
    api_endpoint = f"{url.rstrip('/')}/{index}/_search"
    data = json.dumps(query).encode('utf-8')
    
    req = request.Request(api_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    if token:
        req.add_header('Authorization', f"Bearer {token}")
    elif username and password:
        import base64
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        req.add_header('Authorization', f"Basic {b64_auth}")

    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        with request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as e:
        print(f"Error fetching logs: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

def create_html_report(hits, host, keywords, output_file):
    """Generates the HTML report file."""
    rows = ""
    if not hits:
        rows = "<tr><td colspan='2' class='no-results'>No logs found matching the criteria.</td></tr>"
    else:
        for hit in hits:
            source = hit['_source']
            timestamp = source.get('@timestamp', 'N/A')
            # Fallback to _raw if message is missing
            message = source.get('message', source.get('_raw', ''))
            rows += f"<tr><td class='timestamp'>{timestamp}</td><td class='message'>{message}</td></tr>"

    filter_tags = "".join([f"<span class='keyword-tag'>{k}</span>" for k in keywords])
    
    html_content = HTML_TEMPLATE.format(
        hostname=host,
        total_hits=len(hits),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        filter_tags=filter_tags,
        table_rows=rows
    )

    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Report generated: {output_file}")

def create_log_report(hits, output_file):
    """Generates a plain text log file."""
    with open(output_file, 'w') as f:
        if not hits:
            f.write("No logs found matching the criteria.\n")
        else:
            for hit in hits:
                source = hit['_source']
                timestamp = source.get('@timestamp', 'N/A')
                # Fallback to _raw if message is missing
                message = source.get('message', source.get('_raw', ''))
                f.write(f"{timestamp} {message}\n")
    
    print(f"Log report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Fetch logs from OpenSearch and generate an HTML report.")
    parser.add_argument("--host", required=True, help="Hostname to filter logs (e.g., patroni1)")
    parser.add_argument("--keywords", nargs="+", default=["error", "fail", "exception", "fatal"], help="Keywords to search for (default: error fail exception fatal)")
    parser.add_argument("--time", default="1h", help="Time range (e.g., 15m, 1h, 24h). Ignored if --start-time and --end-time are provided.")
    parser.add_argument("--start-time", help="Start time in ISO format (e.g., 2023-10-27T10:00:00Z)")
    parser.add_argument("--end-time", help="End time in ISO format (e.g., 2023-10-27T11:00:00Z)")
    parser.add_argument("--index", default="patronidata", help="OpenSearch index name")
    parser.add_argument("--output", default="log_report.html", help="Output HTML file name")
    parser.add_argument("--opensearch-url", default="http://100.80.115.61:19200", help="OpenSearch URL")

    args = parser.parse_args()

    print(f"Fetching logs for host: {args.host}")
    print(f"Keywords: {args.keywords}")
    
    if args.start_time and args.end_time:
        print(f"Time Range: {args.start_time} to {args.end_time}")
    else:
        print(f"Time Range: Last {args.time}")

    dsl_query = generate_dsl(args.host, args.keywords, args.time, args.start_time, args.end_time)
    
    result = fetch_logs(args.opensearch_url, args.index, dsl_query)
    hits = result.get('hits', {}).get('hits', [])
    print(f"Found {len(hits)} logs.")

    create_html_report(hits, args.host, args.keywords, args.output)
    create_log_report(hits, "log_report.txt")  # Generate plain text log report

if __name__ == "__main__":
    main()
