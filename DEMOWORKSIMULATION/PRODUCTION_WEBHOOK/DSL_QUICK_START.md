# Dynamic DSL Generator - Quick Start Guide

## Overview
The Dynamic DSL Generator creates OpenSearch webhook monitors from a simple YAML configuration file. You can define monitors on the go without writing JSON manually.

---

## Quick Start

### 1. Install Dependencies
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK
source venv/bin/activate
pip install PyYAML
```

### 2. Edit Configuration
```bash
# Edit the YAML config file
vim webhook_monitors_config.yml
```

### 3. Generate Monitors
```bash
python3 generate_webhook_monitors.py webhook_monitors_config.yml
```

### 4. Deploy
```bash
cd generated_webhook_monitors
./deploy_monitors.sh
```

---

## Configuration Guide

### Basic Monitor Structure
```yaml
monitors:
  - name: "My Monitor Name"
    description: "What this monitor does"
    enabled: true
    
    # Indices to search
    indices:
      - "logs*"
      - "metrics*"
    
    # Field to match patterns against
    match_field: "_raw"
    
    # Time window
    time_window: "5m"  # 5 minutes, 1h, 1d, etc.
    
    # Run schedule
    schedule:
      interval: 1
      unit: "MINUTES"  # MINUTES, HOURS, DAYS
    
    # What to match
    error_codes:
      sqlstate_codes:
        - "22012"  # division by zero
        - "23505"  # unique violation
      keywords:
        - "PANIC:"
        - "ERROR:"
    
    # How to group results
    grouping:
      field: "host.name"  # Group by this field
      size: 100  # Max groups
      top_hits_size: 50  # Max entries per group
    
    # When to trigger
    trigger_condition:
      min_groups: 1  # Alert if >= 1 group
      min_errors_per_group: 1  # Alert if >= 1 error per group
    
    # Email settings
    email_config:
      recipients:
        - "alerts@example.com"
      subject: "Alert: Issues Detected"
    
    # Email styling
    email_template:
      alert_title: "🚨 Alert"
      section_icon: "🔴"
      section_title: "Server"
      styles:
        primary_color: "#d9534f"
```

---

## Pattern Matching Options

### 1. SQLSTATE Codes (PostgreSQL)
```yaml
error_codes:
  sqlstate_codes:
    - "22012"  # division_by_zero
    - "23505"  # unique_violation
    - "40P01"  # deadlock_detected
```
**Generated Query**: `match_phrase: { _raw: "e=22012," }`

### 2. Keywords
```yaml
error_codes:
  keywords:
    - "PANIC:"
    - "FATAL:"
    - "OutOfMemoryError"
```
**Generated Query**: `match_phrase: { field: "PANIC:" }`

### 3. Regex Patterns
```yaml
error_codes:
  regex_patterns:
    - "ERROR.*database.*"
    - "CRITICAL.*failed.*"
```
**Generated Query**: `regexp: { field: "ERROR.*database.*" }`

### 4. Wildcard Patterns
```yaml
error_codes:
  wildcard_patterns:
    - "*timeout*"
    - "*connection*lost*"
```
**Generated Query**: `wildcard: { field: "*timeout*" }`

### 5. Mix and Match
```yaml
error_codes:
  sqlstate_codes: ["22012", "23505"]
  keywords: ["PANIC:", "FATAL:"]
  regex_patterns: ["ERROR.*"]
  wildcard_patterns: ["*timeout*"]
```

---

## Grouping Options

### Basic Grouping
```yaml
grouping:
  field: "host.name"  # Required: field to group by
  size: 100  # Max number of groups
  top_hits_size: 50  # Max logs per group
```

### Custom Sort
```yaml
grouping:
  field: "service.name"
  size: 100
  top_hits_size: 20
  sort_field: "@timestamp"
  sort_order: "desc"  # desc or asc
```

### Custom Source Fields
```yaml
grouping:
  field: "host.name"
  source_fields:
    - "_raw"
    - "@timestamp"
    - "host.name"
    - "severity"
    - "user"
```

### Additional Aggregations
```yaml
grouping:
  field: "service.name"
  additional_aggs:
    error_count:
      value_count:
        field: "message"
    avg_response:
      avg:
        field: "response_time"
```

---

## Trigger Conditions

### Simple: Min Groups/Errors
```yaml
trigger_condition:
  min_groups: 2  # Alert if 2+ groups have errors
  min_errors_per_group: 5  # Each group must have 5+ errors
```

### Custom Painless Script
```yaml
trigger_condition:
  custom_script: |
    if (ctx.results[0].aggregations == null) return false;
    def groups = ctx.results[0].aggregations.group_by_field.buckets;
    
    // Alert if total errors > 100
    def totalErrors = groups.sum { it.doc_count };
    return totalErrors > 100;
```

### Advanced Example
```yaml
trigger_condition:
  custom_script: |
    if (ctx.results[0].aggregations == null) return false;
    def groups = ctx.results[0].aggregations.group_by_field.buckets;
    
    // Alert if any group has > 10 errors OR more than 5 groups total
    def criticalGroups = groups.findAll { it.doc_count > 10 };
    return criticalGroups.size() > 0 || groups.size() > 5;
```

---

## Email Configuration

### Basic Email
```yaml
email_config:
  recipients:
    - "dev@example.com"
    - "ops@example.com"
  subject: "Alert: {{ctx.monitor.name}}"
```

### Dynamic Subject
```yaml
email_config:
  recipients: ["alerts@example.com"]
  subject: "🚨 {{ctx.results.0.aggregations.group_by_field.buckets.size}} servers affected"
```

### Template Customization
```yaml
email_template:
  alert_title: "🚨 Production Alert"
  section_icon: "🔴"
  section_title: "Hostname"
  alert_condition: "Critical errors detected"
  styles:
    primary_color: "#d9534f"  # Red
    header_bg: "#d9534f"
    border_color: "#d9534f"
```

### Color Themes

**Red (Critical)**:
```yaml
styles:
  primary_color: "#d9534f"
  header_bg: "#d9534f"
  border_color: "#d9534f"
```

**Orange (Warning)**:
```yaml
styles:
  primary_color: "#f0ad4e"
  header_bg: "#f0ad4e"
  border_color: "#f0ad4e"
```

**Blue (Info)**:
```yaml
styles:
  primary_color: "#5bc0de"
  header_bg: "#5bc0de"
  border_color: "#5bc0de"
```

---

## Advanced Features

### Additional Filters
```yaml
# Add extra query filters
additional_filters:
  - term:
      severity: "error"
  - range:
      response_time:
        gte: 5000
  - exists:
      field: "error_code"
```

### Custom Throttle
```yaml
throttle:
  enabled: true
  value: 30
  unit: "MINUTES"  # MINUTES, HOURS, DAYS
```

### Severity Levels
```yaml
severity: 1  # 1=Critical, 2=High, 3=Medium, 4=Low, 5=Info
```

---

## Real-World Examples

### Example 1: Database Deadlock Monitor
```yaml
- name: "Database Deadlocks"
  indices: ["db-logs*"]
  match_field: "message"
  time_window: "10m"
  
  schedule:
    interval: 5
    unit: "MINUTES"
  
  error_codes:
    sqlstate_codes: ["40P01"]  # deadlock_detected
    keywords: ["deadlock detected"]
  
  grouping:
    field: "database.name"
    size: 50
    top_hits_size: 10
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 2  # 2+ deadlocks in 10 min
  
  email_config:
    recipients: ["dba@company.com"]
    subject: "⚠️ Deadlocks on {{ctx.results.0.aggregations.group_by_field.buckets.size}} database(s)"
  
  throttle:
    enabled: true
    value: 15
    unit: "MINUTES"
```

### Example 2: API Error Rate Monitor
```yaml
- name: "High API Error Rate"
  indices: ["api-logs*"]
  match_field: "http.status_code"
  time_window: "5m"
  
  error_codes:
    regex_patterns:
      - "5[0-9]{2}"  # 5xx errors
  
  grouping:
    field: "api.endpoint"
    size: 100
    top_hits_size: 20
    additional_aggs:
      error_rate:
        value_count:
          field: "http.status_code"
  
  trigger_condition:
    custom_script: |
      def groups = ctx.results[0].aggregations.group_by_field.buckets;
      return groups.any { it.doc_count > 50 };  // 50+ errors in 5 min
  
  email_config:
    recipients: ["oncall@company.com"]
    subject: "🔥 API Errors: {{ctx.results.0.aggregations.group_by_field.buckets.size}} endpoints affected"
```

### Example 3: Security Alert Monitor
```yaml
- name: "Failed Login Attempts"
  indices: ["auth-logs*"]
  match_field: "event.action"
  time_window: "15m"
  
  error_codes:
    keywords:
      - "authentication_failed"
      - "invalid_credentials"
  
  grouping:
    field: "source.ip"
    size: 100
    top_hits_size: 30
    source_fields:
      - "user.name"
      - "source.ip"
      - "@timestamp"
      - "event.action"
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 10  # 10+ failed attempts from same IP
  
  email_config:
    recipients: ["security@company.com"]
    subject: "🔒 Security Alert: {{ctx.results.0.aggregations.group_by_field.buckets.size}} IPs with failed logins"
  
  email_template:
    alert_title: "🔒 Security Alert"
    section_icon: "⚠️"
    section_title: "Source IP"
    styles:
      primary_color: "#e74c3c"
```

---

## Tips & Best Practices

### 1. Start Simple
Begin with basic monitors and add complexity as needed.

### 2. Test Time Windows
Adjust `time_window` based on your log volume:
- High volume: 1-5 minutes
- Medium volume: 5-15 minutes
- Low volume: 30+ minutes

### 3. Tune Throttle
Set throttle to prevent alert fatigue:
- Critical alerts: 5-10 minutes
- Warning alerts: 15-30 minutes
- Info alerts: 1+ hours

### 4. Group Wisely
Choose grouping fields that help identify issues:
- `host.name` - Infrastructure issues
- `service.name` - Application issues
- `user.name` - User-specific issues
- `error.code` - Error type analysis

### 5. Monitor Monitor Performance
- Keep `group.size` reasonable (< 200)
- Limit `top_hits_size` for large datasets
- Use specific indices (avoid `*` when possible)

---

## Troubleshooting

### Monitor Not Generating
```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('webhook_monitors_config.yml'))"

# Check for errors
python3 generate_webhook_monitors.py webhook_monitors_config.yml 2>&1 | grep -i error
```

### Deployment Fails
```bash
# Check OpenSearch connectivity
curl http://localhost:19200/_cluster/health

# Check notification channel
curl http://localhost:19200/_plugins/_notifications/configs

# Manually create channel first
# Then update channel_id in config
```

### Monitor Not Triggering
```bash
# Test the query directly
curl -X GET 'http://localhost:19200/INDEX/_search?pretty' -d '{
  "query": { ... copy from generated JSON ... }
}'

# Execute monitor manually
curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors/MONITOR_ID/_execute'
```

---

## Next Steps

1. **Start with examples**: Use the provided config as template
2. **Test locally**: Generate and review JSON before deploying
3. **Deploy incrementally**: Start with one monitor, then add more
4. **Monitor the monitors**: Check if alerts are too noisy or too quiet
5. **Iterate**: Adjust thresholds, groupings, and patterns based on feedback

---

**Happy Monitoring! 🚀**
