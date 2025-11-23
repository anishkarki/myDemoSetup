# 🎯 Dynamic DSL Generator for OpenSearch Webhook Monitors

**Transform YAML configurations into production-ready OpenSearch monitors in seconds.**

---

## 🚀 Quick Start (60 Seconds)

```bash
# 1. Activate environment
cd /home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK
source venv/bin/activate

# 2. Create/edit your config (or use existing)
vim webhook_monitors_config.yml

# 3. Generate monitors
python3 generate_webhook_monitors.py webhook_monitors_config.yml

# 4. Deploy
cd generated_webhook_monitors
./deploy_monitors.sh

# ✅ Done! Monitors are live.
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **DSL_QUICK_START.md** | Comprehensive usage guide with examples |
| **MONITOR_TEMPLATES.md** | 7 ready-to-use monitor templates |
| **DSL_SYSTEM_SUMMARY.md** | Complete system overview and capabilities |
| **DEPLOYMENT_SUMMARY.md** | Production deployment guide |

---

## 📁 What's Included

### Core System
- **generate_webhook_monitors.py** - Main DSL generator
- **webhook_monitors_config.yml** - Main configuration file (3 monitors)
- **smtp_webhook_server.py** - Flask webhook server for SMTP
- **venv/** - Python virtual environment

### Examples
- **example_quick_monitor.yml** - Minimal example (1 monitor)
- **insert_test_data.sh** - Test data generator
- **MONITOR_TEMPLATES.md** - Template library

### Generated (Sample)
- **generated_webhook_monitors/** - Example output
  - postgres_critical_errors___production.json
  - postgres_high_frequency_errors.json
  - postgres_connection_issues.json
  - deploy_monitors.sh

---

## ⚡ Features

### Pattern Matching
- ✅ PostgreSQL SQLSTATE codes
- ✅ Keyword matching
- ✅ Regex patterns
- ✅ Wildcard patterns
- ✅ Mixed patterns

### Grouping & Aggregation
- ✅ Group by any field
- ✅ Top hits per group
- ✅ Custom aggregations
- ✅ Multi-level grouping

### Triggering
- ✅ Threshold-based
- ✅ Custom Painless scripts
- ✅ Multi-condition logic

### Email Templates
- ✅ HTML formatting
- ✅ Grouped sections
- ✅ Color themes
- ✅ Custom icons
- ✅ Responsive design

### Deployment
- ✅ Auto-generated scripts
- ✅ Notification channel creation
- ✅ Batch deployment
- ✅ Error handling

---

## 🎯 Use Cases

### Database Monitoring
```yaml
error_codes:
  sqlstate_codes: ["22012", "40P01", "53200"]
grouping:
  field: "host.name"
```

### Application Errors
```yaml
error_codes:
  regex_patterns: ["Exception.*", "Error.*"]
  keywords: ["OutOfMemoryError"]
grouping:
  field: "service.name"
```

### Security Events
```yaml
error_codes:
  keywords: ["authentication_failed", "brute_force"]
grouping:
  field: "source.ip"
trigger_condition:
  min_errors_per_group: 10
```

### Performance Monitoring
```yaml
additional_filters:
  - range:
      response_time:
        gte: 5000
trigger_condition:
  custom_script: |
    return groups.any { it.avg_response.value > 5000 };
```

---

## 📖 Examples

### Create Monitor in 2 Minutes

```yaml
# minimal_config.yml
opensearch_url: "http://localhost:19200"
output_directory: "./my_monitors"

notification_channel:
  channel_id: "YOUR_CHANNEL_ID"
  webhook_url: "http://localhost:5001/webhook/send-email"

monitors:
  - name: "Error Monitor"
    indices: ["logs*"]
    match_field: "message"
    error_codes:
      keywords: ["ERROR"]
    grouping:
      field: "host.name"
    email_config:
      recipients: ["alerts@example.com"]
```

```bash
python3 generate_webhook_monitors.py minimal_config.yml
cd my_monitors && ./deploy_monitors.sh
```

---

## 🔧 Configuration Structure

```yaml
# Global settings
opensearch_url: "http://localhost:19200"
output_directory: "./generated_webhook_monitors"

# Webhook configuration
notification_channel:
  channel_id: ""  # Empty = auto-create
  name: "Webhook Channel"
  webhook_url: "http://192.168.1.222:5001/webhook/send-email"

# Monitors
monitors:
  - name: "Monitor Name"
    description: "What it does"
    enabled: true
    
    # Where to search
    indices: ["logs*"]
    match_field: "_raw"
    time_window: "5m"
    
    # When to run
    schedule:
      interval: 1
      unit: "MINUTES"
    
    # What to match
    error_codes:
      sqlstate_codes: ["22012"]
      keywords: ["ERROR"]
      regex_patterns: ["Exception.*"]
    
    # How to group
    grouping:
      field: "host.name"
      size: 100
      top_hits_size: 50
    
    # When to alert
    trigger_condition:
      min_groups: 1
      min_errors_per_group: 1
    
    # Who to notify
    email_config:
      recipients: ["team@example.com"]
      subject: "Alert: {{buckets.size}} affected"
    
    # Throttle
    throttle:
      enabled: true
      value: 5
      unit: "MINUTES"
```

---

## 🎨 Customization

### Change Colors
```yaml
email_template:
  styles:
    primary_color: "#d9534f"  # Red
    header_bg: "#d9534f"
    border_color: "#d9534f"
```

### Change Icons
```yaml
email_template:
  alert_title: "🚨 Alert"
  section_icon: "🔴"
  section_title: "Server"
```

### Custom Trigger Logic
```yaml
trigger_condition:
  custom_script: |
    def groups = ctx.results[0].aggregations.group_by_field.buckets;
    def total = groups.sum { it.doc_count };
    return total > 100 || groups.size() > 10;
```

---

## 🛠️ Maintenance

### Update Monitors
```bash
# Edit config
vim webhook_monitors_config.yml

# Regenerate
python3 generate_webhook_monitors.py webhook_monitors_config.yml

# Review changes
git diff generated_webhook_monitors/

# Deploy
cd generated_webhook_monitors && ./deploy_monitors.sh
```

### Add New Monitor
```bash
# Copy template from MONITOR_TEMPLATES.md
# Paste into webhook_monitors_config.yml
# Regenerate and deploy
```

---

## 📊 Comparison

| Task | Manual JSON | DSL Generator |
|------|-------------|---------------|
| Create monitor | 30-60 min | 2-5 min |
| Error prone | High | Low |
| Readable | No | Yes |
| Reusable | Hard | Easy |
| Update | Manual edit | Regenerate |
| Deploy | Manual curl | Auto script |

---

## 🎓 Learn More

1. **Start**: Read DSL_QUICK_START.md
2. **Practice**: Use example_quick_monitor.yml
3. **Templates**: Browse MONITOR_TEMPLATES.md
4. **Advanced**: Create custom Painless scripts
5. **Master**: Build complex multi-condition monitors

---

## ✅ Prerequisites

- Python 3.x
- PyYAML (`pip install PyYAML`)
- OpenSearch cluster
- Webhook server (included)

---

## 🚦 Status

- ✅ Generator: Working
- ✅ Templates: 7 included
- ✅ Documentation: Complete
- ✅ Webhook server: Running
- ✅ Test data: Available
- ✅ Deployment scripts: Auto-generated

---

## 📞 Quick Commands

```bash
# Generate
python3 generate_webhook_monitors.py webhook_monitors_config.yml

# Deploy
cd generated_webhook_monitors && ./deploy_monitors.sh

# Test
./insert_test_data.sh
curl -X POST http://localhost:19200/_plugins/_alerting/monitors/ID/_execute

# Check
curl http://localhost:19200/_plugins/_alerting/monitors/_search?pretty
curl http://100.80.115.61:8025/api/v2/messages
```

---

## 📂 Directory Structure

```
PRODUCTION_WEBHOOK/
├── generate_webhook_monitors.py    ⭐ Main generator
├── webhook_monitors_config.yml     ⭐ Main config (3 monitors)
├── example_quick_monitor.yml       ⭐ Quick example (1 monitor)
│
├── DSL_QUICK_START.md             📖 Usage guide
├── MONITOR_TEMPLATES.md            📖 Template library
├── DSL_SYSTEM_SUMMARY.md          📖 System overview
├── DEPLOYMENT_SUMMARY.md          📖 Deployment guide
│
├── smtp_webhook_server.py         🔧 Webhook server
├── insert_test_data.sh            🔧 Test data
│
├── generated_webhook_monitors/    📁 Generated output
│   ├── *.json                     📄 Monitor files
│   ├── deploy_monitors.sh         🚀 Deployment script
│   └── README.md                  📖 Generated docs
│
└── venv/                          🐍 Python environment
```

---

**🎉 Start creating monitors in minutes, not hours!**

```bash
python3 generate_webhook_monitors.py webhook_monitors_config.yml
```
