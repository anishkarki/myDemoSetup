# Operational Scripts Usage Guide

This directory contains scripts for Patroni monitoring, log analysis, and reporting.

## 1. Patroni Monitor (`patroni_monitor.py`)
Fetches cluster status from Patroni API and generates HTML/Markdown reports.

**Usage:**
```bash
python3 patroni_monitor.py <hostname> <port>
```
**Example:**
```bash
python3 patroni_monitor.py 100.80.115.61 8008
```
**Output:** `reports/patroni_status.html`, `reports/patroni_status.md`

---

## 2. Email Generator (`generate_mail.py`)
Generates a formatted HTML email body for a specific action/alert.

**Usage:**
```bash
python3 generate_mail.py <hostname> <port> "<action_description>"
```
**Example:**
```bash
python3 generate_mail.py 100.80.115.61 8008 "Manual Failover Initiated"
```
**Output:** `reports/action_notice.html`, `reports/action_notice.md`

---

## 3. DSL Generator (`generate_dsl.py`)
Creates an OpenSearch DSL query JSON file for filtering logs.

**Usage:**
```bash
python3 generate_dsl.py <hostname> --start <time> --end <time> --filter "<keyword>"
```
**Example:**
```bash
python3 generate_dsl.py 100.80.115.61 --start "now-1h" --end "now" --filter "FATAL"
```
**Output:** `reports/dsl/log_query_<host>.json`

---

## 4. Run DSL (`run_dsl.py`)
Executes a JSON DSL query file against OpenSearch.

**Usage:**
```bash
python3 run_dsl.py <dsl_file_path> --port <port> --index <index>
```
**Example:**
```bash
python3 run_dsl.py reports/dsl/log_query_100.80.115.61.json --port 19200 --index patronidata
```
**Output:** `reports/results_<dsl_filename>.json`

---

## 5. Log Context Fetcher (`fetch_log_context.py`)
Finds a keyword trigger and fetches logs +/- 60 seconds around it.

**Usage:**
```bash
python3 fetch_log_context.py "<keyword>" --start <time> --end <time>
```
**Example:**
```bash
python3 fetch_log_context.py "FATAL" --start "now-24h"
```
**Output:** `reports/incidents/incident_<keyword>_<timestamp>.json`
