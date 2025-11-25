# OpenSearch DSL Queries for Patroni Failover/Switchover Logs

## 📋 Overview

This directory contains OpenSearch DSL queries to fetch Patroni failover and switchover logs from your OpenSearch instance.

## 📁 Query Files

### 1. `opensearch_failover_query.json`
**Purpose**: Fetch all failover-related logs

**Matches**:
- Explicit "failover" mentions
- Promotion/demotion events
- Leader elections
- Lock acquisitions/releases
- Role changes to/from leader
- Automatic failover triggers

**Use when**: Investigating unplanned failover events or automatic leader changes

### 2. `opensearch_switchover_query.json`
**Purpose**: Fetch all switchover-related logs

**Matches**:
- Explicit "switchover" mentions
- Manual failover requests
- Planned switchover events
- Switchover scheduling
- Controlled demotions

**Use when**: Investigating planned maintenance or manual leader changes

### 3. `opensearch_all_events_query.json`
**Purpose**: Comprehensive query for all cluster events

**Matches**:
- All failover events
- All switchover events
- Leader elections
- Replication state changes
- Timeline changes
- Cluster topology changes

**Includes**: Advanced aggregations for event analysis

**Use when**: Getting complete overview of all cluster state changes

## 🚀 Quick Start

### Option 1: Interactive Script (Recommended)

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./query_opensearch.sh
```

Follow the menu to select query type.

### Option 2: Direct cURL Commands

**Failover logs:**
```bash
curl -X GET "http://localhost:19200/patroni-logs-*,postgres-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_failover_query.json | jq '.'
```

**Switchover logs:**
```bash
curl -X GET "http://localhost:19200/patroni-logs-*,postgres-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_switchover_query.json | jq '.'
```

**All events:**
```bash
curl -X GET "http://localhost:19200/patroni-logs-*,postgres-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_all_events_query.json | jq '.'
```

### Option 3: Using OpenSearch Dashboards

1. Open OpenSearch Dashboards: http://localhost:15601
2. Go to Dev Tools
3. Copy-paste the query content
4. Modify the index pattern: `GET /patroni-logs-*,postgres-logs-*/_search`
5. Execute

## 🔧 Configuration

### Environment Variables

```bash
export OPENSEARCH_HOST=localhost
export OPENSEARCH_PORT=19200
export INDEX_PATTERN="patroni-logs-*,postgres-logs-*,logs-*"
```

### Customizing Queries

#### Change Time Range
Add to the `filter` array in any query:
```json
{
  "range": {
    "@timestamp": {
      "gte": "2025-11-25T00:00:00",
      "lte": "2025-11-25T23:59:59"
    }
  }
}
```

#### Change Result Size
Modify the `size` parameter:
```json
"size": 1000
```

#### Filter by Specific Node
Add to the `filter` array:
```json
{
  "term": {
    "source.keyword": "patroni1"
  }
}
```

#### Filter by Severity
Add to the `filter` array:
```json
{
  "terms": {
    "level.keyword": ["ERROR", "WARNING", "CRITICAL"]
  }
}
```

## 📊 Query Structure Explained

### Boolean Query Structure
```json
{
  "query": {
    "bool": {
      "should": [/* OR conditions - at least one must match */],
      "must": [/* AND conditions - all must match */],
      "filter": [/* Filtering without scoring */],
      "minimum_should_match": 1
    }
  }
}
```

### Search Patterns Used

1. **`multi_match`**: Searches across multiple fields
2. **`match_phrase`**: Exact phrase matching
3. **`regexp`**: Regular expression matching
4. **`terms`**: Match multiple exact values

### Highlighting

Results include highlighted matches:
```json
"highlight": {
  "fields": {
    "message": {
      "fragment_size": 200,
      "number_of_fragments": 3
    }
  }
}
```

## 📈 Aggregations

The `opensearch_all_events_query.json` includes aggregations:

- **events_by_source**: Count events per source (patroni1, patroni2, etc.)
- **events_over_time**: Histogram of events over time
- **events_by_severity**: Count events by severity level

Access aggregations in results:
```bash
jq '.aggregations' results.json
```

## 🎯 Example Workflows

### Find All Failovers in Last Hour
```bash
# Create temporary query with time filter
jq '.query.bool.filter += [{"range": {"@timestamp": {"gte": "now-1h"}}}]' \
  opensearch_failover_query.json > temp_query.json

curl -X GET "http://localhost:19200/patroni-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @temp_query.json | jq '.hits.hits[]._source'

rm temp_query.json
```

### Extract Just Messages
```bash
curl -X GET "http://localhost:19200/patroni-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_failover_query.json | \
  jq -r '.hits.hits[]._source | "[\(.\"@timestamp\")] \(.message)"'
```

### Count Events by Type
```bash
curl -X GET "http://localhost:19200/patroni-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_all_events_query.json | \
  jq '.aggregations.events_by_source.buckets'
```

### Export to CSV
```bash
curl -X GET "http://localhost:19200/patroni-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d @opensearch_failover_query.json | \
  jq -r '.hits.hits[]._source | [.["@timestamp"], .source, .level, .message] | @csv' > failover_logs.csv
```

## 🔍 Field Mappings

Common fields in logs:
- `@timestamp`: Event timestamp
- `message` or `log`: Log message content
- `source`: Source system (patroni1, patroni2, postgres)
- `container_name`: Docker container name
- `level` or `severity`: Log level (INFO, WARNING, ERROR)
- `host`: Hostname
- `cluster`: Cluster name
- `timeline`: PostgreSQL timeline number
- `role`: Patroni role (leader, replica)

## 🛠️ Troubleshooting

### No Results Found
1. Check if OpenSearch is running: `curl http://localhost:19200`
2. Check if indices exist: `curl http://localhost:19200/_cat/indices`
3. Verify index pattern matches your indices
4. Check if logs are being ingested

### Connection Refused
```bash
# Check OpenSearch container
docker ps | grep opensearch

# Check OpenSearch logs
docker logs opensearch
```

### Invalid Query
```bash
# Validate JSON syntax
cat opensearch_failover_query.json | jq '.'

# Test with smaller query
curl -X GET "http://localhost:19200/_cat/indices"
```

### JQ Not Found
```bash
# Install jq
sudo apt-get install jq  # Debian/Ubuntu
brew install jq          # macOS
```

## 📝 Advanced Examples

### Combine with Saved Searches
Create saved search in OpenSearch Dashboards and reference it.

### Create Alerts
Use OpenSearch alerting to trigger on failover patterns.

### Build Dashboard
Import these queries into OpenSearch Dashboards for visualization.

### Export for Analysis
```bash
./query_opensearch.sh
# Select option 3 for all events
# Results saved to results_all_events_TIMESTAMP.json

# Analyze with Python
python3 << EOF
import json
with open('results_all_events_*.json') as f:
    data = json.load(f)
    for hit in data['hits']['hits']:
        print(hit['_source']['message'])
EOF
```

## 🔗 Related Files

- `check_health.sh` - Check cluster health before querying
- `trigger_failover.sh` - Generate failover events
- `trigger_switchover.sh` - Generate switchover events
- `monitor_and_collect.sh` - Continuous monitoring

## 📚 Resources

- [OpenSearch Query DSL](https://opensearch.org/docs/latest/query-dsl/)
- [OpenSearch Dashboards](http://localhost:15601)
- [Patroni Documentation](https://patroni.readthedocs.io/)

---

**OpenSearch URL**: http://localhost:19200
**Dashboards URL**: http://localhost:15601
**Default Index Pattern**: `patroni-logs-*,postgres-logs-*`
