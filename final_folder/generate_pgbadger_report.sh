#!/usr/bin/env bash
#
# generate_pgbadger_report.sh
#
# Automates the installation of pgBadger and generation of reports from PostgreSQL logs.
# Supports local files/directories and Docker containers.
#
# Usage: 
#   ./generate_pgbadger_report.sh [options] <input> [output_html]
#
# Options:
#   -d, --docker    Treat input as a Docker container name
#   -h, --help      Show help
#

set -euo pipefail

# --- Configuration ---
PGBADGER_VERSION="12.4"
INSTALL_DIR="$HOME/pgbadger_tools"
PGBADGER_BIN="$INSTALL_DIR/pgbadger-$PGBADGER_VERSION/pgbadger"
DOWNLOAD_URL="https://github.com/darold/pgbadger/archive/refs/tags/v${PGBADGER_VERSION}.tar.gz"
TEMP_DIR="/tmp/pgbadger_work_$$"

# --- Colors ---
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN='' BLUE='' RED='' NC=''
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

cleanup() {
    if [[ -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# --- Functions ---

check_dependencies() {
    local deps=("perl" "curl" "tar")
    for cmd in "${deps[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is required but not installed."
            exit 1
        fi
    done
}

install_pgbadger() {
    if [[ -x "$PGBADGER_BIN" ]]; then
        return
    fi

    log_info "Installing pgBadger v${PGBADGER_VERSION}..."
    mkdir -p "$INSTALL_DIR"
    
    local tarball="$INSTALL_DIR/pgbadger.tar.gz"
    curl -L -s -o "$tarball" "$DOWNLOAD_URL"
    tar -xzf "$tarball" -C "$INSTALL_DIR"
    chmod +x "$PGBADGER_BIN"
    rm "$tarball"
    
    log_success "pgBadger installed."
}

fetch_docker_logs() {
    local container="$1"
    local dest_dir="$2"
    
    log_info "Fetching logs from container '$container'..."
    
    # Check if container exists
    if ! docker ps -q -f name="$container" | grep -q .; then
        log_error "Container '$container' not found or not running."
        exit 1
    fi
    
    # List logs in /var/log/postgresql
    # We use 'docker exec' to list files, then 'docker cp' to copy them.
    # We filter for postgresql-*.log to avoid patroni.log if needed, or take all.
    
    mkdir -p "$dest_dir"
    
    # Copy the whole directory (easiest way)
    if ! docker cp "$container:/var/log/postgresql/." "$dest_dir/"; then
        log_error "Failed to copy logs from $container:/var/log/postgresql/"
        exit 1
    fi
    
    log_success "Logs copied from Docker."
}

run_analysis() {
    local input="$1"
    local output="$2"
    local is_docker="${3:-false}"
    
    local target_files=()
    
    if [[ "$is_docker" == "true" ]]; then
        mkdir -p "$TEMP_DIR"
        fetch_docker_logs "$input" "$TEMP_DIR"
        # Find all log files in temp dir
        while IFS= read -r file; do
            target_files+=("$file")
        done < <(find "$TEMP_DIR" -name "postgresql-*.log" -type f)
        
        if [[ ${#target_files[@]} -eq 0 ]]; then
            log_error "No postgresql-*.log files found in container '$input'."
            exit 1
        fi
    elif [[ -d "$input" ]]; then
        # Directory input
        while IFS= read -r file; do
            target_files+=("$file")
        done < <(find "$input" -name "postgresql-*.log" -type f)
        
        if [[ ${#target_files[@]} -eq 0 ]]; then
            log_error "No postgresql-*.log files found in directory '$input'."
            exit 1
        fi
    elif [[ -f "$input" ]]; then
        target_files+=("$input")
    else
        log_error "Input '$input' not found."
        exit 1
    fi

    log_info "Analyzing ${#target_files[@]} log file(s)..."
    log_info "Output: $output"

    # Run pgbadger
    # -j 4: Parallel jobs
    # -p stderr: Standard Postgres log prefix usually works with stderr format
    # If parsing fails, we might need to adjust -p based on log_line_prefix in postgres.conf
    
    "$PGBADGER_BIN" -j 4 -o "$output" "${target_files[@]}"
    
    if [[ $? -eq 0 ]]; then
        log_success "Report generated successfully: $output"
    else
        log_error "pgBadger failed."
        exit 1
    fi
}

usage() {
    echo "Usage: $0 [options] <input> [output_html]"
    echo ""
    echo "Arguments:"
    echo "  input           Log file, directory, or container name"
    echo "  output_html     Output file path (default: pgbadger_report.html)"
    echo ""
    echo "Options:"
    echo "  -d, --docker    Input is a Docker container name"
    echo "  -h, --help      Show this help"
    exit 1
}

# --- Main ---

check_dependencies
install_pgbadger

IS_DOCKER=false
INPUT=""
OUTPUT="pgbadger_report.html"

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--docker)
            IS_DOCKER=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            ;;
        *)
            if [[ -z "$INPUT" ]]; then
                INPUT="$1"
            elif [[ "$OUTPUT" == "pgbadger_report.html" ]]; then
                # Only override output if it hasn't been set (or is default)
                # Actually, simple logic: 2nd positional is output
                OUTPUT="$1"
            fi
            shift
            ;;
    esac
done

if [[ -z "$INPUT" ]]; then
    usage
fi

run_analysis "$INPUT" "$OUTPUT" "$IS_DOCKER"
