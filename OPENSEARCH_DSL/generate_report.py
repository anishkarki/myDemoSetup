#!/usr/bin/env python3
import json
import sys

# Read from stdin or file
if len(sys.argv) > 1:
    with open(sys.argv[1]) as f:
        data = json.load(f)
else:
    data = json.load(sys.stdin)

hits = data.get('hits', {}).get('hits', [])
aggs = data.get('aggregations', {}).get('by_source', {}).get('buckets', [])

print(f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Patroni Failover Analysis</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
h2 {{ color: #2c3e50; }}
.summary {{ background: white; padding: 15px; margin-bottom: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.summary-item {{ display: inline-block; margin-right: 30px; padding: 10px; }}
.summary-label {{ font-weight: bold; color: #7f8c8d; font-size: 12px; }}
.summary-value {{ font-size: 24px; color: #2980b9; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
th {{ background-color: #34495e; color: white; padding: 12px; text-align: left; }}
td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; vertical-align: top; }}
tr:hover {{ background-color: #f8f9fa; }}
.timestamp {{ white-space: nowrap; font-family: 'Courier New', monospace; color: #2980b9; font-size: 11px; }}
.node {{ font-weight: bold; padding: 4px 8px; border-radius: 3px; display: inline-block; font-size: 12px; }}
.patroni1 {{ background-color: #fee; color: #c0392b; }}
.patroni2 {{ background-color: #efe; color: #27ae60; }}
.message {{ font-family: 'Courier New', monospace; font-size: 11px; line-height: 1.4; word-break: break-all; }}
.promote {{ background-color: #d4edda !important; }}
.demote {{ background-color: #f8d7da !important; }}
.connection {{ background-color: #fff3cd !important; }}
.timeline {{ background-color: #d1ecf1 !important; }}
.keyword {{ background-color: #ffffcc; padding: 2px 4px; border-radius: 2px; font-weight: bold; }}
.no-data {{ text-align: center; padding: 40px; color: #7f8c8d; font-style: italic; }}
</style>
</head>
<body>
<h2>🔄 Patroni Failover Event Analysis - PostgreSQL 17</h2>

<div class="summary">
  <div class="summary-item">
    <div class="summary-label">Total Events</div>
    <div class="summary-value">{len(hits)}</div>
  </div>""")

for bucket in aggs:
    node = bucket['key'].split('/')[-1] if '/' in bucket['key'] else bucket['key']
    print(f"""  <div class="summary-item">
    <div class="summary-label">{node}</div>
    <div class="summary-value">{bucket['doc_count']} events</div>
  </div>""")

print("""</div>

<table>
<tr>
  <th style="width: 160px;">Timestamp</th>
  <th style="width: 100px;">Node</th>
  <th>Event Message</th>
</tr>""")

if not hits:
    print("""<tr><td colspan="3" class="no-data">No failover events found in the specified time range. Update the time range in failover_query.json and try again.</td></tr>""")
else:
    for hit in sorted(hits, key=lambda x: x['_source'].get('@timestamp', '')):
        source = hit['_source']
        timestamp = source.get('@timestamp', '')
        raw = source.get('_raw', '')
        src = source.get('source', '')
        
        node = 'unknown'
        if '/patroni1/' in src:
            node = 'patroni1'
            node_class = 'patroni1'
        elif '/patroni2/' in src:
            node = 'patroni2'
            node_class = 'patroni2'
        else:
            node_class = ''
        
        row_class = ''
        highlighted = raw
        
        # Escape HTML
        highlighted = highlighted.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        if 'promot' in raw.lower():
            row_class = 'promote'
            highlighted = highlighted.replace('received promote request', '<span class="keyword">received promote request</span>')
            highlighted = highlighted.replace('promoting', '<span class="keyword">promoting</span>')
            highlighted = highlighted.replace('promoted', '<span class="keyword">promoted</span>')
        
        if 'demot' in raw.lower() or ('lock' in raw.lower() and 'expir' in raw.lower()):
            row_class = 'demote'
            highlighted = highlighted.replace('demoting', '<span class="keyword">demoting</span>')
            highlighted = highlighted.replace('lock expired', '<span class="keyword">lock expired</span>')
            highlighted = highlighted.replace('lost leader lock', '<span class="keyword">lost leader lock</span>')
        
        if 'timeline' in raw.lower():
            if not row_class:
                row_class = 'timeline'
            highlighted = highlighted.replace('selected new timeline ID', '<span class="keyword">selected new timeline ID</span>')
        
        if 'connect' in raw.lower() and ('fail' in raw.lower() or 'could not' in raw.lower()):
            if not row_class:
                row_class = 'connection'
            highlighted = highlighted.replace('could not connect to the primary', '<span class="keyword">could not connect to the primary</span>')
            highlighted = highlighted.replace('server closed the connection', '<span class="keyword">server closed the connection</span>')
        
        if 'replication terminated' in raw:
            highlighted = highlighted.replace('replication terminated', '<span class="keyword">replication terminated</span>')
        
        if 'archive recovery complete' in raw:
            highlighted = highlighted.replace('archive recovery complete', '<span class="keyword">archive recovery complete</span>')
        
        if len(highlighted) > 800:
            highlighted = highlighted[:800] + '...'
        
        print(f"""<tr class="{row_class}">
  <td class="timestamp">{timestamp}</td>
  <td><span class="node {node_class}">{node}</span></td>
  <td class="message">{highlighted}</td>
</tr>""")

print("""</table>
<p style="margin-top: 20px; color: #7f8c8d; font-size: 12px;">
  <strong>Color Legend:</strong> 
  <span style="background: #d4edda; padding: 2px 6px; margin: 0 5px;">Promotion Events</span>
  <span style="background: #f8d7da; padding: 2px 6px; margin: 0 5px;">Demotion Events</span>
  <span style="background: #fff3cd; padding: 2px 6px; margin: 0 5px;">Connection Events</span>
  <span style="background: #d1ecf1; padding: 2px 6px; margin: 0 5px;">Timeline Events</span>
</p>
</body>
</html>""")
