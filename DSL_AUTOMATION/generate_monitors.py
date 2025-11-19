#!/usr/bin/env python3
"""
OpenSearch Monitor Generator
Generates OpenSearch monitor JSON files from YAML configuration
"""

import json
import yaml
import sys
from pathlib import Path
from typing import Dict, List, Any


class MonitorGenerator:
    """Generates OpenSearch monitor JSON from YAML configuration"""
    
    # HTML template for grouped-by-host email
    HTML_GROUPED_TEMPLATE = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f2f2f2;text-align:left}.hostname{font-weight:bold;color:#0066cc}td.log{font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px}time{color:#555;font-size:11px;font-weight:normal}tbody tr:nth-child(odd){background:#ffffff}tbody tr:nth-child(even){background:#f9f9f9}</style>
</head><body><h2 style="color:#d9534f;margin:0 0 10px 0">🚨 Postgres Critical Alert</h2><p><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Total hits:</strong> {{ctx.results.0.hits.total.value}}<br/><strong>Time:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}</p><table><thead><tr><th>Hostname</th><th>Timestamp</th><th>Log Entry</th></tr></thead><tbody>{{#ctx.results.0.hits.hits}}<tr><td class="hostname">{{_source.host.name}}</td><td><time>{{_source.@timestamp}}</time></td><td class="log">{{{_source._raw}}}</td></tr>{{/ctx.results.0.hits.hits}}</tbody></table></body></html>"""
    
    # HTML template for simple list
    HTML_SIMPLE_TEMPLATE = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f2f2f2;text-align:left}td.log{font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word}</style>
</head><body><p><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Total hits:</strong> {{ctx.results[0].hits.total.value}}</p><table><thead><tr><th>Timestamp</th><th>Hostname</th><th>Log</th></tr></thead><tbody>{{#ctx.results.0.hits.hits}}<tr><td>{{_source.@timestamp}}</td><td>{{_source.host.name}}</td><td class="log">{{{_source._raw}}}</td></tr>{{/ctx.results.0.hits.hits}}</tbody></table></body></html>"""
    
    # Plain text template
    PLAIN_TEXT_TEMPLATE = """Monitor: {{ctx.monitor.name}}
Trigger: {{ctx.trigger.name}}
Total hits: {{ctx.results[0].hits.total.value}}

Log Entries:
{{#ctx.results.0.hits.hits}}
- [{{_source.@timestamp}}] {{_source.host.name}}: {{_source._raw}}
{{/ctx.results.0.hits.hits}}"""

    def __init__(self, config_path: str):
        """Initialize generator with YAML config path"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'monitors' not in config:
            raise ValueError("Config must contain 'monitors' key")
        
        return config
    
    def _build_query_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Build a single query condition"""
        cond_type = condition.get('type')
        
        if cond_type == 'terms':
            return {
                "terms": {
                    condition['field']: condition['values']
                }
            }
        elif cond_type == 'match_phrase':
            return {
                "match_phrase": {
                    condition['field']: condition['value']
                }
            }
        elif cond_type == 'match':
            return {
                "match": {
                    condition['field']: condition['value']
                }
            }
        elif cond_type == 'range':
            return {
                "range": {
                    condition['field']: condition['range']
                }
            }
        else:
            raise ValueError(f"Unknown condition type: {cond_type}")
    
    def _build_query(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build the OpenSearch query from inputs config"""
        query_type = inputs.get('query_type', 'bool_should')
        conditions = inputs.get('conditions', [])
        size = inputs.get('query_size', 100)
        time_range = inputs.get('time_range')
        sort_config = inputs.get('sort')
        
        # Build condition clauses
        condition_clauses = [self._build_query_condition(c) for c in conditions]
        
        # Add time range filter if specified
        if time_range:
            time_filter = {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{time_range['value']}{time_range['unit'][0].lower()}",
                        "lte": "now"
                    }
                }
            }
        
        # Build bool query
        if query_type == 'bool_should':
            bool_query = {
                "bool": {
                    "should": condition_clauses,
                    "minimum_should_match": inputs.get('minimum_should_match', 1)
                }
            }
            # Add time range as must clause if specified
            if time_range:
                bool_query["bool"]["filter"] = [time_filter]
        elif query_type == 'bool_must':
            bool_query = {
                "bool": {
                    "must": condition_clauses
                }
            }
            # Add time range as filter if specified
            if time_range:
                bool_query["bool"]["filter"] = [time_filter]
        else:
            # Single condition query
            if time_range:
                bool_query = {
                    "bool": {
                        "must": [condition_clauses[0] if condition_clauses else {"match_all": {}}],
                        "filter": [time_filter]
                    }
                }
            else:
                bool_query = condition_clauses[0] if condition_clauses else {"match_all": {}}
        
        query_result = {
            "query": bool_query,
            "size": size
        }
        
        # Add sort if specified
        if sort_config:
            query_result["sort"] = [
                {
                    sort_config['field']: {
                        "order": sort_config.get('order', 'desc')
                    }
                }
            ]
        
        return query_result
    
    def _get_message_template(self, template_type: str) -> str:
        """Get message template based on type"""
        templates = {
            'html_grouped_by_host': self.HTML_GROUPED_TEMPLATE,
            'html_simple': self.HTML_SIMPLE_TEMPLATE,
            'plain_text': self.PLAIN_TEXT_TEMPLATE
        }
        return templates.get(template_type, self.HTML_SIMPLE_TEMPLATE)
    
    def _build_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Build trigger action"""
        action_config = {
            "name": action['name'],
            "destination_id": action['destination_id'],
            "subject_template": {
                "source": action['subject_template']
            },
            "message_template": {
                "source": self._get_message_template(action.get('message_template_type', 'html_simple')),
                "lang": "mustache"
            }
        }
        
        # Add throttling if enabled
        throttle = action.get('throttle', {})
        if throttle.get('enabled', False):
            action_config['throttle_enabled'] = True
            action_config['throttle'] = {
                "value": throttle['value'],
                "unit": throttle['unit']
            }
        
        return action_config
    
    def _build_trigger(self, trigger: Dict[str, Any]) -> Dict[str, Any]:
        """Build monitor trigger"""
        return {
            "name": trigger['name'],
            "severity": str(trigger.get('severity', 1)),
            "condition": {
                "script": {
                    "source": trigger['condition']['script'],
                    "lang": trigger['condition'].get('lang', 'painless')
                }
            },
            "actions": [self._build_action(action) for action in trigger.get('actions', [])]
        }
    
    def generate_monitor(self, monitor_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenSearch monitor JSON from config"""
        monitor = {
            "type": "monitor",
            "name": monitor_config['name'],
            "enabled": monitor_config.get('enabled', True),
            "schedule": {
                "period": {
                    "interval": monitor_config['schedule']['interval'],
                    "unit": monitor_config['schedule']['unit']
                }
            },
            "inputs": [
                {
                    "search": {
                        "indices": monitor_config['inputs']['indices'],
                        "query": self._build_query(monitor_config['inputs'])
                    }
                }
            ],
            "triggers": [self._build_trigger(t) for t in monitor_config.get('triggers', [])]
        }
        
        return monitor
    
    def generate_all(self, output_dir: str = None) -> List[Path]:
        """Generate all monitors from config and save to files"""
        if output_dir is None:
            output_dir = self.config_path.parent / 'generated_monitors'
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []
        
        for monitor_config in self.config['monitors']:
            monitor_json = self.generate_monitor(monitor_config)
            
            # Create safe filename from monitor name
            safe_name = monitor_config['name'].lower()
            safe_name = safe_name.replace(' - ', '_').replace(' ', '_').replace('(', '').replace(')', '')
            filename = f"{safe_name}.json"
            
            output_path = output_dir / filename
            
            with open(output_path, 'w') as f:
                json.dump(monitor_json, f, indent=2)
            
            generated_files.append(output_path)
            print(f"✓ Generated: {output_path}")
        
        return generated_files


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python generate_monitors.py <config.yml> [output_dir]")
        print("\nExample:")
        print("  python generate_monitors.py opensearch_dsl.yml")
        print("  python generate_monitors.py opensearch_dsl.yml ./output")
        sys.exit(1)
    
    config_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        generator = MonitorGenerator(config_path)
        generated_files = generator.generate_all(output_dir)
        
        print(f"\n✓ Successfully generated {len(generated_files)} monitor(s)")
        print(f"\nTo upload monitors to OpenSearch:")
        for file in generated_files:
            print(f"  curl -X POST 'http://localhost:19200/_plugins/_alerting/monitors' \\")
            print(f"    -H 'Content-Type: application/json' \\")
            print(f"    -d @{file}")
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
