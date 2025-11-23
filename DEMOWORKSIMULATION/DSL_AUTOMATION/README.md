# OpenSearch Monitor DSL Automation

Dynamic monitor generation for OpenSearch from YAML configuration files.

## Overview

This tool allows you to define OpenSearch monitors in a simple YAML format and automatically generate the corresponding JSON files ready for deployment.

## Files

- `opensearch_dsl.yml` - YAML configuration defining monitors
- `generate_monitors.py` - Python script to generate monitor JSON files
- `test_generator.py` - Test suite for the monitor generator
- `generated_monitors/` - Output directory for generated JSON files

## Quick Start

```bash
# Clone or navigate to the directory
cd /home/swordfish/EveryThing0and1/myDemoSetup/DSL_AUTOMATION

# Generate monitors from YAML config
python3 generate_monitors.py opensearch_dsl.yml

# Run tests
python3 test_generator.py

# Upload generated monitor to OpenSearch
curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @generated_monitors/postgres_criticality_monitor_production_structured_sqlstate.json
```

## Usage

### 1. Define Monitors in YAML

Edit `opensearch_dsl.yml` to define your monitors:

```yaml
monitors:
  - name: "Postgres Criticality Monitor - Production"
    enabled: true
    schedule:
      interval: 1
      unit: "MINUTES"
    
    inputs:
      indices:
        - "postgresdata"
      
      conditions:
        - type: "terms"
          field: "postgres.sqlstate"
          values: ["22012", "53000", "57000"]
        
        - type: "match_phrase"
          field: "_raw"
          value: "FATAL"
    
    triggers:
      - name: "Critical Alert"
        severity: 1
        condition:
          script: "return ctx.results != null && ctx.results[0].hits.total.value > 0;"
        
        actions:
          - name: "Email Alert"
            type: "email"
            destination_id: "your-destination-id"
            subject_template: "Alert: {{ctx.monitor.name}}"
            message_template_type: "html_grouped_by_host"
            throttle:
              enabled: true
              value: 15
              unit: "MINUTES"
```

### 2. Generate Monitor JSON

Run the generator:

```bash
python3 generate_monitors.py opensearch_dsl.yml
```

Or specify a custom output directory:

```bash
python3 generate_monitors.py opensearch_dsl.yml ./my_monitors
```

### 3. Upload to OpenSearch

Upload generated monitors:

```bash
curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @generated_monitors/postgres_criticality_monitor_production.json
```

## Configuration Reference

### Monitor Structure

- `name` - Monitor display name
- `enabled` - Enable/disable monitor (true/false)
- `schedule` - Execution schedule
  - `interval` - Numeric interval
  - `unit` - Time unit (MINUTES, HOURS, DAYS)

### Inputs

- `indices` - List of index patterns to search
- `query_type` - Query type (bool_should, bool_must, match, terms)
- `query_size` - Maximum results to return
- `conditions` - List of query conditions
- `minimum_should_match` - Minimum matching conditions (for bool_should)

### Condition Types

**Terms:**
```yaml
- type: "terms"
  field: "postgres.sqlstate"
  values: ["22012", "53000"]
```

**Match Phrase:**
```yaml
- type: "match_phrase"
  field: "_raw"
  value: "FATAL"
```

**Match:**
```yaml
- type: "match"
  field: "message"
  value: "error"
```

**Range:**
```yaml
- type: "range"
  field: "response_time"
  range:
    gte: 1000
    lte: 5000
```

### Triggers

- `name` - Trigger name
- `severity` - Alert severity (1=Critical, 2=High, 3=Medium, 4=Low, 5=Info)
- `condition` - Painless script condition
  - `script` - Script source code
  - `lang` - Script language (painless)

### Actions

- `name` - Action name
- `type` - Action type (email, webhook, slack, etc.)
- `destination_id` - OpenSearch destination ID
- `subject_template` - Email subject (Mustache template)
- `message_template_type` - Message format:
  - `html_grouped_by_host` - HTML table grouped by hostname
  - `html_simple` - Simple HTML table
  - `plain_text` - Plain text format
- `throttle` - Action throttling
  - `enabled` - Enable throttling
  - `value` - Throttle duration
  - `unit` - Time unit (MINUTES, HOURS, DAYS)

## Examples

### Critical Error Monitor

```yaml
monitors:
  - name: "Database Critical Errors"
    enabled: true
    schedule:
      interval: 1
      unit: "MINUTES"
    
    inputs:
      indices: ["postgresdata"]
      query_type: "bool_should"
      conditions:
        - type: "terms"
          field: "postgres.sqlstate"
          values: ["22012", "53000", "57000"]
        - type: "match_phrase"
          field: "_raw"
          value: "PANIC"
      minimum_should_match: 1
    
    triggers:
      - name: "Critical Trigger"
        severity: 1
        condition:
          script: "return ctx.results[0].hits.total.value > 0;"
        actions:
          - name: "Email Team"
            destination_id: "email-dest-id"
            subject_template: "CRITICAL: {{ctx.monitor.name}}"
            message_template_type: "html_grouped_by_host"
            throttle:
              enabled: true
              value: 15
              unit: "MINUTES"
```

### Performance Warning Monitor

```yaml
monitors:
  - name: "Slow Query Monitor"
    enabled: true
    schedule:
      interval: 5
      unit: "MINUTES"
    
    inputs:
      indices: ["postgresdata"]
      query_type: "bool_must"
      conditions:
        - type: "range"
          field: "query_time_ms"
          range:
            gte: 5000
        - type: "match"
          field: "log_level"
          value: "WARNING"
    
    triggers:
      - name: "Performance Alert"
        severity: 3
        condition:
          script: "return ctx.results[0].hits.total.value > 10;"
        actions:
          - name: "Notify DBA"
            destination_id: "slack-dest-id"
            subject_template: "Slow queries detected"
            message_template_type: "html_simple"
```

## PostgreSQL SQLSTATE Codes

Common critical SQLSTATEs included in the example config:

- `22012` - Division by zero
- `53000` - Insufficient resources
- `53100` - Disk full
- `53200` - Out of memory
- `53300` - Too many connections
- `57000` - Operator intervention
- `57014` - Query canceled
- `57P01` - Admin shutdown
- `58000` - System error
- `XX000` - Internal error

See [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html) for complete list.

## Working with SQLSTATE in OpenSearch

### Approach 1: Using Grok Ingest Pipeline (Recommended for Structured Fields)

If your logs are in raw format and you want to extract SQLSTATE codes into a structured field, use an OpenSearch ingest pipeline with grok patterns.

#### Create Grok Pipeline

```bash
curl -X PUT 'http://localhost:19200/_ingest/pipeline/postgres-sqlstate-parser' \
  -H 'Content-Type: application/json' \
  -d '{
  "description": "Extract PostgreSQL SQLSTATE codes from log messages",
  "processors": [
    {
      "grok": {
        "field": "_raw",
        "patterns": [
          "e=%{DATA:postgres.sqlstate},",
          "SQLSTATE: %{DATA:postgres.sqlstate}"
        ],
        "ignore_missing": true,
        "ignore_failure": false
      }
    }
  ]
}'
```

#### Apply Pipeline to Index

**Option 1: Set as default pipeline for an index**

```bash
curl -X PUT 'http://localhost:19200/postgresdata/_settings' \
  -H 'Content-Type: application/json' \
  -d '{
  "index.default_pipeline": "postgres-sqlstate-parser"
}'
```

**Option 2: Use pipeline during index creation**

```bash
curl -X PUT 'http://localhost:19200/postgresdata' \
  -H 'Content-Type: application/json' \
  -d '{
  "settings": {
    "index.default_pipeline": "postgres-sqlstate-parser"
  },
  "mappings": {
    "properties": {
      "_raw": { "type": "text" },
      "postgres": {
        "properties": {
          "sqlstate": { "type": "keyword" }
        }
      }
    }
  }
}'
```

**Option 3: Apply during document indexing**

```bash
curl -X POST 'http://localhost:19200/postgresdata/_doc?pipeline=postgres-sqlstate-parser' \
  -H 'Content-Type: application/json' \
  -d '{
  "_raw": "ts=2025-11-19 09:32:46 e=22012, ERROR: division by zero"
}'
```

#### Verify Extraction

```bash
# Search for documents with extracted sqlstate
curl -X GET 'http://localhost:19200/postgresdata/_search?pretty' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": {
    "exists": {
      "field": "postgres.sqlstate"
    }
  },
  "_source": ["_raw", "postgres.sqlstate"],
  "size": 5
}'
```

#### Use Structured Field in Monitor

Once you have the `postgres.sqlstate` field extracted, use the `terms` query:

```yaml
conditions:
  - type: "terms"
    field: "postgres.sqlstate"
    values: ["22012", "53000", "57000"]
```

**Pros:**
- Clean, structured queries using `terms` filter
- Better performance with exact keyword matching
- Easier aggregations and analytics
- Reusable structured field across multiple monitors

**Cons:**
- Requires pipeline setup and configuration
- Pipeline must run on all documents (overhead)
- Requires reindexing if applied to existing data

---

### Approach 2: Pattern Matching on _raw Field (Current Implementation)

If you don't have structured fields or cannot use ingest pipelines, match patterns directly in the `_raw` field:

```yaml
conditions:
  - type: "match_phrase"
    field: "_raw"
    value: "e=22012,"
  
  - type: "match_phrase"
    field: "_raw"
    value: "e=53000,"
  
  - type: "match_phrase"
    field: "_raw"
    value: "PANIC"
  
  - type: "match_phrase"
    field: "_raw"
    value: "FATAL"
```

**Pros:**
- No pipeline setup required
- Works immediately with any log format
- Flexible pattern matching
- No reindexing needed

**Cons:**
- Less efficient than structured field queries
- Multiple conditions needed for multiple codes
- Harder to aggregate or analyze SQLSTATEs
- Pattern must exactly match log format

---

### Comparison Example

**Raw Log:**
```
ts=2025-11-19 09:32:46.508 UTC session=2025-11-19 09:32:46 UTC db=postgres user=postgres pid=77645 host=172.18.0.1(47202) app=psql e=22012, ERROR:  division by zero
```

**Approach 1 (Grok Pipeline):**
- Extracts: `postgres.sqlstate = "22012"`
- Monitor uses: `{"terms": {"postgres.sqlstate": ["22012", "53000"]}}`
- Query performance: Fast (keyword exact match)

**Approach 2 (_raw Pattern Match):**
- No extraction
- Monitor uses: `{"match_phrase": {"_raw": "e=22012,"}}`
- Query performance: Slower (text search with phrase matching)

---

### Recommendation

- **Use Approach 1 (Grok Pipeline)** if:
  - You control the indexing pipeline
  - You need to run multiple monitors on SQLSTATE codes
  - You want to perform analytics/aggregations on error codes
  - Performance is critical

- **Use Approach 2 (_raw Pattern Match)** if:
  - You cannot modify the ingest pipeline
  - You need a quick solution without infrastructure changes
  - Logs are already indexed and reindexing is not feasible
  - Simple pattern matching meets your needs

## Troubleshooting

### Invalid destination_id

Update the `destination_id` in your YAML config with a valid OpenSearch notification destination:

```bash
# List destinations
curl -X GET 'http://localhost:19200/_plugins/_notifications/configs'

# Use the ID in your config
destination_id: "your-actual-destination-id"
```

### Monitor not triggering

- Check the condition script syntax
- Verify indices exist and contain matching data
- Test the query manually in OpenSearch Dashboards
- Check monitor execution history in OpenSearch

### Template rendering issues

- Ensure field names match your index mappings
- Use `{{{triple}}}` braces for raw HTML content
- Test templates in OpenSearch Dashboards alerting UI

## Advanced Features

### Custom Script Conditions

Use Painless scripting for complex trigger logic:

```yaml
condition:
  script: |
    def hits = ctx.results[0].hits.total.value;
    def threshold = 10;
    return hits > threshold && hits < 100;
  lang: "painless"
```

### Multiple Actions per Trigger

```yaml
actions:
  - name: "Email DBA"
    destination_id: "email-dest"
    subject_template: "Alert"
    message_template_type: "html_simple"
  
  - name: "Slack Notification"
    destination_id: "slack-dest"
    subject_template: "Alert"
    message_template_type: "plain_text"
```

### Multiple Monitors

Define multiple monitors in one YAML file:

```yaml
monitors:
  - name: "Production Critical Monitor"
    # ... config ...
  
  - name: "Development Warning Monitor"
    # ... config ...
  
  - name: "Staging Performance Monitor"
    # ... config ...
```

## License

MIT
