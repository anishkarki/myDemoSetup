#!/usr/bin/env python3
import yaml
import json
import requests
import argparse
from pathlib import Path
from datetime import datetime

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def build_query(monitor):
    # Time range
    window = monitor.get('window', 'now-1h')
    
    # Base bool query
    must_clauses = [
        { "range": { "@timestamp": { "gte": window, "lte": "now" } } }
    ]
    
    # Severity (OR logic)
    severities = monitor.get('severity', [])
    if severities:
        should_clauses = []
        for sev in severities:
            should_clauses.append({ "match_phrase": { "_raw": sev } })
        
        must_clauses.append({
            "bool": {
                "should": should_clauses,
                "minimum_should_match": 1
            }
        })
        
    # SQL Code Class (Wildcard)
    # Class is 2 chars, code is 5 chars total. e.g. XX000
    # We search for *XX???* to match the code anywhere
    code_class = monitor.get('sql_code_class')
    if code_class:
        # Pattern: *XX???* where ? matches any single char
        # OpenSearch wildcard supports ? for single char
        # We lowercase it because standard analyzers lowercase tokens
        pattern = f"*{code_class.lower()}???*"
        must_clauses.append({ "wildcard": { "_raw": { "value": pattern, "case_insensitive": True } } })

    query = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "size": 10, # Just get a few samples
        "sort": [{ "@timestamp": { "order": "desc" } }]
    }
    return query

def generate_monitor_dsl(config, monitor):
    """Generate the OpenSearch Monitor DSL JSON."""
    
    # 1. Build the query part (same as before but without the 'size' and 'sort' usually)
    # Monitors typically use "inputs" -> "search" -> "query"
    query_body = build_query(monitor)
    
    # Remove size/sort if they are not needed for the count check, 
    # but usually keeping them is fine or setting size: 0 if we only care about count.
    # However, for the email template to show logs, we need hits.
    
    # 2. Construct the full Monitor object
    monitor_dsl = {
        "type": "monitor",
        "name": monitor['name'],
        "monitor_type": "query_level_monitor",
        "enabled": monitor.get('enabled', True),
        "schedule": {
            "period": {
                "interval": monitor.get('schedule', {}).get('period', {}).get('interval', 1),
                "unit": monitor.get('schedule', {}).get('period', {}).get('unit', 'MINUTES')
            }
        },
        "inputs": [
            {
                "search": {
                    "indices": [config['opensearch']['index']],
                    "query": query_body
                }
            }
        ],
        "triggers": []
    }
    
    # 3. Add Trigger
    trigger_conf = monitor.get('trigger')
    if trigger_conf:
        trigger_dsl = {
            "name": trigger_conf.get('name', 'Default Trigger'),
            "severity": trigger_conf.get('level', '1'),
            "condition": {
                "script": {
                    "lang": "painless",
                    "source": trigger_conf.get('condition', "ctx.results[0].hits.total.value > 0")
                }
            },
            "actions": []
        }
        
        # 4. Add Action (Email)
        email_conf = monitor.get('email_template')
        dest_id = config['opensearch'].get('destination_id')
        
        if email_conf and dest_id:
            action_dsl = {
                "name": "Send Email Action",
                "destination_id": dest_id,
                "message_template": {
                    "source": email_conf.get('body', 'Alert triggered.'),
                    "lang": "mustache"
                },
                "subject_template": {
                    "source": email_conf.get('subject', 'Alert'),
                    "lang": "mustache"
                }
            }
            trigger_dsl['actions'].append(action_dsl)
            
        monitor_dsl['triggers'].append(trigger_dsl)
        
    return monitor_dsl

def run_monitor(config, monitor):
    host = config['opensearch']['host']
    port = config['opensearch']['port']
    index = config['opensearch']['index']
    
    url = f"http://{host}:{port}/{index}/_search"
    query = build_query(monitor)
    
    print(f"Running Monitor: {monitor['name']}...")
    try:
        resp = requests.post(url, json=query, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get('hits', {}).get('hits', [])
        total = resp.json().get('hits', {}).get('total', {}).get('value', 0)
        
        print(f"  -> Status: {'ALERT' if total > 0 else 'OK'}")
        print(f"  -> Hits Found: {total}")
        
        if total > 0:
            print("  -> Sample Logs:")
            for hit in hits[:3]:
                raw = hit['_source'].get('_raw', '')
                ts = hit['_source'].get('@timestamp', 'N/A')
                print(f"     [{ts}] {raw[:100]}...")
        print("-" * 40)
        
    except Exception as e:
        print(f"  -> Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run monitors defined in YAML.")
    parser.add_argument("-c", "--config", default="monitor_config.yml", help="Path to config file")
    parser.add_argument("--generate-dsl", action="store_true", help="Generate DSL JSON files for creating monitors")
    parser.add_argument("--create", action="store_true", help="Create the monitors in OpenSearch")
    args = parser.parse_args()
    
    config_path = Path(args.config)
    if not config_path.exists():
        # Try looking in the same directory as the script
        script_dir = Path(__file__).parent
        config_path = script_dir / args.config
        
    if not config_path.exists():
        print(f"Config file not found: {args.config}")
        return

    config = load_config(config_path)
    
    print(f"Loaded {len(config['monitors'])} monitors from {config_path}")
    print("-" * 40)
    
    if args.generate_dsl or args.create:
        output_dir = config_path.parent / "generated_monitors"
        output_dir.mkdir(exist_ok=True)
        
        for monitor in config['monitors']:
            if not monitor.get('enabled', True):
                continue
                
            dsl = generate_monitor_dsl(config, monitor)
            safe_name = monitor['name'].replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            filename = output_dir / f"monitor_{safe_name}.json"
            
            with open(filename, 'w') as f:
                json.dump(dsl, f, indent=2)
                
            print(f"Generated DSL: {filename}")
            
            if args.create:
                host = config['opensearch']['host']
                port = config['opensearch']['port']
                url = f"http://{host}:{port}/_plugins/_alerting/monitors"
                
                try:
                    print(f"Creating Monitor '{monitor['name']}'...")
                    resp = requests.post(url, json=dsl, timeout=10)
                    if resp.status_code in [200, 201]:
                        print(f"  -> Success! ID: {resp.json().get('_id')}")
                    else:
                        print(f"  -> Failed: {resp.status_code} {resp.text}")
                except Exception as e:
                    print(f"  -> Error: {e}")
            else:
                print("To create this monitor in Dev Tools, run:")
                print(f"POST _plugins/_alerting/monitors\n{json.dumps(dsl, indent=2)}")
            print("-" * 40)
    else:
        for monitor in config['monitors']:
            if monitor.get('enabled', True):
                run_monitor(config, monitor)

if __name__ == "__main__":
    main()
