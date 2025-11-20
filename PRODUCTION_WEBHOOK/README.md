# Production Webhook Setup for OpenSearch Alerting

## Overview
This setup uses a custom SMTP webhook server to send emails from OpenSearch monitors instead of using the built-in email destination.

## Components

### 1. SMTP Webhook Server (`smtp_webhook_server.py`)
Flask-based webhook server that:
- Receives POST requests from OpenSearch
- Parses JSON payload (recipients, subject, message)
- Sends emails via SMTP (Mailhog)
- Returns success/error status

### 2. Monitor Configuration
Same critical error monitor with webhook destination instead of email destination.

## Setup Instructions

### Step 1: Install Dependencies
```bash
pip install flask
```

### Step 2: Start SMTP Webhook Server
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/PRODUCTION_WEBHOOK
python3 smtp_webhook_server.py
```
Server will listen on: `http://localhost:5001`

### Step 3: Create Custom Webhook in OpenSearch
```bash
curl -X POST 'http://localhost:19200/_plugins/_alerting/destinations' \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "custom_webhook",
    "name": "SMTP Webhook - Production",
    "custom_webhook": {
      "url": "http://localhost:5001/webhook/send-email",
      "method": "POST",
      "header_params": {
        "Content-Type": "application/json"
      }
    }
  }'
```

### Step 4: Update Monitor with Webhook Action

The monitor will send a JSON payload:
```json
{
  "recipients": ["dev1@test.local", "dev2@test.local"],
  "subject": "🚨 Postgres CRITICAL: Errors Detected",
  "message": "<html>... email template ...</html>"
}
```

## Testing

### Test webhook server:
```bash
curl -X POST 'http://localhost:5001/webhook/send-email' \
  -H 'Content-Type: application/json' \
  -d '{
    "recipients": ["test@example.com"],
    "subject": "Test Email",
    "message": "<html><body><h1>Test</h1></body></html>"
  }'
```

### Check Mailhog:
- Web UI: http://100.80.115.61:8025
- API: http://100.80.115.61:8025/api/v2/messages

## SMTP Configuration
- Host: 100.80.115.61
- Port: 1025 (Mailhog)
- From: alerts@postgres-monitoring.local

## Advantages of Webhook Approach
1. Full control over email formatting
2. Can add custom logic (filtering, throttling, routing)
3. Easy to add attachments or multiple SMTP servers
4. Better logging and error handling
5. Can integrate with other notification systems
