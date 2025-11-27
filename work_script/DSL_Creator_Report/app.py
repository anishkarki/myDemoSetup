from flask import Flask, render_template, request, send_file, jsonify
import sys
import os
import json

# Add current directory to sys.path to import fetch_and_report
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import fetch_and_report

app = Flask(__name__)

REPORT_FILE = "generated_report.html"

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    result_type = None
    hit_count = 0
    global REPORT_FILE

    if request.method == 'POST':
        host = request.form.get('host')
        keywords_str = request.form.get('keywords')
        keywords = [k.strip() for k in keywords_str.split(',')] if keywords_str else []
        
        exclude_keywords_str = request.form.get('exclude_keywords')
        exclude_keywords = [k.strip() for k in exclude_keywords_str.split(',')] if exclude_keywords_str else []

        index_pattern = request.form.get('index')
        time_range = request.form.get('time_range')
        output_format = request.form.get('output_format')
        action = request.form.get('action')

        # Generate DSL
        dsl_query = fetch_and_report.generate_dsl(host, keywords, exclude_keywords=exclude_keywords, time_range=time_range)

        if action == 'generate_dsl':
            result = dsl_query
            result_type = 'dsl'
        
        elif action == 'fetch_logs':
            # Fetch Logs
            try:
                opensearch_url = fetch_and_report.DEFAULT_OPENSEARCH_URL
                fetch_result = fetch_and_report.fetch_logs(opensearch_url, index_pattern, dsl_query)
                hits = fetch_result.get('hits', {}).get('hits', [])
                hit_count = len(hits)
                
                # Generate Report
                if output_format == 'log':
                    REPORT_FILE = "generated_report.log"
                    fetch_and_report.create_log_report(hits, REPORT_FILE)
                else:
                    REPORT_FILE = "generated_report.html"
                    fetch_and_report.create_html_report(hits, host, keywords, REPORT_FILE)
                
                result = f"Report Generated ({output_format})"
                result_type = 'report'
            except Exception as e:
                result = {"error": str(e)}
                result_type = 'dsl' # Show error as JSON

    return render_template('index.html', result=result, result_type=result_type, hit_count=hit_count)

@app.route('/download_report')
def download_report():
    if os.path.exists(REPORT_FILE):
        return send_file(REPORT_FILE, as_attachment=True)
    return "No report found.", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
