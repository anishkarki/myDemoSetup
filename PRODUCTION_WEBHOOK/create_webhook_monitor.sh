#!/bin/bash
# Create Postgres Critical Monitor with Custom Webhook

HTML_TEMPLATE='<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222;padding:10px}.hostname-section{margin-bottom:25px;border:2px solid #d9534f;border-radius:5px;overflow:hidden}.hostname-header{font-weight:bold;color:#fff;background:#d9534f;padding:12px 15px;font-size:16px}.log-container{background:#fff}.log-entry{padding:10px 15px;border-bottom:1px solid #ffe6e6;font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.5}.log-entry:nth-child(odd){background:#fff}.log-entry:nth-child(even){background:#fff9f9}.log-entry:last-child{border-bottom:none}time{color:#666;font-size:11px;display:block;margin-bottom:4px}</style>
</head><body><h2 style="color:#d9534f;margin:0 0 15px 0">🚨 Postgres Critical Alert</h2><p style="margin-bottom:20px"><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Time Window:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}<br/><strong>Alert Condition:</strong> Critical errors detected</p>{{#ctx.results.0.aggregations.group_by_hostname.buckets}}<div class="hostname-section"><div class="hostname-header">🔴 Hostname: {{key}} — {{doc_count}} critical error(s)</div><div class="log-container">{{#top_errors.hits.hits}}<div class="log-entry"><time>{{_source.@timestamp}}</time>{{{_source._raw}}}</div>{{/top_errors.hits.hits}}</div></div>{{/ctx.results.0.aggregations.group_by_hostname.buckets}}</body></html>'

cat > /tmp/webhook_monitor_payload.json << EOF
{
  "recipients": ["dev1@test.local", "dev2@test.local"],
  "subject": "🚨 Postgres CRITICAL: Errors Detected - {{ctx.results.0.aggregations.group_by_hostname.buckets.size}} hosts affected",
  "message": "${HTML_TEMPLATE}"
}
EOF

# Create monitor with custom webhook action
curl -s -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \
  -H 'Content-Type: application/json' \
  -d @- << 'MONITOR_EOF' | jq '{id: ._id, name: .monitor.name}'
{
  "type": "monitor",
  "name": "Postgres Critical Errors - Webhook (Production)",
  "enabled": true,
  "schedule": {
    "period": {
      "interval": 1,
      "unit": "MINUTES"
    }
  },
  "inputs": [
    {
      "search": {
        "indices": ["postgresdata", "postgresd*"],
        "query": {
          "query": {
            "bool": {
              "should": [
                {"match_phrase": {"_raw": "e=08000,"}},
                {"match_phrase": {"_raw": "e=08006,"}},
                {"match_phrase": {"_raw": "e=08001,"}},
                {"match_phrase": {"_raw": "e=08004,"}},
                {"match_phrase": {"_raw": "e=22012,"}},
                {"match_phrase": {"_raw": "e=22003,"}},
                {"match_phrase": {"_raw": "e=22P01,"}},
                {"match_phrase": {"_raw": "e=23000,"}},
                {"match_phrase": {"_raw": "e=23503,"}},
                {"match_phrase": {"_raw": "e=23505,"}},
                {"match_phrase": {"_raw": "e=28000,"}},
                {"match_phrase": {"_raw": "e=28P01,"}},
                {"match_phrase": {"_raw": "e=40000,"}},
                {"match_phrase": {"_raw": "e=40001,"}},
                {"match_phrase": {"_raw": "e=40P01,"}},
                {"match_phrase": {"_raw": "e=53000,"}},
                {"match_phrase": {"_raw": "e=53100,"}},
                {"match_phrase": {"_raw": "e=53200,"}},
                {"match_phrase": {"_raw": "e=53300,"}},
                {"match_phrase": {"_raw": "e=53400,"}},
                {"match_phrase": {"_raw": "e=54000,"}},
                {"match_phrase": {"_raw": "e=54001,"}},
                {"match_phrase": {"_raw": "e=55000,"}},
                {"match_phrase": {"_raw": "e=55P03,"}},
                {"match_phrase": {"_raw": "e=57000,"}},
                {"match_phrase": {"_raw": "e=57014,"}},
                {"match_phrase": {"_raw": "e=57P01,"}},
                {"match_phrase": {"_raw": "e=57P02,"}},
                {"match_phrase": {"_raw": "e=57P04,"}},
                {"match_phrase": {"_raw": "e=58000,"}},
                {"match_phrase": {"_raw": "e=58030,"}},
                {"match_phrase": {"_raw": "e=F0000,"}},
                {"match_phrase": {"_raw": "e=F0001,"}},
                {"match_phrase": {"_raw": "e=XX000,"}},
                {"match_phrase": {"_raw": "e=XX001,"}},
                {"match_phrase": {"_raw": "e=XX002,"}},
                {"match_phrase": {"_raw": "PANIC:"}},
                {"match_phrase": {"_raw": "FATAL:"}}
              ],
              "minimum_should_match": 1,
              "filter": [
                {
                  "range": {
                    "@timestamp": {
                      "gte": "now-2m",
                      "lte": "now"
                    }
                  }
                }
              ]
            }
          },
          "size": 0,
          "aggs": {
            "group_by_hostname": {
              "terms": {
                "field": "host.name",
                "size": 100
              },
              "aggs": {
                "top_errors": {
                  "top_hits": {
                    "size": 100,
                    "sort": [
                      {
                        "@timestamp": {
                          "order": "desc"
                        }
                      }
                    ],
                    "_source": {
                      "includes": [
                        "_raw",
                        "@timestamp",
                        "host.name"
                      ]
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  ],
  "triggers": [
    {
      "name": "Critical Error Detected",
      "severity": "1",
      "condition": {
        "script": {
          "source": "if (ctx.results[0].aggregations == null) return false;\ndef hostBuckets = ctx.results[0].aggregations.group_by_hostname.buckets;\nreturn hostBuckets.size() > 0;",
          "lang": "painless"
        }
      },
      "actions": [
        {
          "name": "Send Email via Webhook",
          "custom_webhook": {
            "url": "http://localhost:5001/webhook/send-email",
            "method": "POST",
            "header_params": {
              "Content-Type": "application/json"
            },
            "body": "{\"recipients\": [\"dev1@test.local\", \"dev2@test.local\"], \"subject\": \"🚨 Postgres CRITICAL: Errors Detected - {{ctx.results.0.aggregations.group_by_hostname.buckets.size}} hosts affected\", \"message\": \"<html><head><meta charset=\\\"utf-8\\\">\\n<style>body{font-family:Arial,Helvetica,sans-serif;color:#222;padding:10px}.hostname-section{margin-bottom:25px;border:2px solid #d9534f;border-radius:5px;overflow:hidden}.hostname-header{font-weight:bold;color:#fff;background:#d9534f;padding:12px 15px;font-size:16px}.log-container{background:#fff}.log-entry{padding:10px 15px;border-bottom:1px solid #ffe6e6;font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.5}.log-entry:nth-child(odd){background:#fff}.log-entry:nth-child(even){background:#fff9f9}.log-entry:last-child{border-bottom:none}time{color:#666;font-size:11px;display:block;margin-bottom:4px}</style>\\n</head><body><h2 style=\\\"color:#d9534f;margin:0 0 15px 0\\\">🚨 Postgres Critical Alert</h2><p style=\\\"margin-bottom:20px\\\"><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Time Window:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}<br/><strong>Alert Condition:</strong> Critical errors detected</p>{{#ctx.results.0.aggregations.group_by_hostname.buckets}}<div class=\\\"hostname-section\\\"><div class=\\\"hostname-header\\\">🔴 Hostname: {{key}} — {{doc_count}} critical error(s)</div><div class=\\\"log-container\\\">{{#top_errors.hits.hits}}<div class=\\\"log-entry\\\"><time>{{_source.@timestamp}}</time>{{{_source._raw}}}</div>{{/top_errors.hits.hits}}</div></div>{{/ctx.results.0.aggregations.group_by_hostname.buckets}}</body></html>\"}"
          },
          "throttle_enabled": true,
          "throttle": {
            "value": 5,
            "unit": "MINUTES"
          }
        }
      ]
    }
  ]
}
MONITOR_EOF
