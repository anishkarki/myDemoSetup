#!/usr/bin/env python3
"""
Dynamic DSL Generator for OpenSearch Webhook Monitors
Generates monitors with notification channel integration for custom webhook delivery
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
import sys


class WebhookMonitorGenerator:
    """Generate OpenSearch monitors with webhook notification channels"""
    
    def __init__(self, config_file: str):
        """Initialize with YAML configuration file"""
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = Path(self.config.get('output_directory', './generated_webhook_monitors'))
        self.output_dir.mkdir(exist_ok=True)
    
    def _build_error_patterns(self, monitor_config: Dict) -> List[Dict]:
        """Build error pattern matching conditions"""
        patterns = []
        
        # Handle different pattern types
        error_codes = monitor_config.get('error_codes', {})
        
        # SQLSTATE codes
        if 'sqlstate_codes' in error_codes:
            for code in error_codes['sqlstate_codes']:
                patterns.append({
                    "match_phrase": {
                        monitor_config['match_field']: f"e={code},"
                    }
                })
        
        # Keyword patterns
        if 'keywords' in error_codes:
            for keyword in error_codes['keywords']:
                patterns.append({
                    "match_phrase": {
                        monitor_config['match_field']: keyword
                    }
                })
        
        # Custom regex patterns
        if 'regex_patterns' in error_codes:
            for pattern in error_codes['regex_patterns']:
                patterns.append({
                    "regexp": {
                        monitor_config['match_field']: pattern
                    }
                })
        
        # Wildcard patterns
        if 'wildcard_patterns' in error_codes:
            for pattern in error_codes['wildcard_patterns']:
                patterns.append({
                    "wildcard": {
                        monitor_config['match_field']: pattern
                    }
                })
        
        return patterns
    
    def _build_aggregation_query(self, monitor_config: Dict) -> Dict:
        """Build aggregation query based on configuration"""
        group_by_field = monitor_config['grouping']['field']
        group_size = monitor_config['grouping'].get('size', 100)
        top_hits_size = monitor_config['grouping'].get('top_hits_size', 100)
        sort_field = monitor_config['grouping'].get('sort_field', '@timestamp')
        sort_order = monitor_config['grouping'].get('sort_order', 'desc')
        
        # Build source includes
        source_includes = monitor_config['grouping'].get('source_fields', 
            ['_raw', '@timestamp', group_by_field])
        
        aggregations = {
            "group_by_field": {
                "terms": {
                    "field": group_by_field,
                    "size": group_size
                },
                "aggs": {
                    "top_entries": {
                        "top_hits": {
                            "size": top_hits_size,
                            "sort": [
                                {
                                    sort_field: {
                                        "order": sort_order
                                    }
                                }
                            ],
                            "_source": {
                                "includes": source_includes
                            }
                        }
                    }
                }
            }
        }
        
        # Add additional aggregations if specified
        if 'additional_aggs' in monitor_config['grouping']:
            for agg_name, agg_config in monitor_config['grouping']['additional_aggs'].items():
                aggregations['group_by_field']['aggs'][agg_name] = agg_config
        
        return aggregations
    
    def _build_query(self, monitor_config: Dict) -> Dict:
        """Build the complete OpenSearch query"""
        patterns = self._build_error_patterns(monitor_config)
        
        if not patterns:
            raise ValueError("No error patterns defined in configuration")
        
        # Time range filter
        time_window = monitor_config.get('time_window', '5m')
        
        query = {
            "query": {
                "bool": {
                    "should": patterns,
                    "minimum_should_match": 1,
                    "filter": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{time_window}",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "size": 0,
            "aggs": self._build_aggregation_query(monitor_config)
        }
        
        # Add additional filters if specified
        if 'additional_filters' in monitor_config:
            query['query']['bool']['filter'].extend(monitor_config['additional_filters'])
        
        return query
    
    def _build_html_template(self, monitor_config: Dict) -> str:
        """Build HTML email template"""
        template_config = monitor_config.get('email_template', {})
        
        # Get styling configuration
        styles = template_config.get('styles', {})
        primary_color = styles.get('primary_color', '#d9534f')
        header_bg = styles.get('header_bg', primary_color)
        border_color = styles.get('border_color', primary_color)
        
        # Get field mappings for template
        group_field = monitor_config['grouping']['field']
        raw_field = monitor_config.get('match_field', '_raw')
        timestamp_field = monitor_config['grouping'].get('sort_field', '@timestamp')
        
        # Get template strings
        alert_title = template_config.get('alert_title', '🚨 Critical Alert')
        section_icon = template_config.get('section_icon', '🔴')
        section_title = template_config.get('section_title', 'Group')
        
        # Build CSS
        css = f"""body{{font-family:Arial,Helvetica,sans-serif;color:#222;padding:10px}}
.group-section{{margin-bottom:25px;border:2px solid {border_color};border-radius:5px;overflow:hidden}}
.group-header{{font-weight:bold;color:#fff;background:{header_bg};padding:12px 15px;font-size:16px}}
.log-container{{background:#fff}}
.log-entry{{padding:10px 15px;border-bottom:1px solid #ffe6e6;font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.5}}
.log-entry:nth-child(odd){{background:#fff}}
.log-entry:nth-child(even){{background:#fff9f9}}
.log-entry:last-child{{border-bottom:none}}
time{{color:#666;font-size:11px;display:block;margin-bottom:4px}}"""
        
        # Build HTML template with Mustache syntax
        html = f"""<html><head><meta charset="utf-8">
<style>{css}</style>
</head><body><h2 style="color:{primary_color};margin:0 0 15px 0">{alert_title}</h2>"""
        
        # Add monitor metadata
        html += """<p style="margin-bottom:20px"><strong>Monitor:</strong> {{ctx.monitor.name}}<br/>"""
        html += """<strong>Trigger:</strong> {{ctx.trigger.name}}<br/>"""
        html += """<strong>Time Window:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}<br/>"""
        html += """<strong>Alert Condition:</strong> """ + template_config.get('alert_condition', 'Errors detected') + "</p>"
        
        # Add grouped sections
        html += """{{#ctx.results.0.aggregations.group_by_field.buckets}}"""
        html += f"""<div class="group-section"><div class="group-header">{section_icon} {section_title}: {{{{key}}}} — {{{{doc_count}}}} error(s)</div>"""
        html += """<div class="log-container">{{#top_entries.hits.hits}}"""
        html += f"""<div class="log-entry"><time>{{{{_source.{timestamp_field}}}}}</time>{{{{{{_source.{raw_field}}}}}}}}}</div>"""
        html += """{{/top_entries.hits.hits}}</div></div>"""
        html += """{{/ctx.results.0.aggregations.group_by_field.buckets}}"""
        html += """</body></html>"""
        
        return html
    
    def _build_webhook_payload(self, monitor_config: Dict) -> str:
        """Build webhook JSON payload template"""
        email_config = monitor_config.get('email_config', {})
        recipients = email_config.get('recipients', ['alert@example.com'])
        subject_template = email_config.get('subject', 'Alert: {{ctx.results.0.aggregations.group_by_field.buckets.size}} groups affected')
        
        html_template = self._build_html_template(monitor_config)
        
        # Escape for JSON
        html_escaped = html_template.replace('\\', '\\\\').replace('"', '\\"')
        
        payload = {
            "recipients": recipients,
            "subject": subject_template,
            "message": html_escaped
        }
        
        return json.dumps(payload, separators=(',', ':'))
    
    def _build_trigger_condition(self, monitor_config: Dict) -> str:
        """Build Painless trigger condition script"""
        condition_config = monitor_config.get('trigger_condition', {})
        
        if 'custom_script' in condition_config:
            return condition_config['custom_script']
        
        # Default: trigger if any groups found
        min_groups = condition_config.get('min_groups', 1)
        min_errors_per_group = condition_config.get('min_errors_per_group', 1)
        
        script = "if (ctx.results[0].aggregations == null) return false;\n"
        script += "def groups = ctx.results[0].aggregations.group_by_field.buckets;\n"
        
        if min_errors_per_group > 1:
            script += f"def validGroups = groups.findAll {{ it.doc_count >= {min_errors_per_group} }};\n"
            script += f"return validGroups.size() >= {min_groups};"
        else:
            script += f"return groups.size() >= {min_groups};"
        
        return script
    
    def _build_monitor_json(self, monitor_config: Dict, channel_id: str) -> Dict:
        """Build complete monitor JSON"""
        schedule = monitor_config.get('schedule', {})
        throttle = monitor_config.get('throttle', {})
        
        monitor = {
            "type": "monitor",
            "name": monitor_config['name'],
            "enabled": monitor_config.get('enabled', True),
            "schedule": {
                "period": {
                    "interval": schedule.get('interval', 1),
                    "unit": schedule.get('unit', 'MINUTES')
                }
            },
            "inputs": [
                {
                    "search": {
                        "indices": monitor_config['indices'],
                        "query": self._build_query(monitor_config)
                    }
                }
            ],
            "triggers": [
                {
                    "name": monitor_config.get('trigger_name', 'Alert Trigger'),
                    "severity": str(monitor_config.get('severity', 1)),
                    "condition": {
                        "script": {
                            "source": self._build_trigger_condition(monitor_config),
                            "lang": "painless"
                        }
                    },
                    "actions": [
                        {
                            "name": monitor_config.get('action_name', 'Send via Webhook'),
                            "destination_id": channel_id,
                            "subject_template": {
                                "source": monitor_config.get('email_config', {}).get('subject', 'Alert Notification'),
                                "lang": "mustache"
                            },
                            "message_template": {
                                "source": self._build_webhook_payload(monitor_config),
                                "lang": "mustache"
                            },
                            "throttle_enabled": throttle.get('enabled', True),
                            "throttle": {
                                "value": throttle.get('value', 5),
                                "unit": throttle.get('unit', 'MINUTES')
                            }
                        }
                    ]
                }
            ]
        }
        
        return monitor
    
    def generate_monitors(self):
        """Generate all monitors from configuration"""
        monitors_config = self.config.get('monitors', [])
        channel_config = self.config.get('notification_channel', {})
        
        if not channel_config:
            raise ValueError("notification_channel configuration is required")
        
        channel_id = channel_config.get('channel_id')
        if not channel_id:
            print("⚠ No channel_id provided. You'll need to create the channel first.")
            channel_id = "CHANNEL_ID_PLACEHOLDER"
        
        generated_files = []
        
        for monitor_config in monitors_config:
            monitor_name = monitor_config['name']
            safe_name = monitor_name.lower().replace(' ', '_').replace('-', '_')
            
            # Generate monitor JSON
            monitor_json = self._build_monitor_json(monitor_config, channel_id)
            
            # Save to file
            output_file = self.output_dir / f"{safe_name}.json"
            with open(output_file, 'w') as f:
                json.dump(monitor_json, f, indent=2)
            
            generated_files.append(output_file)
            print(f"✓ Generated: {output_file}")
        
        # Generate deployment script
        self._generate_deployment_script(generated_files, channel_config)
        
        # Generate README
        self._generate_readme()
        
        return generated_files
    
    def _generate_deployment_script(self, monitor_files: List[Path], channel_config: Dict):
        """Generate shell script to deploy monitors"""
        opensearch_url = self.config.get('opensearch_url', 'http://localhost:19200')
        
        script = f"""#!/bin/bash
# Auto-generated deployment script for webhook monitors

set -e

OPENSEARCH_URL="{opensearch_url}"
CHANNEL_ID="{channel_config.get('channel_id', 'REPLACE_WITH_CHANNEL_ID')}"

echo "🚀 Deploying Webhook Monitors..."
echo ""

# Function to create notification channel if needed
create_channel() {{
    if [ "$CHANNEL_ID" = "REPLACE_WITH_CHANNEL_ID" ]; then
        echo "📡 Creating notification channel..."
        
        RESPONSE=$(curl -s -X POST "${{OPENSEARCH_URL}}/_plugins/_notifications/configs" \\
          -H 'Content-Type: application/json' \\
          -d '{{
            "config": {{
              "name": "{channel_config.get('name', 'Webhook Channel')}",
              "description": "{channel_config.get('description', 'Custom webhook notification')}",
              "config_type": "webhook",
              "is_enabled": true,
              "webhook": {{
                "url": "{channel_config.get('webhook_url', 'http://localhost:5001/webhook/send-email')}",
                "method": "POST",
                "header_params": {{
                  "Content-Type": "application/json"
                }}
              }}
            }}
          }}')
        
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
}}

# Create channel if needed
create_channel

# Deploy monitors
"""
        
        for monitor_file in monitor_files:
            script += f"""
echo "📊 Deploying {monitor_file.name}..."
RESPONSE=$(curl -s -X POST "${{OPENSEARCH_URL}}/_plugins/_alerting/monitors" \\
  -H 'Content-Type: application/json' \\
  -d @{monitor_file.name})

MONITOR_ID=$(echo $RESPONSE | jq -r '._id')
if [ "$MONITOR_ID" != "null" ]; then
    echo "✓ Monitor deployed: $MONITOR_ID"
else
    echo "❌ Failed to deploy {monitor_file.name}"
    echo "$RESPONSE" | jq '.'
fi
echo ""
"""
        
        script += """
echo "✅ Deployment complete!"
"""
        
        script_file = self.output_dir / "deploy_monitors.sh"
        with open(script_file, 'w') as f:
            f.write(script)
        
        script_file.chmod(0o755)
        print(f"✓ Generated deployment script: {script_file}")
    
    def _generate_readme(self):
        """Generate README documentation"""
        readme = f"""# Generated Webhook Monitors

## Overview
This directory contains auto-generated OpenSearch monitors with webhook notification integration.

**Generated on**: {self.config.get('generated_date', 'N/A')}  
**Configuration**: Based on YAML DSL configuration

## Files

### Monitor Definitions
"""
        
        for monitor_config in self.config.get('monitors', []):
            readme += f"- `{monitor_config['name'].lower().replace(' ', '_').replace('-', '_')}.json` - {monitor_config.get('description', monitor_config['name'])}\n"
        
        readme += """
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
"""
        
        readme_file = self.output_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme)
        
        print(f"✓ Generated README: {readme_file}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python generate_webhook_monitors.py <config.yml>")
        print("\nExample:")
        print("  python generate_webhook_monitors.py webhook_monitors_config.yml")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    if not Path(config_file).exists():
        print(f"❌ Configuration file not found: {config_file}")
        sys.exit(1)
    
    try:
        generator = WebhookMonitorGenerator(config_file)
        print(f"\n🔧 Generating monitors from: {config_file}\n")
        
        generated_files = generator.generate_monitors()
        
        print(f"\n✅ Successfully generated {len(generated_files)} monitor(s)")
        print(f"📁 Output directory: {generator.output_dir}")
        print(f"\n🚀 To deploy: cd {generator.output_dir} && ./deploy_monitors.sh")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
