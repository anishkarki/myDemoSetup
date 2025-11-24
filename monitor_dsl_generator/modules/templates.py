"""
Message Templates
Pre-built email and notification templates
"""


class MessageTemplates:
    """Message template library"""
    
    # Simple HTML template
    HTML_SIMPLE = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f2f2f2;text-align:left}td.log{font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word}</style>
</head><body><p><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Total hits:</strong> {{ctx.results[0].hits.total.value}}</p><table><thead><tr><th>Timestamp</th><th>Hostname</th><th>Log</th></tr></thead><tbody>{{#ctx.results.0.hits.hits}}<tr><td>{{_source.@timestamp}}</td><td>{{_source.host.name}}</td><td class="log">{{{_source._raw}}}</td></tr>{{/ctx.results.0.hits.hits}}</tbody></table></body></html>"""
    
    # Grouped by hostname template
    HTML_GROUPED_BY_HOST = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f2f2f2;text-align:left}.hostname{font-weight:bold;color:#0066cc}td.log{font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px}time{color:#555;font-size:11px;font-weight:normal}tbody tr:nth-child(odd){background:#ffffff}tbody tr:nth-child(even){background:#f9f9f9}</style>
</head><body><h2 style="color:#d9534f;margin:0 0 10px 0">🚨 Alert</h2><p><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Total hits:</strong> {{ctx.results.0.hits.total.value}}<br/><strong>Time:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}</p><table><thead><tr><th>Hostname</th><th>Timestamp</th><th>Log Entry</th></tr></thead><tbody>{{#ctx.results.0.hits.hits}}<tr><td class="hostname">{{_source.host.name}}</td><td><time>{{_source.@timestamp}}</time></td><td class="log">{{{_source._raw}}}</td></tr>{{/ctx.results.0.hits.hits}}</tbody></table></body></html>"""
    
    # Critical alerts grouped by hostname (aggregation-based)
    HTML_CRITICAL_GROUPED = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222;padding:10px}.hostname-section{margin-bottom:25px;border:2px solid #d9534f;border-radius:5px;overflow:hidden}.hostname-header{font-weight:bold;color:#fff;background:#d9534f;padding:12px 15px;font-size:16px}.log-container{background:#fff}.log-entry{padding:10px 15px;border-bottom:1px solid #ffe6e6;font-family:Menlo,Consolas,monospace;white-space:pre-wrap;word-break:break-word;font-size:12px;line-height:1.5}.log-entry:nth-child(odd){background:#fff}.log-entry:nth-child(even){background:#fff9f9}.log-entry:last-child{border-bottom:none}time{color:#666;font-size:11px;display:block;margin-bottom:4px}</style>
</head><body><h2 style="color:#d9534f;margin:0 0 15px 0">🚨 Critical Alert</h2><p style="margin-bottom:20px"><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Time:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}</p>{{#ctx.results.0.aggregations.group_by_hostname.buckets}}<div class="hostname-section"><div class="hostname-header">🔴 Hostname: {{key}} — {{doc_count}} error(s)</div><div class="log-container">{{#top_errors.hits.hits}}<div class="log-entry"><time>{{_source.@timestamp}}</time>{{{_source._raw}}}</div>{{/top_errors.hits.hits}}</div></div>{{/ctx.results.0.aggregations.group_by_hostname.buckets}}</body></html>"""
    
    # Frequency alert template (aggregation-based)
    HTML_FREQUENCY = """<html><head><meta charset="utf-8">
<style>body{font-family:Arial,Helvetica,sans-serif;color:#222}table{border-collapse:collapse;width:100%;font-size:13px;margin-bottom:20px}th,td{border:1px solid #ddd;padding:8px;vertical-align:top}th{background:#f2f2f2;text-align:left}.hostname{font-weight:bold;color:#0066cc;background:#e6f2ff;padding:10px;font-size:15px}.count{font-weight:bold;color:#d9534f;font-size:16px}.warning{background:#fff3cd;border-left:4px solid #ffc107}tr:nth-child(even){background:#f9f9f9}</style>
</head><body><h2 style="color:#ff9800;margin:0 0 10px 0">⚠️ Frequency Alert</h2><p><strong>Monitor:</strong> {{ctx.monitor.name}}<br/><strong>Trigger:</strong> {{ctx.trigger.name}}<br/><strong>Time:</strong> {{ctx.periodStart}} to {{ctx.periodEnd}}</p>{{#ctx.results.0.aggregations.group_by_hostname.buckets}}<div class="hostname">📍 Hostname: {{key}} ({{doc_count}} total)</div><table><thead><tr><th width="100">Count</th><th>Field</th><th>Value</th></tr></thead><tbody>{{#group_by_field.buckets}}<tr class="warning"><td class="count">{{doc_count}}×</td><td>Error</td><td>{{key}}</td></tr>{{/group_by_field.buckets}}</tbody></table>{{/ctx.results.0.aggregations.group_by_hostname.buckets}}</body></html>"""
    
    # Plain text template
    PLAIN_TEXT = """Monitor: {{ctx.monitor.name}}
Trigger: {{ctx.trigger.name}}
Total hits: {{ctx.results[0].hits.total.value}}

Log Entries:
{{#ctx.results.0.hits.hits}}
- [{{_source.@timestamp}}] {{_source.host.name}}: {{_source._raw}}
{{/ctx.results.0.hits.hits}}"""
    
    def get_template(self, template_type: str) -> str:
        """Get template by type"""
        templates = {
            'html_simple': self.HTML_SIMPLE,
            'html_grouped_by_host': self.HTML_GROUPED_BY_HOST,
            'html_critical_grouped': self.HTML_CRITICAL_GROUPED,
            'html_frequency': self.HTML_FREQUENCY,
            'plain_text': self.PLAIN_TEXT
        }
        
        return templates.get(template_type, self.HTML_SIMPLE)
