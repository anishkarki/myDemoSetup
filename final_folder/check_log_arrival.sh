#!/usr/bin/env bash
#
# check_log_arrival.sh
#
# Checks for the presence of logs in OpenSearch for a specific hostname.
# Designed for robustness, portability, and ease of use.
#
# Usage: ./check_log_arrival.sh <hostname> [opensearch_url] [index_name]
#

set -euo pipefail

# --- Configuration ---
DEFAULT_OPENSEARCH_URL="http://100.80.115.61:19200"
DEFAULT_INDEX="patronidata"
TIMEOUT=10

# --- Colors ---
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

# --- Functions ---

usage() {
    cat <<USAGE_EOF
Usage: $(basename "${0}") [OPTIONS] <hostname> [opensearch_url] [index_name]

Arguments:
    hostname        The hostname to search for in logs (required).
    opensearch_url  The OpenSearch URL (default: ${DEFAULT_OPENSEARCH_URL}).
    index_name      The index pattern to search (default: ${DEFAULT_INDEX}).

Options:
    -u, --username <user>   Basic Auth Username (overrides OPENSEARCH_USERNAME)
    -p, --password <pass>   Basic Auth Password (overrides OPENSEARCH_PASSWORD)
    -t, --token <token>     Bearer Token (overrides OPENSEARCH_TOKEN)
    --url <url>             OpenSearch URL (alternative to positional arg)
    --index <index>         Index Name (alternative to positional arg)
    -h, --help              Show this help message

Environment Variables:
    OPENSEARCH_USERNAME  Basic Auth Username
    OPENSEARCH_PASSWORD  Basic Auth Password
    OPENSEARCH_TOKEN     Bearer Token

Example:
    $(basename "${0}") patroni1
    $(basename "${0}") -u admin -p secret patroni1
    $(basename "${0}") --token "eyJ..." patroni1 https://opensearch.local:9200
USAGE_EOF
    exit 1
}

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

check_deps() {
    local deps=("curl" "jq")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_fail "Missing dependency: '$cmd' is required."
            exit 1
        fi
    done
}

# --- Main Execution ---

# Variables for arguments
HOSTNAME=""
ARG_URL=""
ARG_INDEX=""
ARG_USER=""
ARG_PASS=""
ARG_TOKEN=""

# Parse Arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--username)
            if [[ -n "${2:-}" ]]; then ARG_USER="$2"; shift 2; else log_fail "Missing value for $1"; exit 1; fi
            ;;
        -p|--password)
            if [[ -n "${2:-}" ]]; then ARG_PASS="$2"; shift 2; else log_fail "Missing value for $1"; exit 1; fi
            ;;
        -t|--token)
            if [[ -n "${2:-}" ]]; then ARG_TOKEN="$2"; shift 2; else log_fail "Missing value for $1"; exit 1; fi
            ;;
        --url)
            if [[ -n "${2:-}" ]]; then ARG_URL="$2"; shift 2; else log_fail "Missing value for $1"; exit 1; fi
            ;;
        --index)
            if [[ -n "${2:-}" ]]; then ARG_INDEX="$2"; shift 2; else log_fail "Missing value for $1"; exit 1; fi
            ;;
        -h|--help)
            usage
            ;;
        -*)
            log_fail "Unknown option: $1"
            usage
            ;;
        *)
            # Positional arguments handling
            if [[ -z "$HOSTNAME" ]]; then
                HOSTNAME="$1"
            elif [[ -z "$ARG_URL" ]]; then
                ARG_URL="$1"
            elif [[ -z "$ARG_INDEX" ]]; then
                ARG_INDEX="$1"
            else
                log_fail "Unexpected argument: $1"
                usage
            fi
            shift
            ;;
    esac
done

# Validate Hostname
if [[ -z "$HOSTNAME" ]]; then
    log_fail "Hostname argument is required."
    usage
fi

# Resolve Configuration (Arg > Env > Default)
OPENSEARCH_URL="${ARG_URL:-$DEFAULT_OPENSEARCH_URL}"
INDEX="${ARG_INDEX:-$DEFAULT_INDEX}"

# Resolve Auth (Arg > Env)
FINAL_USER="${ARG_USER:-${OPENSEARCH_USERNAME:-}}"
FINAL_PASS="${ARG_PASS:-${OPENSEARCH_PASSWORD:-}}"
FINAL_TOKEN="${ARG_TOKEN:-${OPENSEARCH_TOKEN:-}}"

# 2. Check Dependencies
check_deps

# 3. Prepare Query
# Using jq to safely construct JSON prevents injection issues and syntax errors
QUERY=$(jq -n \
    --arg host "$HOSTNAME" \
    '{
        size: 1,
        sort: [{ "@timestamp": { order: "desc" } }],
        query: {
            term: { "host.name.keyword": $host }
        }
    }')

# 4. Prepare Curl Options
CURL_OPTS=(
    -s 
    -k 
    --max-time "$TIMEOUT"
    -X GET "$OPENSEARCH_URL/$INDEX/_search"
    -H 'Content-Type: application/json'
)

if [[ -n "$FINAL_TOKEN" ]]; then
    CURL_OPTS+=(-H "Authorization: Bearer $FINAL_TOKEN")
elif [[ -n "$FINAL_USER" ]] && [[ -n "$FINAL_PASS" ]]; then
    CURL_OPTS+=(-u "$FINAL_USER:$FINAL_PASS")
fi

# 5. Execute Request
log_info "Querying $OPENSEARCH_URL/$INDEX for host '$HOSTNAME'..."

if ! RESPONSE=$(curl "${CURL_OPTS[@]}" -d "$QUERY"); then
    log_fail "Failed to connect to OpenSearch at $OPENSEARCH_URL"
    exit 1
fi

# 6. Parse Response
# We capture exit code of jq to check for parsing errors
if ! PARSED_DATA=$(echo "$RESPONSE" | jq -r '.hits.total.value // 0, .hits.hits[0]._source["@timestamp"] // "None"'); then
    log_fail "Failed to parse JSON response."
    log_warn "Raw Response: $RESPONSE"
    exit 1
fi

# Read into variables (newline separated from jq output)
{ read -r TOTAL_HITS; read -r LAST_TIMESTAMP; } <<< "$PARSED_DATA"

# 7. Evaluate Results
if [[ "$TOTAL_HITS" -gt 0 ]]; then
    log_pass "Logs detected."
    echo -e "       Details: Found ${GREEN}${TOTAL_HITS}${NC} logs. Last received at ${YELLOW}${LAST_TIMESTAMP}${NC}."
else
    log_fail "No logs found."
    echo -e "       Details: Host '$HOSTNAME' has 0 documents in index '$INDEX'."
    exit 1
fi
