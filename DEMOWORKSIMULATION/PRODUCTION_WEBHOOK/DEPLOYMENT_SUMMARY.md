# Production Webhook Deployment - Complete Summary

## Overview
Custom webhook implementation for OpenSearch alerting with SMTP email delivery, replacing built-in email destination for full control over email formatting and delivery.

---

## Architecture Components

### 1. Flask SMTP Webhook Server
- **Location**: `/home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK/smtp_webhook_server.py`
- **Endpoint**: `http://192.168.1.222:5001/webhook/send-email`
- **Health Check**: `http://192.168.1.222:5001/health`
- **Process**: Running in background (PID in `webhook_server.pid`)
- **Virtual Environment**: `venv/` with Flask installed
- **Logs**: `webhook_server.log`

**Key Features**:
- Accepts JSON payload: `{"recipients": [...], "subject": "...", "message": "HTML"}`
- Detects HTML vs plain text emails
- Connects to Mailhog SMTP (100.80.115.61:1025)
- Returns status and delivery confirmation

### 2. OpenSearch Notification Channel
- **Channel ID**: `Pt_ioJoBd6nYLt6SZJOX`
- **Name**: "SMTP Webhook Channel (Host IP)"
- **Type**: webhook
- **URL**: `http://192.168.1.222:5001/webhook/send-email`
- **Method**: POST
- **Headers**: `Content-Type: application/json`

**Note**: Uses host IP (192.168.1.222) instead of localhost because OpenSearch may run in different network context.

### 3. OpenSearch Monitor
- **Monitor ID**: `St_joJoBd6nYLt6SP5On`
- **Name**: "Postgres Critical Errors - Webhook v2"
- **Schedule**: Every 1 minute
- **Time Window**: Last 2 minutes
- **Indices**: `postgresdata`, `postgresd*`
- **Throttle**: 5 minutes

**Query Structure**:
- **Type**: Aggregation-based monitoring
- **Error Matching**: 38 critical SQLSTATE codes via `_raw` field patterns
- **Grouping**: Terms aggregation on `host.name` (size: 100)
- **Log Retrieval**: Top hits aggregation (size: 100, sorted by @timestamp desc)

**Critical Error Codes Monitored**:
```
08xxx - Connection Exceptions (08000, 08006, 08001, 08004)
22xxx - Data Exceptions (22012, 22003, 22P01)
23xxx - Integrity Constraint Violations (23000, 23503, 23505)
28xxx - Invalid Authorization (28000, 28P01)
40xxx - Transaction Rollback (40000, 40001, 40P01)
53xxx - Insufficient Resources (53000, 53100, 53200, 53300, 53400)
54xxx - Program Limit Exceeded (54000, 54001)
55xxx - Object Not in Prerequisite State (55000, 55P03)
57xxx - Operator Intervention (57000, 57014, 57P01, 57P02, 57P04)
58xxx - System Error (58000, 58030)
F0xxx - Configuration File Error (F0000, F0001)
XXxxx - Internal Error (XX000, XX001, XX002)
PANIC/FATAL keywords
```

**Trigger Condition**:
```painless
if (ctx.results[0].aggregations == null) return false;
def hostBuckets = ctx.results[0].aggregations.group_by_hostname.buckets;
return hostBuckets.size() > 0;
```

### 4. Email Template
**Style Features**:
- Red alert theme (#d9534f)
- Hostname-section based layout (no tables)
- Monospace font for log entries
- Alternating row colors (#fff / #fff9f9)
- Responsive design with proper spacing
- Emoji indicators: 🚨 for alerts, 🔴 for hostnames

**Template Structure**:
```
🚨 Postgres Critical Alert
├── Monitor metadata (name, trigger, time window)
├── Hostname Section 1
│   ├── 🔴 Hostname: db-server-01 — 3 critical error(s)
│   └── Log entries (timestamp + full raw log)
├── Hostname Section 2
│   ├── 🔴 Hostname: db-server-02 — 3 critical error(s)
│   └── Log entries
└── Hostname Section 3
    ├── 🔴 Hostname: db-server-03 — 3 critical error(s)
    └── Log entries
```

---

## Files Created

### Configuration Files
- `webhook_monitor.json` - Initial monitor definition
- `webhook_monitor_v2.json` - Monitor with updated channel ID
- `smtp_webhook_server.py` - Flask webhook server
- `README.md` - Setup and usage instructions
- `create_webhook_monitor.sh` - Monitor creation script (deprecated)
- `insert_test_data.sh` - Test data generation script

### Test Results
- `webhook_email_production.html` - Raw email from Mailhog (base64 encoded)
- `webhook_email_clean.html` - Decoded HTML email
- `webhook_server.log` - Server request/response logs
- `webhook_server.pid` - Process ID file

---

## Verified Test Results

### Test Execution
**Date**: 2025-11-20 10:50:56 UTC

**Test Data**: 9 critical errors across 3 hostnames
- `db-server-01`: 3 errors (22012, 22003, 23505)
- `db-server-02`: 3 errors (22012, 22003, 23505)
- `db-server-03`: 3 errors (22012, 22003, 23505)

### Webhook Flow Verification
✅ Monitor triggered successfully  
✅ Webhook received POST request from OpenSearch  
✅ JSON payload correctly formatted with recipients, subject, message  
✅ HTML email parsed and sent via SMTP  
✅ Email delivered to Mailhog (both dev1@test.local and dev2@test.local)  
✅ Email subject: "🚨 Postgres CRITICAL: Errors Detected - 3 hosts affected"  
✅ HTML rendering verified with 3 hostname sections  
✅ All 9 log entries displayed with correct grouping  

### Webhook Server Logs
```
INFO: Received webhook request: {
  "recipients": ["dev1@test.local", "dev2@test.local"],
  "subject": "🚨 Postgres CRITICAL: Errors Detected - 3 hosts affected",
  "message": "<html>...</html>"
}
INFO: Email sent successfully to ['dev1@test.local', 'dev2@test.local']
172.18.0.7 - - [20/Nov/2025 20:50:56] "POST /webhook/send-email HTTP/1.1" 200 -
```

---

## Deployment Steps

### Initial Setup
```bash
# 1. Create virtual environment and install Flask
cd /home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK
python3 -m venv venv
source venv/bin/activate
pip install Flask

# 2. Start webhook server
python3 smtp_webhook_server.py &
# Server PID saved to webhook_server.pid

# 3. Verify server health
curl http://192.168.1.222:5001/health
# Response: {"status": "healthy"}
```

### OpenSearch Configuration
```bash
# 4. Create notification channel
curl -X POST 'http://localhost:19200/_plugins/_notifications/configs' \
  -H 'Content-Type: application/json' \
  -d '{
    "config": {
      "name": "SMTP Webhook Channel (Host IP)",
      "description": "Custom webhook for SMTP email delivery using host IP",
      "config_type": "webhook",
      "is_enabled": true,
      "webhook": {
        "url": "http://192.168.1.222:5001/webhook/send-email",
        "method": "POST",
        "header_params": {
          "Content-Type": "application/json"
        }
      }
    }
  }'
# Response: {"config_id": "Pt_ioJoBd6nYLt6SZJOX"}

# 5. Create monitor
curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @webhook_monitor_v2.json
# Response: {"_id": "St_joJoBd6nYLt6SP5On"}

# 6. Execute monitor for testing
curl -X POST "http://localhost:19200/_plugins/_alerting/monitors/St_joJoBd6nYLt6SP5On/_execute"
```

### Test Data Generation
```bash
# 7. Insert test data
./insert_test_data.sh
# Creates 9 critical errors across 3 hostnames with current timestamp

# 8. Execute monitor and verify
curl -X POST "http://localhost:19200/_plugins/_alerting/monitors/St_joJoBd6nYLt6SP5On/_execute"

# 9. Check webhook logs
tail -f webhook_server.log

# 10. Verify email in Mailhog
curl "http://100.80.115.61:8025/api/v2/messages?limit=1"
```

---

## Key Differences from Built-in Email Destination

### Advantages of Webhook Approach
1. **Full Control**: Custom logic for email delivery, formatting, retry mechanisms
2. **Flexibility**: Can add logging, analytics, custom headers, attachments
3. **Integration**: Easy to integrate with other systems (PagerDuty, Slack, etc.)
4. **Debugging**: Clear logs of all requests and responses
5. **Testing**: Can mock SMTP server for testing
6. **Scalability**: Can load balance across multiple webhook servers

### Technical Differences
- **Old Approach**: Monitor → Email Destination → SMTP
- **New Approach**: Monitor → Notification Channel → Webhook → Flask Server → SMTP

### Configuration Complexity
- **Built-in**: Simple, but limited customization
- **Webhook**: More setup, but unlimited flexibility

---

## Troubleshooting

### Common Issues

**1. Connection Refused**
```
Error: "Connect to http://localhost:5001 failed: Connection refused"
```
**Solution**: Use host IP (192.168.1.222) instead of localhost in notification channel URL

**2. Webhook Not Receiving Requests**
```bash
# Check if server is running
curl http://192.168.1.222:5001/health

# Check logs
tail -f webhook_server.log

# Restart server
cd /home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK
source venv/bin/activate
python3 smtp_webhook_server.py &
```

**3. Monitor Not Triggering**
```bash
# Check if data exists in index
curl -X GET "http://localhost:19200/postgresdata/_search" -d '{
  "query": {"bool": {"should": [{"match_phrase": {"_raw": "e=22012,"}}]}},
  "size": 1
}'

# Check aggregation results
curl -X POST "http://localhost:19200/_plugins/_alerting/monitors/St_joJoBd6nYLt6SP5On/_execute" \
  | jq '.input_results.results[0].aggregations.group_by_hostname.buckets'
```

**4. Action Throttled**
```
"throttled": true
```
**Solution**: Delete and recreate monitor, or wait for throttle period (5 minutes)

---

## Production Recommendations

### Security
- [ ] Use HTTPS for webhook endpoint (add TLS certificates)
- [ ] Implement authentication (API keys, OAuth)
- [ ] Rate limiting to prevent abuse
- [ ] Input validation and sanitization
- [ ] Firewall rules to restrict webhook access

### Reliability
- [ ] Use production WSGI server (Gunicorn, uWSGI) instead of Flask dev server
- [ ] Implement retry logic for failed SMTP deliveries
- [ ] Add dead letter queue for failed webhooks
- [ ] Monitor webhook server health (Prometheus, Nagios)
- [ ] Set up alerting for webhook failures

### Performance
- [ ] Connection pooling for SMTP
- [ ] Async processing for high volume (Celery, RabbitMQ)
- [ ] Cache frequently used data
- [ ] Optimize email template rendering
- [ ] Load balancing for multiple webhook servers

### Maintenance
- [ ] Rotate logs (logrotate)
- [ ] Monitor disk space
- [ ] Automated backups of configuration
- [ ] Version control for all configuration files
- [ ] Document runbook for common tasks

---

## Environment Details

**OpenSearch**: 3.3.2 (localhost:19200)  
**PostgreSQL**: 16 (localhost:15432)  
**Mailhog**: SMTP 100.80.115.61:1025, Web UI :8025  
**Webhook Server**: Flask 3.1.0, Python 3.x  
**Host**: 192.168.1.222 (Linux/zsh)  

---

## Success Metrics

✅ **Monitor Creation**: Successfully created with aggregation query  
✅ **Notification Channel**: Created with host IP webhook URL  
✅ **Webhook Server**: Running and responding to health checks  
✅ **Email Delivery**: Confirmed in Mailhog with proper formatting  
✅ **HTML Rendering**: All 3 hostname sections displayed correctly  
✅ **Log Grouping**: Errors properly grouped by hostname  
✅ **End-to-End Flow**: Complete flow verified from monitor → webhook → SMTP  

---

## Next Steps

1. **Production Hardening**: Implement security recommendations
2. **Monitoring**: Add health checks and alerting for webhook server
3. **Documentation**: Create runbook for operations team
4. **Testing**: Add automated tests for webhook server
5. **Integration**: Connect to production SMTP server (replace Mailhog)
6. **Scaling**: Configure load balancer if needed

---

**Deployment Date**: 2025-11-20  
**Deployed By**: Automation via GitHub Copilot  
**Status**: ✅ Fully Operational
