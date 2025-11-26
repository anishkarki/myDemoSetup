import requests
import json
from datetime import datetime

# OpenSearch Config
HOST = "100.80.115.61"
PORT = 19200
INDEX = "patronidata"
URL = f"http://{HOST}:{PORT}/{INDEX}/_doc"

def inject_log(message):
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    payload = {
        "@timestamp": timestamp,
        "host": { "name": "test-injector" },
        "_raw": f"{timestamp} UTC [TEST]: {message}"
    }
    
    try:
        resp = requests.post(URL, json=payload, timeout=5)
        print(f"Injecting: {message}")
        print(f"  -> Response: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"  -> Error: {e}")

if __name__ == "__main__":
    print(f"Injecting test logs into {INDEX}...")
    
    # 1. Inject a Class XX (Internal Error) - FATAL
    # Matches monitor: "Postgres Internal Errors (Class XX)"
    inject_log("FATAL:  XX000: Simulated internal system error (Class XX)")

    # 2. Inject a Class 08 (Connection Exception) - FATAL
    # Matches monitor: "Connection Exceptions (Class 08)"
    inject_log("FATAL:  08006: Simulated connection failure (Class 08)")
    
    # 3. Inject a Class 58 (System Error) - ERROR
    # Matches monitor: "Disk I/O Errors (Class 58)"
    inject_log("ERROR:  58P01: Simulated disk I/O error (Class 58)")

    print("Done.")
