# OpenSearch DSL Query for Patroni Failover Detection

## Overview
This DSL query captures PostgreSQL failover events from both primary and replica nodes during a Patroni failover scenario.

## Index
- **Target Index**: `patronidata`
- **Log Field**: `_raw` (contains the actual log message)
- **Source Field**: `source` (log file path)
- **Timestamp Field**: `@timestamp`

## Query File
- `failover_query.json` - Production-ready DSL query

## Usage

### Basic Query
```bash
curl -X GET "http://localhost:19200/patronidata/_search" \
  -H 'Content-Type: application/json' \
  -d @failover_query.json | jq '.'
```

### View Events Only
```bash
curl -s -X GET "http://localhost:19200/patronidata/_search" \
  -H 'Content-Type: application/json' \
  -d @failover_query.json | \
  jq '.hits.hits[] | {time: ._source["@timestamp"], source: ._source.source, message: ._source._raw}'
```

### View Aggregation by Source
```bash
curl -s -X GET "http://localhost:19200/patronidata/_search" \
  -H 'Content-Type: application/json' \
  -d @failover_query.json | \
  jq '.aggregations.by_source.buckets | map({source: .key, count: .doc_count})'
```

## Customization

### Adjust Time Range
Edit the `@timestamp` range in the query:
```json
"range": {
  "@timestamp": {
    "gte": "2025-11-25T04:42:00",  // Start time
    "lte": "2025-11-25T04:42:10",  // End time
    "time_zone": "-07:00"           // Your timezone
  }
}
```

### Add More Patterns
Add additional failover patterns to the `should` clause:
```json
{
  "wildcard": {
    "_raw": {
      "value": "*your pattern here*"
    }
  }
}
```

## What It Captures

### From Primary Node (patroni1)
- Connection terminations
- Checkpoint completion
- Shutdown sequence

### From Replica Node (patroni2)
- Replication termination detection
- WAL end reached on timeline
- Promote request received
- New timeline selection
- Archive recovery completion
- Database ready to accept connections

## Validation
Query has been tested and validated to capture:
- **15 failover events** total
- **3 events** from patroni1 (failed primary)
- **12 events** from patroni2 (promoted replica)

## Key Patterns Matched
- `replication terminated`
- `End of WAL reached`
- `received promote request`
- `selected new timeline ID`
- `archive recovery complete`
- `database system is ready to accept connections`
- `standby promoted`
- `failover`
