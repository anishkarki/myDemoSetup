# OpenSearch Dynamic Monitor & Alerting Toolkit

This toolkit provides a flexible, automated way to generate OpenSearch Monitors, configure Alerting channels, and bridge Webhook alerts to SMTP (Email) destinations like MailHog. It supports both CLI-based generation and YAML-based configuration for Infrastructure-as-Code (IaC) workflows.

## 🚀 Features

*   **YAML-Driven Configuration**: Define monitors, triggers, and actions in a simple YAML file.
*   **Webhook-to-Email Relay**: A lightweight Flask server (`webhook_mail_relay.py`) that converts OpenSearch Webhook alerts into SMTP emails (useful for local dev/MailHog).
*   **Dynamic DSL Generation**: Automatically generates OpenSearch Query DSL and Monitor JSON.
*   **Automated Deployment**: Scripts to create Notification Channels and post Monitors directly to the OpenSearch API.
*   **Reporting**: Fetch logs and generate HTML reports.

## dV Prerequisites

*   Python 3.x
*   OpenSearch (running on `localhost:9200` or accessible network)
*   MailHog (running on `localhost:1025` for SMTP, `8025` for UI)
*   `pip` (Python package manager)

## 📦 Installation

1.  **Clone/Navigate to the directory**:
    ```bash
    cd /home/swordfish/EveryThing0and1/work_script
    ```

2.  **Set up a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install requests flask pyyaml
    ```

## 🛠️ Components & Usage

### 1. Webhook Mail Relay (`webhook_mail_relay.py`)
*Description*: Bridges the gap between OpenSearch Webhooks and SMTP. OpenSearch sends a JSON payload to this service, which then formats and sends an email.

*   **Start the Relay**:
    ```bash
    # Runs on port 5001
    python3 webhook_mail_relay.py
    ```
    *Note: Keep this running in a separate terminal or background process.*

### 2. YAML Monitor Generator (`generate_monitor_from_yaml.py`)
*Description*: The recommended way to manage monitors. Reads `monitor_config.yaml`, generates the DSL, and deploys it.

1.  **Configure**: Edit `monitor_config.yaml`.
    ```yaml
    monitor:
      name: "Production Error Monitor"
      inputs:
        indices: ["patronidata"]
        filters:
          - field: "message"
            match: "error"
        exclude_filters:
          - field: "message"
            match: "user=,"
      triggers:
        ...
    ```
2.  **Run**:
    ```bash
    python3 generate_monitor_from_yaml.py
    ```
    *   **Output**: Saves DSL to `dsl_report/yaml_generated_monitor.json` and posts to OpenSearch.

### 3. CLI Monitor Generator (`generate_dynamic_monitor.py`)
*Description*: Quick, ad-hoc monitor generation via command line arguments.

*   **Usage**:
    ```bash
    python3 generate_dynamic_monitor.py \
      --name "CLI Generated Monitor" \
      --index "patronidata" \
      --filter "error" \
      --filter "fatal" \
      --output "dsl_report/cli_monitor.json"
    ```

### 4. Setup Script (`setup_opensearch_monitor.py`)
*Description*: A standalone script that sets up a specific "Patroni Error Monitor" and the Webhook Channel. Useful for initial setup or testing.

*   **Run**:
    ```bash
    python3 setup_opensearch_monitor.py
    ```

### 5. Log Reporting (`fetch_and_report.py`)
*Description*: Fetches logs from OpenSearch and generates a static HTML report.

*   **Usage**:
    ```bash
    python3 fetch_and_report.py --host patroni1 --time 1h --output html_report/my_report.html
    ```

## 📂 File Structure

| File | Description |
| :--- | :--- |
| `monitor_config.yaml` | Main configuration file for monitors. |
| `webhook_mail_relay.py` | Flask server receiving webhooks and sending emails. |
| `generate_monitor_from_yaml.py` | Script to deploy monitors based on YAML config. |
| `generate_dynamic_monitor.py` | CLI tool for generating monitor JSONs. |
| `setup_opensearch_monitor.py` | Setup script for channels and basic monitors. |
| `fetch_and_report.py` | Generates HTML reports from logs. |
| `dsl_report/` | Directory where generated Monitor DSL JSONs are saved. |
| `html_report/` | Directory where HTML log reports are saved. |

## 🧪 Testing the Pipeline

1.  **Ensure Infrastructure is Up**: OpenSearch and MailHog must be running.
2.  **Start Relay**: `python3 webhook_mail_relay.py`
3.  **Deploy Monitor**: `python3 generate_monitor_from_yaml.py`
4.  **Trigger Alert**: Inject a log that matches your filter.
    ```bash
    curl -X POST "http://localhost:19200/patronidata/_doc" -H 'Content-Type: application/json' -d '{
      "@timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
      "message": "CRITICAL error: Test trigger",
      "host": { "name": "test-host" }
    }'
    ```
5.  **Verify**: Check MailHog UI at `http://localhost:8025`.

## ⚠️ Troubleshooting

*   **Port 5001 in use**: If `webhook_mail_relay.py` fails, check if another instance is running: `lsof -i :5001` and kill it.
*   **Connection Refused**: Ensure OpenSearch is reachable at `localhost:19200`. If running in Docker, the scripts attempt to auto-detect the host IP, but you may need to adjust `OPENSEARCH_URL`.
