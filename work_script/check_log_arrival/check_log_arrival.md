# Check Log Arrival Script Documentation

## Overview

The `check_log_arrival.sh` script is a robust, production-grade Bash utility designed to verify the presence of logs in an OpenSearch cluster. It ensures that logs from specific hosts or entire clusters (e.g., `patroni-az`) are successfully reaching the indexing layer.

This tool is built with a "100-year experience" philosophy, emphasizing:
- **Safety**: Strict error handling (`set -euo pipefail`) and secure secret management.
- **Portability**: Minimal dependencies (`curl`, `jq`).
- **Flexibility**: Supports CLI flags, environment variables, and cluster aliases.

---

## Prerequisites

Ensure the following tools are installed on the system where the script will run:

1.  **Bash** (v4.0+)
2.  **curl**: For making HTTP requests to OpenSearch.
3.  **jq**: For safe and reliable JSON parsing.

---

## Usage

```bash
./check_log_arrival.sh [OPTIONS] <hostname|cluster_name> [opensearch_url] [index_name]
```

### Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `hostname` / `cluster_name` | **Required**. The specific hostname (e.g., `patroni1`) or a defined cluster alias (e.g., `patroni-az`) to check. | N/A |
| `opensearch_url` | The base URL of the OpenSearch instance. | `http://100.80.115.61:19200` |
| `index_name` | The index pattern to search within. | `patronidata` |

### Options

| Flag | Long Flag | Description |
| :--- | :--- | :--- |
| `-u` | `--username` | Basic Auth Username. Overrides `OPENSEARCH_USERNAME`. |
| `-p` | `--password` | Basic Auth Password. Overrides `OPENSEARCH_PASSWORD`. |
| `-t` | `--token` | Bearer Token. Overrides `OPENSEARCH_TOKEN`. |
| | `--url` | Alternative way to specify OpenSearch URL. |
| | `--index` | Alternative way to specify Index Name. |
| `-h` | `--help` | Displays the help message. |

---

## Logic Flow & Architecture

The script follows a linear, fail-fast execution path:

### 1. Initialization & Safety
- **Strict Mode**: `set -euo pipefail` is enabled immediately.
    - `-e`: Exit immediately if a command exits with a non-zero status.
    - `-u`: Treat unset variables as an error.
    - `-o pipefail`: Return the exit status of the last command in the pipe that failed.
- **Trap**: A `cleanup` function is registered to run on `EXIT`, `INT`, or `TERM` signals to ensure clean termination.

### 2. Argument Parsing
- The script uses a `while` loop to parse command-line arguments.
- It supports both short (`-u`) and long (`--username`) flags.
- Positional arguments are handled dynamically if flags are not used.

### 3. Configuration Resolution
Configuration is resolved in the following priority order (highest to lowest):
1.  **CLI Arguments**: Flags passed directly to the script.
2.  **Environment Variables**: `OPENSEARCH_USERNAME`, `OPENSEARCH_PASSWORD`, etc.
3.  **Defaults**: Hardcoded defaults in the script.

### 4. Target Resolution (`list_hosts`)
- The script checks if the input target is a known cluster alias.
- **Example**: If `patroni-az` is passed, it expands to `patroni1`, `patroni2`, and `etcd`.
- If the target is unknown, it is treated as a single hostname.

### 5. Execution Loop
- The script iterates through every resolved host.
- For each host, it calls `check_single_host`.

### 6. The Check Logic (`check_single_host`)
This is the core function. It performs the following steps:
1.  **Query Construction**: Uses `jq` to build a safe JSON query object. This prevents JSON injection attacks and syntax errors.
    - *Query*: Searches for documents where `host.name.keyword` matches the target host.
    - *Sort*: Sorts by `@timestamp` descending.
    - *Size*: Limits to 1 result (we only need to know if *any* logs exist).
2.  **Request Execution**: Uses `curl` to send a `GET` request to `/_search`.
    - Handles Authentication (Bearer Token > Basic Auth).
    - Sets a strict timeout (10s).
3.  **Response Parsing**:
    - Uses `jq` to extract `hits.total.value` and the timestamp of the last log.
    - Validates that the response is valid JSON.
4.  **Evaluation**:
    - If `total_hits > 0`: **PASS**.
    - If `total_hits == 0`: **FAIL**.

### 7. Final Summary
- After checking all hosts, the script calculates the total number of failures.
- If `failures == 0`, it exits with code `0` (Success).
- If `failures > 0`, it exits with code `1` (Error).

---

## Examples

### 1. Simple check for a single host (uses defaults)
```bash
./check_log_arrival.sh patroni1
```

### 2. Check a defined cluster (e.g., patroni1, patroni2, etcd)
```bash
./check_log_arrival.sh patroni-az
```

### 3. Authentication with Username/Password
```bash
./check_log_arrival.sh -u admin -p mysecret patroni1
```

### 4. Authentication with Bearer Token
```bash
./check_log_arrival.sh --token "eyJhbGciOi..." patroni1
```

### 5. Custom OpenSearch URL and Index (using flags)
```bash
./check_log_arrival.sh --url "https://os.example.com:9200" --index "logs-*" patroni1
```

### 6. Custom OpenSearch URL and Index (using positional args)
```bash
./check_log_arrival.sh patroni1 "https://os.example.com:9200" "logs-*"
```

### 7. Using Environment Variables for Auth
```bash
export OPENSEARCH_USERNAME="admin"
export OPENSEARCH_PASSWORD="password"
./check_log_arrival.sh patroni-az
```

### 8. Mixed Flags and Positional Args
```bash
./check_log_arrival.sh -u admin -p pass patroni1 https://custom-url:9200
```

---

## Troubleshooting

| Error Message | Possible Cause | Solution |
| :--- | :--- | :--- |
| `Missing dependency: 'jq' is required.` | `jq` is not installed. | Install `jq` via your package manager (e.g., `apt install jq`, `brew install jq`). |
| `Failed to connect to OpenSearch` | Network issue or wrong URL. | Verify the URL and ensure the host is reachable. Check firewalls/VPN. |
| `Failed to parse JSON response` | Invalid response from server. | The server might be returning HTML (e.g., 403 Forbidden, 502 Bad Gateway). Check credentials and URL. |
| `No logs found in index 'patronidata'` | Logs are not arriving. | Check FluentBit/Fluentd on the source host. Verify the index name is correct. |

---

## Security Best Practices

- **Secret Handling**: The script avoids passing secrets as arguments to internal functions to prevent leakage in `set -x` debug traces.
- **Global Variables**: Secrets are accessed via global variables (`FINAL_USER`, `FINAL_PASS`) inside functions.
- **JSON Safety**: All JSON payloads are constructed using `jq --arg` to ensure proper escaping of user input.
