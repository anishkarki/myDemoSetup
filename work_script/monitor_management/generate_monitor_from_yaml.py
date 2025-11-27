import yaml
import json
import os
import socket
import requests
import sys
import argparse

# Configuration
OPENSEARCH_URL = "http://localhost:19200"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DSL_REPORT_DIR = os.path.join(BASE_DIR, "dsl_report")
CONFIG_FILE = os.path.join(BASE_DIR, "monitor_config.yaml")

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        s.close()
        return IP
    except Exception:
        return '127.0.0.1'

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

def load_config(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
        # Simple template substitution for HOST_IP
        host_ip = get_host_ip()
        content = content.replace("{{HOST_IP}}", host_ip)
        return yaml.safe_load(content)

def create_webhook_channel(name, url):
    api_url = f"{OPENSEARCH_URL}/_plugins/_notifications/configs"
    
    payload = {
        "config": {
            "name": name,
            "description": "Auto-generated webhook channel",
            "config_type": "webhook",
            "is_enabled": True,
            "webhook": {
                "url": url,
                "header_params": {"Content-Type": "application/json"},
                "method": "POST"
            }
        }
    }
    
    try:
        response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        res_json = response.json()
        print(f"Created Webhook Channel '{name}': {res_json['config_id']}")
        return res_json['config_id']
    except requests.exceptions.RequestException as e:
        print(f"Error creating channel '{name}': {e}")
        if e.response is not None:
            print(e.response.text)
        return None

def generate_monitor_dsl(config, channel_id):
    monitor_cfg = config['monitor']
    
    # Build Query
    filter_clauses = []
    must_clauses = []
    must_not_clauses = []
    should_clauses = []
    
    # Time Range
    # Assuming time_range format like "1h", "10m"
    time_range = monitor_cfg['inputs'].get('time_range', '1h')
    filter_clauses.append({
        "range": {
            "@timestamp": {
                "gte": f"now-{time_range}",
                "lte": "now"
            }
        }
    })

    # Host Pattern (Wildcard)
    if 'host_pattern' in monitor_cfg['inputs']:
        filter_clauses.append({
            "wildcard": {
                "host.name.keyword": {
                    "value": monitor_cfg['inputs']['host_pattern'],
                    "case_insensitive": True
                }
            }
        })
    
    # Filters
    for f in monitor_cfg['inputs'].get('filters', []):
        must_clauses.append({
            "match_phrase": {
                f['field']: f['match']
            }
        })

    # Match Any (Should)
    for f in monitor_cfg['inputs'].get('match_any', []):
        should_clauses.append({
            "match_phrase": {
                f['field']: f['match']
            }
        })

    # Exclude Filters
    for f in monitor_cfg['inputs'].get('exclude_filters', []):
        must_not_clauses.append({
            "match_phrase": {
                f['field']: f['match']
            }
        })

    # Build Triggers
    triggers = []
    for t in monitor_cfg['triggers']:
        actions = []
        for a in t['actions']:
            # We only support webhook actions for this specific generator logic for now
            # or we use the passed channel_id if it matches the intent
            
            # Construct the message body. 
            # If the YAML has a JSON-like string, we use it.
            # The Mustache template needs to be a string in the DSL.
            
            actions.append({
                "name": a['name'],
                "destination_id": channel_id,
                "message_template": {
                    "source": a['message_body'],
                    "lang": "mustache"
                },
                "throttle_enabled": False,
                "subject_template": {
                    "source": a['subject'],
                    "lang": "mustache"
                }
            })

        triggers.append({
            "name": t['name'],
            "severity": t['severity'],
            "condition": {
                "script": {
                    "source": t['condition_script'],
                    "lang": "painless"
                }
            },
            "actions": actions
        })

    monitor_dsl = {
        "type": "monitor",
        "name": monitor_cfg['name'],
        "monitor_type": "query_level_monitor",
        "enabled": monitor_cfg['enabled'],
        "schedule": {
            "period": {
                "interval": monitor_cfg['schedule']['interval'],
                "unit": monitor_cfg['schedule']['unit']
            }
        },
        "inputs": [
            {
                "search": {
                    "indices": monitor_cfg['inputs']['indices'],
                    "query": {
                        "size": 0,
                        "query": {
                            "bool": {
                                "filter": filter_clauses,
                                "must": must_clauses,
                                "must_not": must_not_clauses,
                                "should": should_clauses,
                                "minimum_should_match": 1 if should_clauses else 0
                            }
                        }
                    }
                }
            }
        ],
        "triggers": triggers
    }
    
    return monitor_dsl

def save_monitor_dsl(monitor_dsl, filename):
    filepath = os.path.join(DSL_REPORT_DIR, filename)
    with open(filepath, 'w') as f:
        json.dump(monitor_dsl, f, indent=4)
    print(f"Saved Monitor DSL to: {filepath}")
    return filepath

def post_monitor(monitor_dsl):
    url = f"{OPENSEARCH_URL}/_plugins/_alerting/monitors"
    try:
        response = requests.post(url, json=monitor_dsl, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        res_json = response.json()
        print(f"Successfully posted monitor '{monitor_dsl['name']}': {res_json['_id']}")
        return res_json['_id']
    except requests.exceptions.RequestException as e:
        print(f"Error posting monitor: {e}")
        if e.response is not None:
            print(e.response.text)
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate OpenSearch Monitor from YAML")
    parser.add_argument("-out", choices=['dsl', 'post'], required=True, help="Output mode: 'dsl' for JSON only, 'post' to deploy")
    args = parser.parse_args()

    print(f"Starting YAML Monitor Generator (Mode: {args.out})...")
    ensure_dir(DSL_REPORT_DIR)
    
    # 1. Load Config
    try:
        config = load_config(CONFIG_FILE)
        print(f"Loaded configuration for: {config['monitor']['name']}")
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    # 2. Setup Channel
    channel_id = "PLACEHOLDER_CHANNEL_ID"
    if args.out == 'post':
        # In a real app, we might check if channel exists or support multiple channels.
        # Here we look at the first action of the first trigger to get the URL.
        # Simplified logic for this task.
        try:
            webhook_url = config['monitor']['triggers'][0]['actions'][0]['webhook_url']
            channel_name = f"Channel for {config['monitor']['name']}"
            channel_id = create_webhook_channel(channel_name, webhook_url)
            
            if not channel_id:
                print("Failed to create notification channel.")
                return
                
        except (KeyError, IndexError) as e:
            print(f"Configuration error: Could not find webhook_url in first trigger action. {e}")
            return
    else:
        print("DSL-only mode: Using placeholder channel ID.")

    # 3. Generate DSL
    monitor_dsl = generate_monitor_dsl(config, channel_id)

    # 4. Save DSL
    save_monitor_dsl(monitor_dsl, "yaml_generated_monitor.json")

    # 5. Post Monitor
    if args.out == 'post':
        post_monitor(monitor_dsl)
    else:
        print("DSL-only mode: Monitor not posted to OpenSearch.")

    print("Done.")

if __name__ == "__main__":
    main()
