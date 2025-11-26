# OpenSearch Monitor Generator & Alerting System

This project provides a Python-based tool to generate and deploy OpenSearch Alerting Monitors based on a YAML configuration. It is designed to detect specific PostgreSQL error codes (SQLSTATE) in logs and trigger email alerts.

## Components

1.  **`monitor_generator.py`**: The main script that parses the configuration and interacts with the OpenSearch API to create monitors.
2.  **`monitor_config.yml`**: The configuration file defining monitor logic, triggers, and email templates.
3.  **`inject_test_log.py`**: A utility script to inject fake log entries into OpenSearch for testing purposes.

## Prerequisites

*   Python 3.x
*   `requests` library (`pip install requests`)
*   Access to an OpenSearch cluster with the Alerting plugin enabled.
*   A configured Email Destination in OpenSearch (e.g., Mailhog).

## Configuration (`monitor_config.yml`)

The configuration file allows you to define multiple monitors. Each monitor has:
*   **name**: Display name in OpenSearch.
*   **schedule**: Cron-like schedule (e.g., `period: { interval: 5, unit: MINUTES }`).
*   **query**: The search query (supports wildcards).
*   **triggers**: Conditions to fire alerts (e.g., `count > 0`).
*   **actions**: Notification channels (Email) and templates.

Example:
```yaml
monitors:
  - name: "Postgres Internal Errors (Class XX)"
    query: "*xx???*"  # Matches XX000, XX001, etc.
    schedule:
      period:
        interval: 5
        unit: MINUTES
    triggers:
      - name: "Internal Error Trigger"
        severity: "1"
        condition_script: "ctx.results[0].hits.total.value > 0"
        actions:
          - name: "Send Email Action"
            destination_id: "YOUR_DESTINATION_ID"
            subject: "CRITICAL: Postgres Internal Error Detected"
            message_template: |
              Monitor {{ctx.monitor.name}} just entered alert status.
              Hits: {{ctx.results.0.hits.total.value}}
```

## Usage

### 1. Deploy Monitors

To create or update the monitors in OpenSearch, run:

```bash
python3 monitor_generator.py --create
```

This will:
*   Read `monitor_config.yml`.
*   Generate the OpenSearch DSL JSON.
*   POST the monitors to the OpenSearch API.

### 2. Generate DSL (Dry Run)

To see the generated JSON without creating the monitors:

```bash
python3 monitor_generator.py --generate-dsl
```

### 3. Test Alerts

To verify the system is working, use the injection script to send fake logs:

```bash
python3 inject_test_log.py
```

This script injects logs with SQL codes `XX000`, `08006`, and `58P01`. The monitors (running every 5 minutes) should pick these up and send alerts.

## Troubleshooting

*   **No Alerts?**
    *   Check if the monitors are created: `curl -X GET "http://localhost:9200/_plugins/_alerting/monitors"`
    *   Check the `destination_id` in `monitor_config.yml`. It must match an existing Destination in OpenSearch.
    *   Verify the index name in `monitor_generator.py` matches your data (default: `patronidata`).

*   **Case Sensitivity**: The generator automatically handles case-insensitive wildcard searches for SQL codes.
