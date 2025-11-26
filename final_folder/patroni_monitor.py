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

    # 6. /history (Cluster history)
    try:
        r = requests.get(f"{base_url}/history", timeout=5)
        if r.status_code == 200:
            data["history"] = r.json()
    except Exception as e:
        data["history"] = {"_error": str(e)}

    # 7. Role Checks (Load Balancer endpoints)
    data["role_checks"] = {}
    for endpoint in ["leader", "replica", "standby-leader", "synchronous", "asynchronous"]:
        try:
            r = requests.get(f"{base_url}/{endpoint}", timeout=2)
            data["role_checks"][endpoint] = r.status_code
        except Exception:
            data["role_checks"][endpoint] = "Unreachable"

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
            # Strip labels to get the metric name
            if "{" in key:
                key = key.split("{")[0]
            metrics[key] = val
    return metrics


def analyze_alerts(data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Analyze data for potential issues."""
    alerts = []
    
    # 1. Health
    if not data.get("is_healthy"):
        alerts.append({"level": "CRITICAL", "message": f"Node health check failed (Status: {data.get('health_status')})"})

    # 2. Node State
    node = data.get("node", {})
    state = node.get("state", "unknown")
    role = node.get("role", "unknown")
    if state not in ["running", "streaming"]:
        alerts.append({"level": "WARNING", "message": f"Node state is '{state}' (Role: {role})"})
    
    if node.get("pending_restart"):
        alerts.append({"level": "WARNING", "message": "Node has a pending restart flag set."})

    # 3. Metrics
    metrics = data.get("metrics", {})
    if metrics.get("patroni_failsafe_mode_is_active", "0") == "1":
        alerts.append({"level": "WARNING", "message": "Cluster is in Failsafe Mode."})
    
    if metrics.get("patroni_is_paused", "0") == "1":
        alerts.append({"level": "INFO", "message": "Cluster is in Maintenance Mode (Paused)."})

    # 4. Cluster Members
    cluster = data.get("cluster", {})
    members = cluster.get("members", [])
    leader_found = False
    if members:
        for m in members:
            if m.get("role") == "leader":
                leader_found = True
            
            m_name = m.get("name", "Unknown")
            m_state = m.get("state", "unknown")
            if m_state not in ["running", "streaming"]:
                 alerts.append({"level": "WARNING", "message": f"Member '{m_name}' is in state '{m_state}'."})
            
            # Lag check
            lag = m.get("lag")
            if lag is not None and isinstance(lag, (int, float)) and lag > 10485760: # > 10MB
                 alerts.append({"level": "WARNING", "message": f"Member '{m_name}' has high replication lag: {lag}"})

        if not leader_found:
            alerts.append({"level": "CRITICAL", "message": "No leader found in cluster members list."})
    else:
        alerts.append({"level": "WARNING", "message": "No cluster members information available."})

    return alerts


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
    patroni_version = metrics.get("patroni_version", "Unknown")
    is_paused = metrics.get("patroni_is_paused", "0") == "1"
    is_failsafe = metrics.get("patroni_failsafe_mode_is_active", "0") == "1"
    is_unlocked = metrics.get("patroni_cluster_unlocked", "0") == "1"

    # DCS Config
    dcs_ttl = config.get("ttl", "N/A")
    dcs_loop = config.get("loop_wait", "N/A")
    dcs_retry = config.get("retry_timeout", "N/A")
    dcs_max_lag = config.get("maximum_lag_on_failover", "N/A")

    # History
    history_html = ""
    history = data.get("history", [])
    if isinstance(history, list) and history:
        for h in history:
            # Patroni history: [timeline, lsn, reason, timestamp]
            if isinstance(h, list) and len(h) >= 4:
                 history_html += f"<tr><td>{h[0]}</td><td>{h[1]}</td><td>{h[2]}</td><td>{h[3]}</td></tr>"
            else:
                 history_html += f"<tr><td colspan='4'>{str(h)}</td></tr>"
    elif isinstance(history, dict) and "_error" in history:
        history_html = f"<tr><td colspan='4'>Error: {history['_error']}</td></tr>"
    else:
        history_html = "<tr><td colspan='4'>No history found.</td></tr>"

    # Role Checks
    role_checks_html = ""
    role_checks = data.get("role_checks", {})
    for r_name, r_code in role_checks.items():
        color = "#16a34a" if r_code == 200 else "#64748b"
        role_checks_html += f"<div class='metric-box'><div class='metric-label'>/{r_name}</div><div class='metric-value' style='color: {color}'>{r_code}</div></div>"
    
    # Alerts
    alerts = analyze_alerts(data)
    alerts_html = ""
    if alerts:
        for alert in alerts:
            alerts_html += f"<div class='alert-item alert-{alert['level']}'><strong>{alert['level']}:</strong> {alert['message']}</div>"
    else:
        alerts_html = "<div class='alert-item' style='border-left-color: #16a34a; color: #16a34a;'>No active alerts. System is healthy.</div>"

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
            
            /* Accordion Styles */
            .accordion {{ background-color: #f8fafc; color: #334155; cursor: pointer; padding: 16px; width: 100%; border: 1px solid #e2e8f0; text-align: left; outline: none; font-size: 16px; transition: 0.4s; border-radius: 8px; margin-bottom: 12px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }}
            .active, .accordion:hover {{ background-color: #f1f5f9; }}
            .accordion:after {{ content: '+'; font-size: 20px; color: #64748b; }}
            .active:after {{ content: '-'; }}
            .panel {{ padding: 0 18px; background-color: white; max-height: 0; overflow: hidden; transition: max-height 0.2s ease-out; margin-bottom: 12px; }}
            .alert-item {{ padding: 12px; border-left: 4px solid #ccc; margin: 8px 0; background: #fff; border-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
            .alert-CRITICAL {{ border-left-color: #dc2626; background: #fef2f2; color: #991b1b; }}
            .alert-WARNING {{ border-left-color: #f59e0b; background: #fffbeb; color: #92400e; }}
            .alert-INFO {{ border-left-color: #3b82f6; background: #eff6ff; color: #1e40af; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">
              <span>Patroni Monitor</span>
              <span class="status-badge">{state}</span>
            </div>
            <div class="content">
              
              <!-- Alerts Accordion -->
              <button class="accordion">Active Alerts <span style="background: {'#ef4444' if alerts else '#16a34a'}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px;">{len(alerts)}</span></button>
              <div class="panel" style="max-height: {'500px' if alerts else '0px'}">
                {alerts_html}
              </div>

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
                <tr><th>Patroni Version</th><td>{patroni_version}</td></tr>
                <tr><th>Server Version</th><td>{node.get('server_version', 'Unknown')}</td></tr>
                <tr><th>Cluster Name</th><td>{node.get('cluster_name', 'Unknown')}</td></tr>
                <tr><th>Pending Restart</th><td>{node.get('pending_restart', False)}</td></tr>
              </table>

              <div class="section-title">Cluster Control Flags</div>
              <div class="metric-grid">
                <div class="metric-box">
                  <div class="metric-label">Maintenance Mode (Paused)</div>
                  <div class="metric-value" style="color: {'#d97706' if is_paused else '#0f172a'}">{'YES' if is_paused else 'NO'}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">Failsafe Mode</div>
                  <div class="metric-value" style="color: {'#dc2626' if is_failsafe else '#0f172a'}">{'ACTIVE' if is_failsafe else 'INACTIVE'}</div>
                </div>
                <div class="metric-box">
                  <div class="metric-label">Cluster Unlocked</div>
                  <div class="metric-value">{'YES' if is_unlocked else 'NO'}</div>
                </div>
              </div>

              <div class="section-title">DCS Configuration</div>
              <table>
                <tr><th>TTL</th><td>{dcs_ttl} s</td><th>Loop Wait</th><td>{dcs_loop} s</td></tr>
                <tr><th>Retry Timeout</th><td>{dcs_retry} s</td><th>Max Lag on Failover</th><td>{dcs_max_lag} bytes</td></tr>
              </table>

              <div class="section-title">Load Balancer Checks (HTTP Status)</div>
              <div class="metric-grid">
                {role_checks_html}
              </div>

              <div class="section-title">Cluster History</div>
              <table>
                <thead><tr><th>Timeline</th><th>LSN</th><th>Reason</th><th>Timestamp</th></tr></thead>
                <tbody>{history_html}</tbody>
              </table>

              <div class="section-title">Configuration (Partial)</div>
              <pre>{json.dumps(config, indent=2)[:1000]} ...</pre>
              
            </div>
            <div class="footer">Generated at {timestamp} UTC</div>
          </div>
          <script>
            var acc = document.getElementsByClassName("accordion");
            var i;
            for (i = 0; i < acc.length; i++) {{
              acc[i].addEventListener("click", function() {{
                this.classList.toggle("active");
                var panel = this.nextElementSibling;
                if (panel.style.maxHeight) {{
                  panel.style.maxHeight = null;
                }} else {{
                  panel.style.maxHeight = panel.scrollHeight + "px";
                }} 
              }});
            }}
          </script>
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

    # History
    history_rows = []
    history = data.get("history", [])
    if isinstance(history, list) and history:
        for h in history:
            if isinstance(h, list) and len(h) >= 4:
                 history_rows.append(f"| {h[0]} | {h[1]} | {h[2]} | {h[3]} |")
            else:
                 history_rows.append(f"| {str(h)} | | | |")
    else:
        history_rows.append("| N/A | N/A | N/A | N/A |")
    history_table = "\n".join(history_rows)

    # Role Checks
    role_checks = data.get("role_checks", {})
    role_checks_str = ", ".join([f"**{k}:** {v}" for k, v in role_checks.items()])

    # Metrics extraction for Markdown
    patroni_version = metrics.get("patroni_version", "Unknown")
    is_paused = metrics.get("patroni_is_paused", "0") == "1"
    is_failsafe = metrics.get("patroni_failsafe_mode_is_active", "0") == "1"
    
    # DCS Config
    config = data.get("config", {})
    dcs_ttl = config.get("ttl", "N/A")
    dcs_loop = config.get("loop_wait", "N/A")

    # Alerts
    alerts = analyze_alerts(data)
    alerts_md = ""
    if alerts:
        for alert in alerts:
            icon = "🔴" if alert['level'] == "CRITICAL" else "🟠" if alert['level'] == "WARNING" else "🔵"
            alerts_md += f"- {icon} **{alert['level']}:** {alert['message']}\n"
    else:
        alerts_md = "- ✅ No active alerts. System is healthy."

    return dedent(
        f"""\
        # Patroni Comprehensive Monitor Report

        **Status:** {health_icon} {state}
        **Generated:** {timestamp}

        ## 1. Active Alerts
        {alerts_md}

        ## 2. Cluster State & Health
        - **Leader:** {role if role == 'Leader' else 'See Members Table'}
        - **Health:** {health_icon} {"Healthy" if is_healthy else "Unhealthy"}
        - **PG Running:** {metrics.get("patroni_postgres_running", "Unknown")}
        - **Endpoints:** {role_checks_str}
        - **Paused:** {is_paused} | **Failsafe:** {is_failsafe}

        ## 3. Cluster Members (Replication & Failover Readiness)
        
        | Name | Role | State | Lag | Timeline |
        | --- | --- | --- | --- | --- |
        {members_table}

        ## 4. Cluster History
        
        | Timeline | LSN | Reason | Timestamp |
        | --- | --- | --- | --- |
        {history_table}

        ## 5. Node Details
        - **Hostname:** `{host}`
        - **Port:** `{port}`
        - **Patroni Version:** `{patroni_version}`
        - **Server Version:** `{node.get('server_version', 'Unknown')}`
        - **Cluster Name:** `{node.get('cluster_name', 'Unknown')}`
        - **Pending Restart:** `{node.get('pending_restart', False)}`
        
        ## 6. DCS Configuration
        - **TTL:** `{dcs_ttl}`
        - **Loop Wait:** `{dcs_loop}`

        ## 7. WAL & Metrics
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
