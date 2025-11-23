# Generated Webhook Monitors

## Overview
This directory contains auto-generated OpenSearch monitors with webhook notification integration.

**Generated on**: N/A  
**Configuration**: Based on YAML DSL configuration

## Files

### Monitor Definitions
- `my_quick_test_monitor.json` - Testing the DSL generator

### Deployment Scripts
- `deploy_monitors.sh` - Automated deployment script

## Deployment

### Prerequisites
- OpenSearch cluster running and accessible
- Webhook server running (if using custom webhook)
- `curl` and `jq` installed

### Steps

1. **Review Configuration**
   ```bash
   # Check all generated monitors
   ls -l *.json
   ```

2. **Create Notification Channel** (if not exists)
   ```bash
   # The deploy script will handle this automatically
   # Or create manually via OpenSearch API
   ```

3. **Deploy Monitors**
   ```bash
   ./deploy_monitors.sh
   ```

4. **Verify Deployment**
   ```bash
   # List all monitors
   curl -X GET 'http://localhost:19200/_plugins/_alerting/monitors/_search?pretty'
   
   # Execute a specific monitor for testing
   curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors/MONITOR_ID/_execute'
   ```

## Configuration Structure

Each monitor includes:
- **Query**: Pattern matching with aggregation
- **Grouping**: Groups errors by specified field
- **Trigger**: Condition for alert activation
- **Action**: Webhook notification with email template
- **Throttle**: Rate limiting for alerts

## Customization

To modify monitors:
1. Edit the YAML configuration file
2. Re-run the generator
3. Redeploy using `deploy_monitors.sh`

## Troubleshooting

### Monitor Not Triggering
```bash
# Check if data matches patterns
curl -X GET 'http://localhost:19200/INDEX_NAME/_search?pretty' -d '{
  "query": { ... pattern from monitor ... }
}'
```

### Webhook Not Receiving
```bash
# Check webhook server logs
# Verify channel configuration
curl -X GET 'http://localhost:19200/_plugins/_notifications/configs'
```

### Action Throttled
```bash
# Check throttle settings in monitor configuration
# Wait for throttle period to expire
# Or delete and recreate monitor to reset throttle
```

## Support

For issues or questions, review the main configuration file and regenerate monitors as needed.
