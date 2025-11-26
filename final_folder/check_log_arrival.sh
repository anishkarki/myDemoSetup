#!/usr/bin/env bash
#
# check_log_arrival.sh
#
# Checks for the presence of logs in OpenSearch for a specific hostname or a cluster of hosts.
# Designed for robustness, portability, and ease of use.
#
# Usage: ./check_log_arrival.sh [OPTIONS] <hostname|cluster_name> [opensearch_url] [index_name]
#

set -euo pipefail

# --- Cleanup Trap ---
cleanup() {
    # This function runs on exit. You can add temporary file removal or other cleanup here.
    # For now, we just ensure we exit cleanly.
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        # Only print if we haven't already printed a specific error message
        # (This is a generic catch-all)
        :
    fi
}
trap cleanup EXIT INT TERM

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
Usage: $(basename "${0}") [OPTIONS] <hostname|cluster_name> [opensearch_url] [index_name]

Arguments:
    hostname/cluster The hostname or cluster name (e.g., 'patroni-az') to check.
    opensearch_url   The OpenSearch URL (default: ${DEFAULT_OPENSEARCH_URL}).
    index_name       The index pattern to search (default: ${DEFAULT_INDEX}).

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
    $(basename "${0}") patroni-az
    $(basename "${0}") -u admin -p secret patroni-az
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

# Function to list hosts for a given target (cluster or single host)
list_hosts() {
    local target="$1"
    case "$target" in
        "patroni-az")
            echo "patroni1"
            echo "patroni2"
            echo "etcd"
            ;;
        *)
            echo "$target"
            ;;
    esac
}

# Function to check logs for a single host
check_single_host() {
    local host="$1"
    # We use global variables for configuration to avoid passing secrets as arguments
    # This is safer if 'set -x' is ever enabled.
    local url="$OPENSEARCH_URL"
    local index="$INDEX"
    local user="$FINAL_USER"
    local pass="$FINAL_PASS"
    local token="$FINAL_TOKEN"

    # Prepare Query
    local query
    query=$(jq -n \
        --arg host "$host" \
        '{
            size: 1,
            sort: [{ "@timestamp": { order: "desc" } }],
            query: {
                term: { "host.name.keyword": $host }
            }
        }')

    # Prepare Curl Options
    local curl_opts=(
        -s 
        -k 
        --max-time "$TIMEOUT"
        -X GET "$url/$index/_search"
        -H 'Content-Type: application/json'
    )

    if [[ -n "$token" ]]; then
        curl_opts+=(-H "Authorization: Bearer $token")
    elif [[ -n "$user" ]] && [[ -n "$pass" ]]; then
        curl_opts+=(-u "$user:$pass")
    fi

    # Execute Request
    local response
    if ! response=$(curl "${curl_opts[@]}" -d "$query"); then
        log_fail "[$host] Failed to connect to OpenSearch at $url"
        return 1
    fi

    # Parse Response
    local parsed_data
    if ! parsed_data=$(echo "$response" | jq -r '.hits.total.value // 0, .hits.hits[0]._source["@timestamp"] // "None"'); then
        log_fail "[$host] Failed to parse JSON response."
        log_warn "[$host] Raw Response: $response"
        return 1
    fi

    # Read into variables
    local total_hits last_timestamp
    { read -r total_hits; read -r last_timestamp; } <<< "$parsed_data"

    # Evaluate Results
    if [[ "$total_hits" -gt 0 ]]; then
        log_pass "[$host] Logs detected. (Count: $total_hits, Last: $last_timestamp)"
        return 0
    else
        log_fail "[$host] No logs found in index '$index'."
        return 1
    fi
}

# --- Main Execution ---

# Variables for arguments
TARGET=""
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
            if [[ -z "$TARGET" ]]; then
                TARGET="$1"
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

# Validate Target
if [[ -z "$TARGET" ]]; then
    log_fail "Hostname or Cluster Name argument is required."
    usage
fi

# Resolve Configuration (Arg > Env > Default)
OPENSEARCH_URL="${ARG_URL:-$DEFAULT_OPENSEARCH_URL}"
INDEX="${ARG_INDEX:-$DEFAULT_INDEX}"

# Resolve Auth (Arg > Env)
FINAL_USER="${ARG_USER:-${OPENSEARCH_USERNAME:-}}"
FINAL_PASS="${ARG_PASS:-${OPENSEARCH_PASSWORD:-}}"
FINAL_TOKEN="${ARG_TOKEN:-${OPENSEARCH_TOKEN:-}}"

# Check Dependencies
check_deps

# Get list of hosts to check
log_info "Resolving hosts for target '$TARGET'..."
mapfile -t HOSTS < <(list_hosts "$TARGET")

if [[ ${#HOSTS[@]} -eq 0 ]]; then
    log_fail "No hosts found for target '$TARGET'."
    exit 1
fi

log_info "Checking logs for ${#HOSTS[@]} host(s): ${HOSTS[*]}"

# Iterate and check
FAIL_COUNT=0
for HOST in "${HOSTS[@]}"; do
    if ! check_single_host "$HOST"; then
        ((FAIL_COUNT+=1))
    fi
done

# Final Summary
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo ""
    log_pass "All hosts passed log checks."
    exit 0
else
    echo ""
    log_fail "$FAIL_COUNT host(s) failed log checks."
    exit 1
fi
