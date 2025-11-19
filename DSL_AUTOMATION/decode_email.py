#!/usr/bin/env python3
"""Decode quoted-printable email content to HTML"""

import quopri

# Read the quoted-printable encoded content
with open('/tmp/final_body.html', 'r') as f:
    content = f.read()

# Decode quoted-printable
decoded = quopri.decodestring(content.encode('utf-8')).decode('utf-8')

# Write to email_preview.html
with open('email_preview.html', 'w') as f:
    f.write('<!DOCTYPE html>\n')
    f.write(decoded)

print('✓ Email preview decoded and saved to email_preview.html')
