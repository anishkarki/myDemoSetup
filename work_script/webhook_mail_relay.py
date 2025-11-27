import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Configuration
SMTP_HOST = "localhost"
SMTP_PORT = 1025
SENDER_EMAIL = "monitor-alert@opensearch.local"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/webhook/send-email', methods=['POST'])
def send_email():
    try:
        data = request.json
        logger.info(f"Received webhook payload: {data}")

        recipient = data.get('recipient_email')
        subject = data.get('subject_title')
        message_body = data.get('message')

        if not recipient or not subject or not message_body:
            return jsonify({"error": "Missing required fields"}), 400

        # Create message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))

        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.send_message(msg)
        
        logger.info(f"Email sent to {recipient}")
        return jsonify({"status": "success", "message": "Email sent"}), 200

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on all interfaces so Docker containers can reach it
    app.run(host='0.0.0.0', port=5001)
