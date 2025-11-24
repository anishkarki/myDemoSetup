#!/usr/bin/env python3
"""
SMTP Webhook Server for OpenSearch Alerting
Receives webhook requests from OpenSearch and sends emails via SMTP
Enhanced with log context retrieval for error alerts
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import logging
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = "100.80.115.61"
SMTP_PORT = 1025
SMTP_FROM = "alerts@postgres-monitoring.local"

# OpenSearch Configuration
OPENSEARCH_URL = "http://localhost:19200"
OPENSEARCH_INDEX = "postgresdata"

# OpenSearch Configuration
OPENSEARCH_URL = "http://localhost:19200"
OPENSEARCH_INDEX = "postgresdata"

def get_log_context(timestamp_str, host_name, context_lines=5):
    """
    Fetch surrounding log lines for a given timestamp and host
    
    Args:
        timestamp_str: ISO timestamp of the error log
        host_name: Hostname to filter logs
        context_lines: Number of lines before and after (default 5)
    
    Returns:
        List of log entries with context
    """
    try:
        # Parse timestamp
        error_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        
        # Query for logs within ±30 seconds
        time_before = (error_time - timedelta(seconds=30)).isoformat()
        time_after = (error_time + timedelta(seconds=30)).isoformat()
        
        query = {
            "size": context_lines * 2 + 1,
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": time_before,
                                    "lte": time_after
                                }
                            }
                        },
                        {
                            "term": {
                                "host.name": host_name
                            }
                        }
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
            "_source": ["_raw", "@timestamp"]
        }
        
        response = requests.post(
            f"{OPENSEARCH_URL}/{OPENSEARCH_INDEX}/_search",
            json=query,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            hits = response.json().get('hits', {}).get('hits', [])
            return [
                {
                    "timestamp": hit["_source"]["@timestamp"],
                    "message": hit["_source"]["_raw"],
                    "is_error": timestamp_str in hit["_source"]["@timestamp"]
                }
                for hit in hits
            ]
        else:
            logger.error(f"Failed to fetch context: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching log context: {str(e)}")
        return []

def enhance_message_with_context(message, data):
    """
    Enhance email message with surrounding log context for errors
    
    Args:
        message: Original HTML message
        data: Webhook payload containing error information
    
    Returns:
        Enhanced HTML message with context
    """
    try:
        # Check if this is an error alert with timestamp info
        if 'error_timestamp' in data and 'error_host' in data:
            timestamp = data['error_timestamp']
            host = data['error_host']
            
            context_logs = get_log_context(timestamp, host)
            
            if context_logs:
                # Build context HTML
                context_html = "<div style='margin-top:20px;padding:15px;background:#f8f9fa;border:1px solid #dee2e6;border-radius:5px'>"
                context_html += "<h3 style='margin:0 0 10px 0;color:#495057'>📋 Log Context (surrounding lines)</h3>"
                
                for log in context_logs:
                    style = "padding:6px 10px;margin:2px 0;font-family:Consolas,monospace;font-size:12px;border-left:3px solid "
                    if log['is_error']:
                        style += "#dc3545;background:#ffe6e6;font-weight:bold"
                    else:
                        style += "#ced4da;background:#fff"
                    
                    context_html += f"<div style='{style}'>"
                    context_html += f"<span style='color:#6c757d;font-size:10px'>{log['timestamp']}</span><br/>"
                    context_html += f"{log['message']}</div>"
                
                context_html += "</div>"
                
                # Insert context before closing body tag
                if '</body>' in message:
                    message = message.replace('</body>', context_html + '</body>')
                else:
                    message += context_html
                    
        return message
        
    except Exception as e:
        logger.error(f"Error enhancing message: {str(e)}")
        return message

@app.route('/webhook/send-email', methods=['POST'])
def send_email():
    """
    Webhook endpoint to send emails
    Expected JSON payload:
    {
        "recipients": ["user1@example.com", "user2@example.com"],
        "subject": "Email subject",
        "message": "HTML or plain text message",
        "error_timestamp": "2025-11-24T08:30:00Z",  # Optional: for context retrieval
        "error_host": "patroni1"  # Optional: for context retrieval
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Received webhook request: {json.dumps(data, indent=2)}")
        
        recipients = data.get('recipients', [])
        subject = data.get('subject', 'OpenSearch Alert')
        message = data.get('message', '')
        
        if not recipients:
            return jsonify({"error": "No recipients specified"}), 400
        
        # Enhance message with log context if error info provided
        message = enhance_message_with_context(message, data)
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_FROM
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        
        # Check if message is HTML
        if message.strip().startswith('<html>'):
            part = MIMEText(message, 'html', 'utf-8')
        else:
            part = MIMEText(message, 'plain', 'utf-8')
        
        msg.attach(part)
        
        # Send email via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.sendmail(SMTP_FROM, recipients, msg.as_string())
        
        logger.info(f"Email sent successfully to {recipients}")
        return jsonify({
            "status": "success",
            "message": f"Email sent to {len(recipients)} recipient(s)",
            "recipients": recipients
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
