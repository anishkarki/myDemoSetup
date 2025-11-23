# PostgreSQL Frequency Monitor Setup

## Overview
Frequency-based alerting system that triggers when the same PostgreSQL error occurs more than 5 times on the same hostname within 5 minutes.

## Monitor Details

### Monitor ID
`SN-fm5oBd6nYLt6Sb13S`

### Configuration
- **Name**: Postgres Frequency Alert - Repeated Errors by Hostname
- **Schedule**: Runs every 1 minute
- **Time Window**: Aggregates last 5 minutes of data
- **Alert Threshold**: >5 occurrences of same SQLSTATE on same hostname
- **Throttle**: 5 minutes

### How It Works

1. **Data Collection**:
   - Grok pipeline extracts `postgres.sqlstate` from `_raw` field
   - Pipeline applied to: `postgresdata`, `postgresd*`, `postgreslogs` indices

2. **Aggregation Query**:
   ```json
   {
     "group_by_hostname": {
       "terms": {"field": "host.name.keyword"},
       "aggs": {
         "group_by_sqlstate": {
           "terms": {"field": "postgres.sqlstate", "min_doc_count": 6}
         }
       }
     }
   }
   ```

3. **Trigger Logic** (Painless script):
   - Iterates through hostname buckets
   - For each hostname, checks SQLSTATE buckets
   - Returns true if any SQLSTATE count > 5

4. **Email Alert**:
   - Groups results by hostname
   - Shows SQLSTATE code, count, and description
   - Includes time window and total error count per host

### Monitored SQLSTATE Codes

| Code | Description |
|------|-------------|
| 22012 | Division by zero |
| 53000 | Insufficient resources |
| 53100 | Disk full |
| 53200 | Out of memory |
| 53300 | Too many connections |
| 54000 | Program limit exceeded |
| 57000 | Operator intervention |
| 57014 | Query canceled |
| 57P01 | Admin shutdown |
| 57P02 | Crash shutdown |
| 58000 | System error |
| XX000 | Internal error |

## Grok Pipeline

### Pipeline Name
`postgres-error-parser`

### Pattern
```
.*e=%{DATA:postgres.sqlstate}, (?<postgres.error_level>ERROR|FATAL|PANIC): %{GREEDYDATA:postgres.error_message}
```

### Extracted Fields
- `postgres.sqlstate` - PostgreSQL error code (e.g., "22012")
- `postgres.error_level` - Error severity (ERROR, FATAL, PANIC)
- `postgres.error_message` - Error description

## Testing

### Generate Test Errors
```bash
# Generate 7 identical errors (should trigger alert after 5th one)
for i in {1..7}; do 
  psql -h localhost -p 15432 -U postgres -d postgres -c "SELECT 1/0;";
  sleep 1;
done
```

### Wait for Alert
- Logs are ingested (may take 5-30 seconds depending on your setup)
- Monitor runs every 1 minute
- Check Mailhog after 60-90 seconds

### Verify Email
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/DSL_AUTOMATION
curl -sS 'http://100.80.115.61:8025/api/v2/messages' | jq '.items[0].Content.Headers.Subject[0]'
# Should contain "FREQUENCY Alert"
```

## Email Template

The frequency alert email shows:
- Header with monitor name and time window
- Each hostname as a section
- Table with:
  - Count (number of occurrences)
  - SQLSTATE code
  - Error description
- Alternating row colors for readability

## Files Modified

1. `opensearch_dsl.yml` - Added frequency monitor configuration
2. `generate_monitors.py` - Added HTML_FREQUENCY_TEMPLATE and aggregation support
3. `generated_monitors/postgres_frequency_alert_repeated_errors_by_hostname.json` - Generated monitor

## Maintenance

### Update Monitored Codes
Edit `opensearch_dsl.yml`:
```yaml
conditions:
  - type: "terms"
    field: "postgres.sqlstate"
    values: ["22012", "53000", ...] # Add/remove codes
```

### Change Threshold
Edit `opensearch_dsl.yml`:
```yaml
aggregations:
  group_by_hostname:
    terms:
      field: "host.name.keyword"
    aggs:
      group_by_sqlstate:
        terms:
          field: "postgres.sqlstate"
          min_doc_count: 6  # Change this (threshold + 1)
```

And update trigger condition:
```yaml
if (sqlstate.doc_count > 5) {  # Change threshold here
  return true;
}
```

### Regenerate and Deploy
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/DSL_AUTOMATION
python3 generate_monitors.py opensearch_dsl.yml
curl -X DELETE "http://localhost:19200/_plugins/_alerting/monitors/$(cat /tmp/frequency_monitor_id.txt)"
curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @generated_monitors/postgres_frequency_alert_repeated_errors_by_hostname.json
```

## Troubleshooting

### No Alerts Received
1. Check if monitor is enabled:
   ```bash
   curl -sS "http://localhost:19200/_plugins/_alerting/monitors/$(cat /tmp/frequency_monitor_id.txt)" | jq '.monitor.enabled'
   ```

2. Verify data exists:
   ```bash
   curl -sS 'http://localhost:19200/postgres*/_search' -H 'Content-Type: application/json' -d '{
     "query": {"range": {"@timestamp": {"gte": "now-5m"}}},
     "aggs": {
       "by_host": {
         "terms": {"field": "host.name.keyword"},
         "aggs": {"by_code": {"terms": {"field": "postgres.sqlstate"}}}
       }
     },
     "size": 0
   }' | jq '.aggregations'
   ```

3. Check monitor execution history:
   ```bash
   curl -sS "http://localhost:19200/_plugins/_alerting/monitors/$(cat /tmp/frequency_monitor_id.txt)/_execute" | jq '.trigger_results'
   ```

### Grok Pipeline Not Working
```bash
# Test pipeline manually
curl -X POST 'http://localhost:19200/_ingest/pipeline/postgres-error-parser/_simulate' \
  -H 'Content-Type: application/json' -d '{
  "docs": [
    {"_source": {"_raw": "ts=2025-11-19 10:12:23 e=22012, ERROR: division by zero"}}
  ]
}'
```
