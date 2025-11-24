#!/bin/bash
# Auto-generated deployment script for webhook monitors

set -e

OPENSEARCH_URL="http://localhost:19200"
CHANNEL_ID=""

echo "🚀 Deploying Webhook Monitors..."
echo ""

# Function to create notification channel if needed
create_channel() {
    if [ "$CHANNEL_ID" = "REPLACE_WITH_CHANNEL_ID" ]; then
        echo "📡 Creating notification channel..."
        
        RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_notifications/configs" \
          -H 'Content-Type: application/json' \
          -d '{
            "config": {
              "name": "Patroni SMTP Webhook Channel",
              "description": "Webhook for Patroni cluster alerts via SMTP",
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
          }')
        
        CHANNEL_ID=$(echo $RESPONSE | jq -r '.config_id')
        echo "✓ Channel created: $CHANNEL_ID"
        echo ""
        
        # Update monitor files with actual channel ID
        for file in *.json; do
            if [ -f "$file" ]; then
                sed -i "s/CHANNEL_ID_PLACEHOLDER/$CHANNEL_ID/g" "$file"
            fi
        done
    else
        echo "✓ Using existing channel: $CHANNEL_ID"
        echo ""
    fi
}

# Create channel if needed
create_channel

# Deploy monitors

echo "📊 Deploying patroni_leader_election_events.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_leader_election_events.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_leader_election_events.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "📊 Deploying patroni_replication_lag_issues.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_replication_lag_issues.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_replication_lag_issues.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "📊 Deploying patroni_etcd_connection_issues.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_etcd_connection_issues.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_etcd_connection_issues.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "📊 Deploying patroni_rest_api_health_issues.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_rest_api_health_issues.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_rest_api_health_issues.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "📊 Deploying patroni_cluster_state_changes.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_cluster_state_changes.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_cluster_state_changes.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "📊 Deploying patroni_configuration_errors.json..."
RESPONSE=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H 'Content-Type: application/json' \
  -d @patroni_configuration_errors.json)

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy patroni_configuration_errors.json"
    echo "$RESPONSE" | jq '.'
fi
echo ""

echo "✅ Deployment complete!"
