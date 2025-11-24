# Log Context Retrieval Guide

## Problem
OpenSearch Alerting monitors have limitations:
- ✅ Can detect errors in logs and send alerts
- ✅ Can aggregate and group errors by host
- ✅ Can show sample error messages
- ❌ **Cannot retrieve surrounding log lines (context) within a single monitor**
- ❌ Cannot make multiple search queries in one monitor
- ❌ Cannot use nested queries to fetch related documents

## Solutions

### Option 1: Manual Context Retrieval (Recommended)
When you receive an error alert email, use the timestamps to query OpenSearch for surrounding context:

```bash
# Get ±5 lines around an error at timestamp 2025-01-24T10:30:00Z
curl -X POST "http://localhost:19200/postgresdata/_search" -H 'Content-Type: application/json' -d'
{
  "size": 100,
  "query": {
    "bool": {
      "filter": [
        {
          "term": {
            "host.name": "patroni1"
          }
        },
        {
          "term": {
            "source.keyword": "/var/log/postgresql/patroni.log"
          }
        },
        {
          "range": {
            "@timestamp": {
              "gte": "2025-01-24T10:29:30Z",
              "lte": "2025-01-24T10:30:30Z"
            }
          }
        }
      ]
    }
  },
  "sort": [
    {
      "@timestamp": {
        "order": "asc"
      }
    }
  ],
  "_source": ["@timestamp", "_raw"]
}' | jq '.hits.hits[]._source'
```

### Option 2: Check Log Files Directly
SSH to the container and use grep with context:

```bash
# Show 5 lines before and after error
docker exec -it patroni1 grep -C 5 "ERROR" /var/log/postgresql/patroni.log

# Show errors with timestamps
docker exec -it patroni1 tail -f /var/log/postgresql/patroni.log | grep --color -C 5 "ERROR\|FATAL\|PANIC"
```

### Option 3: Enhanced Webhook Server (Implemented but Not Fully Integrated)
The `smtp_webhook_server.py` has `get_log_context()` function that can fetch surrounding logs.

**To use it:**
1. Modify OpenSearch monitor JSON to pass error metadata:
   ```json
   {
     "error_timestamp": "{{ctx.results.0.hits.hits.0._source.@timestamp}}",
     "error_host": "{{ctx.results.0.hits.hits.0._source.host.name}}"
   }
   ```

2. The webhook will automatically query OpenSearch for ±5 lines around each error

**Limitation:** OpenSearch doesn't allow custom webhook body formatting with dynamic fields from aggregations.

### Option 4: Post-Processing Script
Create a cron job that runs every minute:

```python
#!/usr/bin/env python3
"""
Fetch recent errors from OpenSearch and enrich with context
"""
import requests
from datetime import datetime, timedelta

def get_errors_with_context():
    # 1. Query for errors in last minute
    errors_query = {
        "size": 50,
        "query": {
            "bool": {
                "filter": [
                    {"range": {"@timestamp": {"gte": "now-1m"}}},
                    {"match": {"_raw": "ERROR"}}
                ]
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}]
    }
    
    response = requests.post(
        "http://localhost:19200/postgresdata/_search",
        json=errors_query
    )
    
    errors = response.json()['hits']['hits']
    
    # 2. For each error, get surrounding context
    for error in errors:
        timestamp = error['_source']['@timestamp']
        host = error['_source']['host']['name']
        source_file = error['_source']['source']
        
        # Query for ±30 seconds around error
        error_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        time_before = (error_time - timedelta(seconds=30)).isoformat()
        time_after = (error_time + timedelta(seconds=30)).isoformat()
        
        context_query = {
            "size": 11,  # 5 before + error + 5 after
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"host.name": host}},
                        {"term": {"source.keyword": source_file}},
                        {"range": {"@timestamp": {"gte": time_before, "lte": time_after}}}
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}]
        }
        
        context_response = requests.post(
            "http://localhost:19200/postgresdata/_search",
            json=context_query
        )
        
        context_logs = context_response.json()['hits']['hits']
        
        print(f"\n{'='*80}")
        print(f"ERROR FOUND: {timestamp} on {host}")
        print(f"File: {source_file}")
        print(f"{'='*80}")
        print("\nSURROUNDING LOG CONTEXT:")
        print("-" * 80)
        
        for log in context_logs:
            log_time = log['_source']['@timestamp']
            log_msg = log['_source']['_raw']
            marker = ">>> " if log_time == timestamp else "    "
            print(f"{marker}[{log_time}] {log_msg}")

if __name__ == '__main__':
    get_errors_with_context()
```

## Current Implementation

The monitors deployed (`patroni_error_monitor.json`) provide:
- ✅ Real-time error detection
- ✅ Grouping by host
- ✅ Aggregation by log source file
- ✅ Up to 50 sample error logs per host
- ✅ Email alerts via webhook
- ✅ HTML formatted emails with structured data

**To view context:** Use the timestamps from alert emails with Option 1 or Option 2 above.

## Why Not Native Context in Monitor?

OpenSearch Alerting plugin limitations:
1. **Single query only** - Cannot run multiple searches per monitor execution
2. **No nested queries** - Cannot query based on results of first query
3. **Limited scripting** - Painless scripts can't make additional index searches
4. **Webhook format** - Cannot dynamically construct webhook body from nested aggregation results

**Workaround:** The monitor provides all necessary metadata (timestamp, host, source file) in alerts. You can then manually or automatically retrieve context using that metadata.

## Recommended Workflow

1. **Monitor detects errors** → sends email alert
2. **Email contains**:
   - Host name
   - Error count
   - Sample error messages with timestamps
   - Source log files
3. **To investigate**:
   - Copy error timestamp from email
   - Run OpenSearch query (Option 1) or grep log file (Option 2)
   - View ±5 lines of context around the error

This two-step approach is more reliable than trying to work around OpenSearch's limitations.
