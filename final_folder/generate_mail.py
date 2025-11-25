#!/usr/bin/env python3
"""Generate an HTML email body and a Markdown version for a host/port action."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent


def build_html(host: str, port: int, action: str) -> str:
    """Return a formatted HTML snippet for the action."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    return dedent(
        f"""\
        <!doctype html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <title>Action Notice</title>
          <style>
            body {{
              font-family: "Segoe UI", Tahoma, sans-serif;
              background: #f7f9fb;
              color: #0f172a;
              padding: 24px;
            }}
            .card {{
              max-width: 640px;
              margin: auto;
              background: #ffffff;
              border-radius: 12px;
              box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
              border: 1px solid #e2e8f0;
              overflow: hidden;
            }}
            .header {{
              padding: 18px 24px;
              background: linear-gradient(120deg, #2563eb, #0ea5e9);
              color: #f8fafc;
              font-size: 20px;
              font-weight: 700;
              letter-spacing: 0.4px;
            }}
            .content {{ padding: 20px 24px 10px; }}
            .content p {{ margin: 0 0 12px; line-height: 1.6; }}
            .pill {{
              display: inline-block;
              background: #e0f2fe;
              color: #0c4a6e;
              padding: 6px 10px;
              border-radius: 999px;
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              font-weight: 700;
              border: 1px solid #bae6fd;
            }}
            table {{
              width: 100%;
              border-collapse: collapse;
              margin: 12px 0 6px;
            }}
            th, td {{
              text-align: left;
              padding: 10px 12px;
              border-bottom: 1px solid #e2e8f0;
              font-size: 14px;
            }}
            th {{ width: 28%; color: #475569; }}
            .footer {{
              padding: 14px 24px 20px;
              font-size: 12px;
              color: #64748b;
              background: #f8fafc;
              border-top: 1px solid #e2e8f0;
            }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="header">Action Required</div>
            <div class="content">
              <p><span class="pill">Action</span></p>
              <p>The following action is requested for the specified endpoint.</p>
              <table aria-label="Action details">
                <tr><th scope="row">Action</th><td>{action}</td></tr>
                <tr><th scope="row">Hostname</th><td>{host}</td></tr>
                <tr><th scope="row">Port</th><td>{port}</td></tr>
                <tr><th scope="row">Generated (UTC)</th><td>{timestamp}</td></tr>
              </table>
            </div>
            <div class="footer">This message was auto-generated for notification purposes.</div>
          </div>
        </body>
        </html>
        """
    )


def build_markdown(host: str, port: int, action: str) -> str:
    """Return a Markdown representation mirroring the HTML content."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    return dedent(
        f"""\
        # Action Required

        **Action:** `{action}`

        The following action is requested for the specified endpoint.

        | Field | Value |
        | --- | --- |
        | Action | {action} |
        | Hostname | {host} |
        | Port | {port} |
        | Generated (UTC) | {timestamp} |

        _This message was auto-generated for notification purposes._
        """
    )


def write_files(output_dir: Path, host: str, port: int, action: str) -> None:
    """Create HTML and Markdown files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "action_notice.html"
    md_path = output_dir / "action_notice.md"
    html_path.write_text(build_html(host, port, action), encoding="utf-8")
    md_path.write_text(build_markdown(host, port, action), encoding="utf-8")
    print(f"HTML written to: {html_path}")
    print(f"Markdown written to: {md_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an HTML email and Markdown summary for a host/port action."
    )
    parser.add_argument("hostname", help="Target hostname or IP")
    parser.add_argument("port", type=int, help="Target port number")
    parser.add_argument("action", help="Description of the requested action")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("/home/swordfish/EveryThing0and1/myDemoSetup/final_folder/reports"),
        help="Output directory for generated files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_files(args.output, args.hostname, args.port, args.action)


if __name__ == "__main__":
    main()
