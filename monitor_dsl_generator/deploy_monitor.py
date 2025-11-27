#!/usr/bin/env python3
"""
Deploy OpenSearch Monitor
Reads a Monitor JSON file and posts it to the OpenSearch Alerting API.
"""

import argparse
import json
import sys
import ssl
import os
from urllib import request, error

def deploy_monitor(file_path, url, username=None, password=None, token=None, verify_ssl=False):
    # 1. Read the Monitor JSON
    try:
        with open(file_path, 'r') as f:
            monitor_data = json.load(f)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Prepare the Request
    api_endpoint = f"{url.rstrip('/')}/_plugins/_alerting/monitors"
    data = json.dumps(monitor_data).encode('utf-8')
    
    req = request.Request(api_endpoint, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    # 3. Authentication
    if token:
        req.add_header('Authorization', f"Bearer {token}")
    elif username and password:
        # Basic Auth
        import base64
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        req.add_header('Authorization', f"Basic {b64_auth}")

    # 4. SSL Context
    ctx = ssl.create_default_context()
    if not verify_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    # 5. Send Request
    print(f"🚀 Deploying monitor '{monitor_data.get('name', 'Unknown')}' to {api_endpoint}...")
    try:
        with request.urlopen(req, context=ctx) as response:
            response_body = response.read().decode('utf-8')
            result = json.loads(response_body)
            
            print(f"✅ Monitor created successfully!")
            print(f"   ID: {result.get('_id')}")
            print(f"   Version: {result.get('_version')}")
            return result
            
    except error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        try:
            error_body = e.read().decode('utf-8')
            print(f"   Response: {error_body}", file=sys.stderr)
        except:
            pass
        sys.exit(1)
    except error.URLError as e:
        print(f"❌ Connection Error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Deploy a monitor JSON to OpenSearch.")
    parser.add_argument("file", help="Path to the monitor JSON file")
    parser.add_argument("--url", default="http://100.80.115.61:19200", help="OpenSearch URL")
    parser.add_argument("-u", "--username", help="Basic Auth Username")
    parser.add_argument("-p", "--password", help="Basic Auth Password")
    parser.add_argument("-t", "--token", help="Bearer Token")
    parser.add_argument("--insecure", action="store_true", help="Skip SSL verification")

    args = parser.parse_args()

    # Environment variable fallback
    username = args.username or os.environ.get("OPENSEARCH_USERNAME")
    password = args.password or os.environ.get("OPENSEARCH_PASSWORD")
    token = args.token or os.environ.get("OPENSEARCH_TOKEN")

    deploy_monitor(args.file, args.url, username, password, token, not args.insecure)

if __name__ == "__main__":
    main()
