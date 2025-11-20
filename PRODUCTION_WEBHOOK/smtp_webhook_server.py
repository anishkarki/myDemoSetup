#!/usr/bin/env python3
"""
SMTP Webhook Server for OpenSearch Alerting
Receives webhook requests from OpenSearch and sends emails via SMTP
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_HOST = "100.80.115.61"
SMTP_PORT = 1025
SMTP_FROM = "alerts@postgres-monitoring.local"

@app.route('/webhook/send-email', methods=['POST'])
def send_email():
    """
    Webhook endpoint to send emails
    Expected JSON payload:
    {
        "recipients": ["user1@example.com", "user2@example.com"],
        "subject": "Email subject",
        "message": "HTML or plain text message"
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
