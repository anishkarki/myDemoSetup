#!/usr/bin/env python3
"""
Monitor Patroni status and generate HTML/Markdown reports.
Monitors: Patroni status, Health, Leader, LSN, WAL, Replication stats, Space available.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Optional, List

import requests


def fetch_patroni_data(host: str, port: int) -> Dict[str, Any]:
    """Fetch comprehensive status from Patroni API."""
    base_url = f"http://{host}:{port}"
    data = {
        "node": {},
        "cluster": {},
        "metrics": {},
        "config": {},
        "meta": {"host": host, "port": port, "timestamp": datetime.now(timezone.utc)}
    }
    
    # 1. /patroni (Node status)
    try:
        r = requests.get(f"{base_url}/patroni", timeout=5)
        if r.status_code == 200:
            data["node"] = r.json()
            data["node"]["_status_code"] = r.status_code
        else:
            data["node"]["_error"] = f"HTTP {r.status_code}"
    except Exception as e:
        data["node"]["_error"] = str(e)

    # 2. /cluster (Cluster state)
    try:
        r = requests.get(f"{base_url}/cluster", timeout=5)
        if r.status_code == 200:
            data["cluster"] = r.json()
    except Exception as e:
        data["cluster"]["_error"] = str(e)

    # 3. /metrics (Prometheus)
    try:
        r = requests.get(f"{base_url}/metrics", timeout=5)
        if r.status_code == 200:
            data["metrics"] = parse_prometheus(r.text)
    except Exception as e:
        data["metrics"]["_error"] = str(e)
        
    # 4. /config (Configuration)
    try:
        r = requests.get(f"{base_url}/config", timeout=5)
        if r.status_code == 200:
            data["config"] = r.json()
    except Exception as e:
        data["config"]["_error"] = str(e)

    # 5. /health (Simple check)
    try:
        r = requests.get(f"{base_url}/health", timeout=5)
        data["health_status"] = r.status_code
        data["is_healthy"] = r.status_code == 200
    except Exception:
        data["health_status"] = "Unreachable"
        data["is_healthy"] = False

    return data


def parse_prometheus(text: str) -> Dict[str, str]:
    """Simple parser for Prometheus metrics."""
    metrics = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            key = parts[0]
            val = parts[1]
            # Store simple keys, ignore complex labels for now unless needed
            if "{" not in key: 
                metrics[key] = val
    return metrics


def build_monitor_html(data: Dict[str, Any]) -> str:
    """Generate HTML report for Patroni status."""
    meta = data["meta"]
    node = data.get("node", {})
    cluster = data.get("cluster", {})
    metrics = data.get("metrics", {})
    config = data.get("config", {})
    
    timestamp = meta["timestamp"].strftime("%Y-%m-%d %H:%M:%SZ")
    host = meta["host"]
    port = meta["port"]
    
    is_healthy = data.get("is_healthy", False)
    health_color = "#16a34a" if is_healthy else "#dc2626"
    health_text = "Healthy" if is_healthy else "Unhealthy"
    
    role = node.get("role", "Unknown").title()
    state = node.get("state", "Unknown").title()
    
    # Cluster Members
    members_html = ""
    members = cluster.get("members", [])
    if members:
        for m in members:
            m_name = m.get("name", "Unknown")
            m_role = m.get("role", "replica").title()
            m_state = m.get("state", "running").title()
            m_lag = m.get("lag", 0)
            m_tl = m.get("timeline", "?")
            members_html += f"<tr><td>{m_name}</td><td>{m_role}</td><td>{m_state}</td><td>{m_lag}</td><td>{m_tl}</td></tr>"
    else:
        members_html = "<tr><td colspan='5'>No cluster members found or /cluster endpoint unavailable.</td></tr>"

    # Metrics
    wal_gen = metrics.get("patroni_xlog_location", "N/A")
    pg_running = metrics.get("patroni_postgres_running", "N/A")
    
    return dedent(
        f"""\
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <title>Patroni Comprehensive Monitor</title>
          <style>
            body {{ font-family: "Segoe UI", Tahoma, sans-serif; background: #f7f9fb; color: #0f172a; padding: 24px; }}
            .card {{ max-width: 900px; margin: auto; background: #ffffff; border-radius: 12px; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08); border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ padding: 18px 24px; background: linear-gradient(120deg, #4f46e5, #818cf8); color: #f8fafc; font-size: 20px; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }}
            .status-badge {{ background: rgba(255, 255, 255, 0.2); padding: 4px 12px; border-radius: 99px; font-size: 14px; }}
            .content {{ padding: 24px; }}
            .section-title {{ font-size: 16px; font-weight: 700; margin: 24px 0 12px; color: #334155; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
            .metric-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }}
            .metric-label {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
            .metric-value {{ font-size: 18px; font-weight: 700; color: #0f172a; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
            th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f1f5f9; color: #475569; font-weight: 600; }}
            .footer {{ padding: 14px 24px; font-size: 12px; color: #64748b; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; }}
            pre {{ background: #f1f5f9; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 12px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <span>Patroni Monitor</span>
              <span class="status-badge">{state}</span>
            </div>
            <div class="content">
              
              <div class="metric-grid">
                <div class="metric-box">
                  <div class="metric-label">Health Status</div>
                  <div class="metric-value" style="color: {health_color}">{health_text}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">Role</div>
                  <div class="metric-value">{role}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">PG Running</div>
                  <div class="metric-value">{pg_running}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">WAL Location</div>
                  <div class="metric-value" style="font-size: 14px; word-break: break-all;">{wal_gen}</div>
                </div>
              </div>

              <div class="section-title">Cluster Members</div>
              <table>
                <thead><tr><th>Name</th><th>Role</th><th>State</th><th>Lag</th><th>Timeline</th></tr></thead>
                <tbody>{members_html}</tbody>
              </table>

              <div class="section-title">Node Details</div>
              <table>
                <tr><th style="width: 30%">Hostname</th><td>{host}</td></tr>
                <tr><th>Port</th><td>{port}</td></tr>
                <tr><th>Server Version</th><td>{node.get('server_version', 'Unknown')}</td></tr>
                <tr><th>Cluster Name</th><td>{node.get('cluster_name', 'Unknown')}</td></tr>
                <tr><th>Pending Restart</th><td>{node.get('pending_restart', False)}</td></tr>
              </table>

              <div class="section-title">Configuration (Partial)</div>
              <pre>{json.dumps(config, indent=2)[:1000]} ...</pre>
              
            </div>
            <div class="footer">Generated at {timestamp} UTC</div>
          </div>
        </body>
        </html>
        """
    )


def build_monitor_markdown(data: Dict[str, Any]) -> str:
    """Generate Markdown report for Patroni status."""
    meta = data["meta"]
    node = data.get("node", {})
    cluster = data.get("cluster", {})
    metrics = data.get("metrics", {})
    
    timestamp = meta["timestamp"].strftime("%Y-%m-%d %H:%M:%SZ")
    host = meta["host"]
    port = meta["port"]
    
    is_healthy = data.get("is_healthy", False)
    health_icon = "✅" if is_healthy else "❌"
    role = node.get("role", "Unknown").title()
    state = node.get("state", "Unknown").title()
    
    # Members Table
    members_rows = []
    members = cluster.get("members", [])
    if members:
        for m in members:
            members_rows.append(f"| {m.get('name')} | {m.get('role')} | {m.get('state')} | {m.get('lag', 0)} | {m.get('timeline')} |")
    else:
        members_rows.append("| N/A | N/A | N/A | N/A | N/A |")
    members_table = "\n".join(members_rows)

    return dedent(
        f"""\
        # Patroni Comprehensive Monitor Report

        **Status:** {health_icon} {state}
        **Generated:** {timestamp}

        ## 1. Cluster State & Health
        - **Leader:** {role if role == 'Leader' else 'See Members Table'}
        - **Health:** {health_icon} {"Healthy" if is_healthy else "Unhealthy"}
        - **PG Running:** {metrics.get("patroni_postgres_running", "Unknown")}

        ## 2. Cluster Members (Replication & Failover Readiness)
        
        | Name | Role | State | Lag | Timeline |
        | --- | --- | --- | --- | --- |
        {members_table}

        ## 3. Node Details
        - **Hostname:** `{host}`
        - **Port:** `{port}`
        - **Server Version:** `{node.get('server_version', 'Unknown')}`
        - **Cluster Name:** `{node.get('cluster_name', 'Unknown')}`
        - **Pending Restart:** `{node.get('pending_restart', False)}`

        ## 4. WAL & Metrics
        - **WAL Location:** `{metrics.get("patroni_xlog_location", "N/A")}`
        - **Timeline:** `{node.get("timeline", "N/A")}`

        ---
        _Generated by Patroni Monitor Script_
        """
    )


def write_reports(output_dir: Path, data: Dict[str, Any]) -> None:
    """Write HTML and Markdown reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    html_content = build_monitor_html(data)
    md_content = build_monitor_markdown(data)
    
    html_path = output_dir / "patroni_status.html"
    md_path = output_dir / "patroni_status.md"
    
    html_path.write_text(html_content, encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")
    
    print(f"HTML Report written to: {html_path}")
    print(f"Markdown Report written to: {md_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Patroni and generate reports.")
    parser.add_argument("hostname", help="Patroni hostname or IP")
    parser.add_argument("port", type=int, help="Patroni API port")
    parser.add_argument(
        "-o", "--output", 
        type=Path, 
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports"),
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    print(f"Fetching Patroni status from {args.hostname}:{args.port}...")
    data = fetch_patroni_data(args.hostname, args.port)
    
    # Debug output for errors
    for key in ["node", "cluster", "metrics", "config"]:
        if "_error" in data.get(key, {}):
             print(f"Warning: Error fetching {key}: {data[key]['_error']}", file=sys.stderr)

    write_reports(args.output, data)


if __name__ == "__main__":
    main()
