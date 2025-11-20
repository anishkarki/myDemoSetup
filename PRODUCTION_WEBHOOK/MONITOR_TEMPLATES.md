# Monitor Template - Copy and Customize

# Quick copy-paste templates for common monitoring scenarios

---

## Template 1: Basic Error Monitor
```yaml
- name: "Your Monitor Name Here"
  description: "What this monitor does"
  enabled: true
  
  indices:
    - "your-index*"
  
  match_field: "_raw"  # or "message", "log", etc.
  time_window: "5m"
  
  schedule:
    interval: 1
    unit: "MINUTES"
  
  error_codes:
    keywords:
      - "ERROR"
      - "CRITICAL"
  
  grouping:
    field: "host.name"
    size: 100
    top_hits_size: 50
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 1
  
  trigger_name: "Error Detected"
  severity: 1
  action_name: "Send Alert"
  
  throttle:
    enabled: true
    value: 5
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "your-email@example.com"
    subject: "🚨 Alert: Errors on {{ctx.results.0.aggregations.group_by_field.buckets.size}} host(s)"
  
  email_template:
    alert_title: "🚨 Alert"
    section_icon: "🔴"
    section_title: "Host"
    alert_condition: "Errors detected"
    styles:
      primary_color: "#d9534f"
      header_bg: "#d9534f"
      border_color: "#d9534f"
```

---

## Template 2: Frequency-Based Monitor
```yaml
- name: "High Frequency Error Monitor"
  description: "Alert when same error repeats multiple times"
  enabled: true
  
  indices:
    - "logs*"
  
  match_field: "message"
  time_window: "10m"
  
  schedule:
    interval: 2
    unit: "MINUTES"
  
  error_codes:
    keywords:
      - "timeout"
      - "connection refused"
  
  grouping:
    field: "service.name"
    size: 50
    top_hits_size: 30
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 10  # 10+ occurrences
  
  trigger_name: "High Frequency Alert"
  severity: 2
  action_name: "Send Frequency Alert"
  
  throttle:
    enabled: true
    value: 15
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "ops@example.com"
    subject: "⚠️ Repeated Errors: {{ctx.results.0.aggregations.group_by_field.buckets.size}} service(s)"
  
  email_template:
    alert_title: "⚠️ High Frequency Alert"
    section_icon: "🟡"
    section_title: "Service"
    alert_condition: "Same error repeated 10+ times in 10 minutes"
    styles:
      primary_color: "#f0ad4e"
      header_bg: "#f0ad4e"
      border_color: "#f0ad4e"
```

---

## Template 3: Database Monitor
```yaml
- name: "Database Error Monitor"
  description: "Monitor database errors and performance issues"
  enabled: true
  
  indices:
    - "db-logs*"
  
  match_field: "_raw"
  time_window: "5m"
  
  schedule:
    interval: 1
    unit: "MINUTES"
  
  error_codes:
    sqlstate_codes:
      - "22012"  # division_by_zero
      - "23505"  # unique_violation
      - "40P01"  # deadlock
      - "53200"  # out_of_memory
    keywords:
      - "PANIC:"
      - "FATAL:"
  
  grouping:
    field: "host.name"
    size: 100
    top_hits_size: 50
    source_fields:
      - "_raw"
      - "@timestamp"
      - "host.name"
      - "database.name"
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 1
  
  trigger_name: "Database Error"
  severity: 1
  action_name: "Alert DBA"
  
  throttle:
    enabled: true
    value: 10
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "dba@example.com"
      - "oncall@example.com"
    subject: "🗄️ Database Errors: {{ctx.results.0.aggregations.group_by_field.buckets.size}} host(s)"
  
  email_template:
    alert_title: "🗄️ Database Alert"
    section_icon: "🔴"
    section_title: "Database Host"
    alert_condition: "Database errors detected"
    styles:
      primary_color: "#d9534f"
      header_bg: "#d9534f"
      border_color: "#d9534f"
```

---

## Template 4: Application Error Monitor
```yaml
- name: "Application Error Monitor"
  description: "Monitor application exceptions and errors"
  enabled: true
  
  indices:
    - "app-logs*"
  
  match_field: "message"
  time_window: "5m"
  
  schedule:
    interval: 1
    unit: "MINUTES"
  
  error_codes:
    regex_patterns:
      - "Exception.*"
      - "Error.*"
    keywords:
      - "OutOfMemoryError"
      - "NullPointerException"
      - "StackOverflow"
  
  grouping:
    field: "service.name"
    size: 50
    top_hits_size: 20
    source_fields:
      - "message"
      - "@timestamp"
      - "service.name"
      - "log.level"
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 3
  
  trigger_name: "Application Error"
  severity: 2
  action_name: "Alert Developers"
  
  throttle:
    enabled: true
    value: 10
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "dev-team@example.com"
    subject: "💥 App Errors: {{ctx.results.0.aggregations.group_by_field.buckets.size}} service(s)"
  
  email_template:
    alert_title: "💥 Application Alert"
    section_icon: "⚠️"
    section_title: "Service"
    alert_condition: "Application exceptions detected"
    styles:
      primary_color: "#e67e22"
      header_bg: "#e67e22"
      border_color: "#e67e22"
```

---

## Template 5: Security Monitor
```yaml
- name: "Security Event Monitor"
  description: "Monitor security events and suspicious activity"
  enabled: true
  
  indices:
    - "security-logs*"
    - "auth-logs*"
  
  match_field: "event.action"
  time_window: "15m"
  
  schedule:
    interval: 5
    unit: "MINUTES"
  
  error_codes:
    keywords:
      - "authentication_failed"
      - "authorization_denied"
      - "suspicious_activity"
      - "brute_force"
  
  grouping:
    field: "source.ip"
    size: 100
    top_hits_size: 50
    source_fields:
      - "user.name"
      - "source.ip"
      - "@timestamp"
      - "event.action"
      - "geo.country"
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 5  # 5+ failed attempts
  
  trigger_name: "Security Alert"
  severity: 1
  action_name: "Alert Security Team"
  
  throttle:
    enabled: true
    value: 30
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "security@example.com"
      - "soc@example.com"
    subject: "🔒 Security Alert: {{ctx.results.0.aggregations.group_by_field.buckets.size}} source(s)"
  
  email_template:
    alert_title: "🔒 Security Alert"
    section_icon: "🚨"
    section_title: "Source IP"
    alert_condition: "Multiple failed authentication attempts detected"
    styles:
      primary_color: "#e74c3c"
      header_bg: "#e74c3c"
      border_color: "#e74c3c"
```

---

## Template 6: Performance Monitor
```yaml
- name: "Performance Degradation Monitor"
  description: "Monitor slow responses and performance issues"
  enabled: true
  
  indices:
    - "metrics*"
  
  match_field: "message"
  time_window: "10m"
  
  schedule:
    interval: 5
    unit: "MINUTES"
  
  error_codes:
    keywords:
      - "slow query"
      - "timeout"
      - "high latency"
  
  additional_filters:
    - range:
        response_time:
          gte: 5000  # 5 seconds
  
  grouping:
    field: "service.name"
    size: 50
    top_hits_size: 20
    additional_aggs:
      avg_response:
        avg:
          field: "response_time"
      max_response:
        max:
          field: "response_time"
  
  trigger_condition:
    custom_script: |
      if (ctx.results[0].aggregations == null) return false;
      def groups = ctx.results[0].aggregations.group_by_field.buckets;
      // Alert if any service has avg response > 5 seconds
      return groups.any { it.avg_response.value > 5000 };
  
  trigger_name: "Performance Issue"
  severity: 3
  action_name: "Alert Ops Team"
  
  throttle:
    enabled: true
    value: 20
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "ops@example.com"
    subject: "⏱️ Performance: {{ctx.results.0.aggregations.group_by_field.buckets.size}} service(s) slow"
  
  email_template:
    alert_title: "⏱️ Performance Alert"
    section_icon: "🐌"
    section_title: "Service"
    alert_condition: "Slow response times detected"
    styles:
      primary_color: "#f39c12"
      header_bg: "#f39c12"
      border_color: "#f39c12"
```

---

## Template 7: Infrastructure Monitor
```yaml
- name: "Infrastructure Alert Monitor"
  description: "Monitor infrastructure issues (disk, CPU, memory)"
  enabled: true
  
  indices:
    - "system-metrics*"
  
  match_field: "message"
  time_window: "5m"
  
  schedule:
    interval: 2
    unit: "MINUTES"
  
  error_codes:
    keywords:
      - "disk full"
      - "high CPU"
      - "out of memory"
      - "network unreachable"
  
  grouping:
    field: "host.name"
    size: 100
    top_hits_size: 30
  
  trigger_condition:
    min_groups: 1
    min_errors_per_group: 1
  
  trigger_name: "Infrastructure Alert"
  severity: 1
  action_name: "Alert SRE"
  
  throttle:
    enabled: true
    value: 15
    unit: "MINUTES"
  
  email_config:
    recipients:
      - "sre@example.com"
      - "oncall@example.com"
    subject: "🖥️ Infrastructure: {{ctx.results.0.aggregations.group_by_field.buckets.size}} host(s) in trouble"
  
  email_template:
    alert_title: "🖥️ Infrastructure Alert"
    section_icon: "⚠️"
    section_title: "Hostname"
    alert_condition: "Infrastructure resource issues detected"
    styles:
      primary_color: "#c0392b"
      header_bg: "#c0392b"
      border_color: "#c0392b"
```

---

## Quick Customization Checklist

When creating a new monitor from template:

- [ ] Change `name` to descriptive monitor name
- [ ] Update `description` 
- [ ] Set correct `indices` patterns
- [ ] Choose appropriate `match_field`
- [ ] Adjust `time_window` for your use case
- [ ] Set `schedule.interval` based on urgency
- [ ] Define `error_codes` (keywords/regex/sqlstate)
- [ ] Set `grouping.field` to meaningful dimension
- [ ] Tune `trigger_condition` thresholds
- [ ] Update `email_config.recipients`
- [ ] Customize `email_config.subject`
- [ ] Adjust `throttle` settings
- [ ] Pick appropriate severity (1-5)
- [ ] Customize email template colors/icons

---

## Color Palette Reference

```yaml
# Red - Critical/Emergency
primary_color: "#d9534f"

# Orange - Warning
primary_color: "#f0ad4e"

# Yellow - Caution
primary_color: "#f39c12"

# Blue - Info
primary_color: "#5bc0de"

# Green - Success
primary_color: "#5cb85c"

# Purple - Custom
primary_color: "#9b59b6"

# Dark Red - Security
primary_color: "#e74c3c"
```

---

## Icon Reference

```yaml
# Severity Icons
section_icon: "🔴"  # Critical
section_icon: "🟡"  # Warning
section_icon: "🔵"  # Info
section_icon: "🟢"  # Low priority

# Type Icons
section_icon: "🗄️"  # Database
section_icon: "💥"  # Application crash
section_icon: "⚠️"  # Generic warning
section_icon: "🚨"  # Security
section_icon: "🔒"  # Authentication
section_icon: "🖥️"  # Infrastructure
section_icon: "🌐"  # Network
section_icon: "⏱️"  # Performance
section_icon: "📊"  # Metrics
section_icon: "🐌"  # Slow
```

---

Save this file as reference and copy templates as needed!
