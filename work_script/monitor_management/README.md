# OpenSearch Monitor Manager

A lightweight, YAML-driven tool to generate and deploy OpenSearch monitors with advanced filtering capabilities.

## 🚀 Usage

### 1. Generate DSL Only (Dry Run)
Generates the OpenSearch DSL JSON in `dsl_report/` without deploying. Useful for validation.
```bash
python3 generate_monitor_from_yaml.py -out dsl
```

### 2. Deploy Monitor
Creates the notification channel and posts the monitor to OpenSearch.
```bash
python3 generate_monitor_from_yaml.py -out post
```

---

## ⚙️ Configuration (`monitor_config.yaml`)

Define your monitor logic in `monitor_config.yaml`.

### Key Features
*   **`host_pattern`**: Wildcard matching for hostnames (e.g., `patroni*`).
*   **`filters`**: AND conditions (Must match).
*   **`match_any`**: OR conditions (At least one must match).
*   **`exclude_filters`**: NOT conditions (Must not match).
*   **`webhook_url`**: Supports `{{HOST_IP}}` placeholder for dynamic local IP resolution.

### Example Config
```yaml
monitor:
  name: "Production Error Monitor"
  enabled: true
  schedule: { interval: 1, unit: "MINUTES" }
  inputs:
    indices: ["patronidata"]
    time_range: "1h"
    host_pattern: "db-node-*"
    
    # AND condition (Must contain "error")
    filters:
      - field: "message"
        match: "error"
    
    # OR condition (Must contain at least one of these error codes)
    match_any:
      - field: "message"
        match: "e=22012," # Division by zero
      - field: "message"
        match: "e=22000," # Data exception
        
    # NOT condition (Ignore logs with this pattern)
    exclude_filters:
      - field: "message"
        match: "user=replicator,"

  triggers:
    - name: "Critical Error Trigger"
      severity: "1"
      condition_script: "ctx.results[0].hits.total.value > 0"
      actions:
        - name: "Alert Team"
          webhook_url: "http://{{HOST_IP}}:5001/webhook/send-email"
          subject: "Alert: {{ctx.monitor.name}}"
          message_body: |
            {
              "message": "Errors detected: {{ctx.results.0.hits.total.value}}"
            }
```

## 📦 Requirements
*   Python 3
*   `pip install requests pyyaml`
*   OpenSearch running on `localhost:19200` (configurable in script)
