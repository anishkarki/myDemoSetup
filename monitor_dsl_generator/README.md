# OpenSearch Monitor DSL Generator

A modular Python program for generating OpenSearch monitor JSON files from simple YAML DSL configurations.

## Features

- **Simple YAML DSL**: Define monitors in easy-to-read YAML format
- **Modular Architecture**: Separate modules for queries, triggers, actions, and templates
- **Multiple Monitor Types**: Support for basic, aggregation, and frequency-based monitors
- **Template Library**: Pre-built email templates (HTML, plain text)
- **Validation**: Built-in configuration validation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate monitors from DSL
python main.py config/monitors.yml

# Output will be in the monitors/ folder
```

## DSL Format

```yaml
monitors:
  - name: "My Monitor"
    enabled: true
    schedule:
      interval: 1
      unit: "MINUTES"
    
    inputs:
      indices: ["my-index-*"]
      query_type: "bool_should"
      conditions:
        - type: "match_phrase"
          field: "error.level"
          value: "CRITICAL"
    
    triggers:
      - name: "Alert Trigger"
        severity: 1
        condition:
          script: "return ctx.results[0].hits.total.value > 0;"
        actions:
          - name: "Email Alert"
            destination_id: "your-destination-id"
            subject_template: "Alert: {{ctx.monitor.name}}"
            message_template_type: "html_simple"
```

## Usage

```bash
# Generate all monitors
python main.py config/monitors.yml

# Specify output directory
python main.py config/monitors.yml -o /path/to/output

# Validate only (don't generate)
python main.py config/monitors.yml --validate-only
```

## Posting to OpenSearch

```bash
# Post a generated monitor
curl -X POST 'http://localhost:9200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @monitors/my_monitor.json
```
