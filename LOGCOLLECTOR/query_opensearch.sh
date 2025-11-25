#!/bin/bash

# OpenSearch Query Script for Patroni Failover/Switchover Logs
# This script executes DSL queries against OpenSearch to fetch event logs

OPENSEARCH_HOST="${OPENSEARCH_HOST:-localhost}"
OPENSEARCH_PORT="${OPENSEARCH_PORT:-19200}"
OPENSEARCH_URL="http://${OPENSEARCH_HOST}:${OPENSEARCH_PORT}"
INDEX_PATTERN="${INDEX_PATTERN:-patroni-logs-*,postgres-logs-*,logs-*}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}=== OpenSearch Patroni Log Query Tool ===${NC}\n"

# Function to execute query
execute_query() {
    local query_file=$1
    local output_file=$2
    local description=$3
    
    echo -e "${YELLOW}Executing: ${description}${NC}"
    echo -e "Query file: ${query_file}"
    echo -e "Index pattern: ${INDEX_PATTERN}"
    echo -e "OpenSearch: ${OPENSEARCH_URL}\n"
    
    if [ ! -f "$query_file" ]; then
        echo -e "${RED}Error: Query file not found: ${query_file}${NC}\n"
        return 1
    fi
    
    # Execute the query
    curl -s -X GET "${OPENSEARCH_URL}/${INDEX_PATTERN}/_search" \
        -H 'Content-Type: application/json' \
        -d @"${query_file}" \
        -o "${output_file}"
    
    if [ $? -eq 0 ]; then
        # Check if we got results
        local hit_count=$(jq -r '.hits.total.value // 0' "${output_file}" 2>/dev/null)
        if [ -n "$hit_count" ] && [ "$hit_count" -gt 0 ]; then
            echo -e "${GREEN}✓ Query successful! Found ${hit_count} matching logs${NC}"
            echo -e "Results saved to: ${output_file}\n"
            
            # Display sample results
            echo -e "${YELLOW}Sample results (first 3):${NC}"
            jq -r '.hits.hits[0:3] | .[] | "[\(._source["@timestamp"] // "N/A")] [\(._source.source // "unknown")] \(._source.message // ._source.log // "No message")"' "${output_file}" 2>/dev/null || echo "Unable to parse results"
            echo ""
        else
            echo -e "${YELLOW}⚠ Query successful but no results found${NC}\n"
        fi
        return 0
    else
        echo -e "${RED}✗ Query failed${NC}\n"
        return 1
    fi
}

# Function to display formatted results
display_results() {
    local results_file=$1
    
    if [ ! -f "$results_file" ]; then
        echo -e "${RED}Results file not found: ${results_file}${NC}"
        return 1
    fi
    
    echo -e "${BLUE}=== Formatted Results ===${NC}\n"
    
    jq -r '.hits.hits[] | 
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" +
        "Timestamp: \(._source["@timestamp"] // "N/A")\n" +
        "Source: \(._source.source // ._source.container_name // "unknown")\n" +
        "Level: \(._source.level // ._source.severity // "N/A")\n" +
        "Message: \(._source.message // ._source.log // "No message")\n"
    ' "$results_file" 2>/dev/null
}

# Main menu
echo -e "${YELLOW}Select query type:${NC}"
echo "1. Failover logs only"
echo "2. Switchover logs only"
echo "3. All failover/switchover events (comprehensive)"
echo "4. Custom time range (all events)"
echo "5. Display formatted results from existing file"
echo ""
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        OUTPUT_FILE="${SCRIPT_DIR}/results_failover_${TIMESTAMP}.json"
        execute_query "${SCRIPT_DIR}/opensearch_failover_query.json" "${OUTPUT_FILE}" "Failover logs query"
        
        read -p "Display formatted results? [y/N]: " display
        if [[ "$display" =~ ^[Yy]$ ]]; then
            display_results "${OUTPUT_FILE}"
        fi
        ;;
    
    2)
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        OUTPUT_FILE="${SCRIPT_DIR}/results_switchover_${TIMESTAMP}.json"
        execute_query "${SCRIPT_DIR}/opensearch_switchover_query.json" "${OUTPUT_FILE}" "Switchover logs query"
        
        read -p "Display formatted results? [y/N]: " display
        if [[ "$display" =~ ^[Yy]$ ]]; then
            display_results "${OUTPUT_FILE}"
        fi
        ;;
    
    3)
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        OUTPUT_FILE="${SCRIPT_DIR}/results_all_events_${TIMESTAMP}.json"
        execute_query "${SCRIPT_DIR}/opensearch_all_events_query.json" "${OUTPUT_FILE}" "All failover/switchover events query"
        
        read -p "Display formatted results? [y/N]: " display
        if [[ "$display" =~ ^[Yy]$ ]]; then
            display_results "${OUTPUT_FILE}"
        fi
        ;;
    
    4)
        echo -e "\n${YELLOW}Enter time range:${NC}"
        read -p "From (e.g., 2025-11-25T00:00:00): " time_from
        read -p "To (e.g., 2025-11-25T23:59:59): " time_to
        
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        TEMP_QUERY="${SCRIPT_DIR}/temp_query_${TIMESTAMP}.json"
        OUTPUT_FILE="${SCRIPT_DIR}/results_timerange_${TIMESTAMP}.json"
        
        # Create temporary query with time range
        jq --arg from "$time_from" --arg to "$time_to" \
            '.query.bool.filter += [{"range": {"@timestamp": {"gte": $from, "lte": $to}}}]' \
            "${SCRIPT_DIR}/opensearch_all_events_query.json" > "${TEMP_QUERY}"
        
        execute_query "${TEMP_QUERY}" "${OUTPUT_FILE}" "Time-ranged events query"
        rm -f "${TEMP_QUERY}"
        
        read -p "Display formatted results? [y/N]: " display
        if [[ "$display" =~ ^[Yy]$ ]]; then
            display_results "${OUTPUT_FILE}"
        fi
        ;;
    
    5)
        echo -e "\n${YELLOW}Available result files:${NC}"
        ls -1t "${SCRIPT_DIR}"/results_*.json 2>/dev/null | head -10
        echo ""
        read -p "Enter file path: " result_file
        display_results "$result_file"
        ;;
    
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${BLUE}=== Query Complete ===${NC}"
echo -e "OpenSearch URL: ${OPENSEARCH_URL}"
echo -e "Index pattern: ${INDEX_PATTERN}"
echo ""

# Show aggregations if available
if [ -f "${OUTPUT_FILE}" ]; then
    echo -e "${YELLOW}Event statistics:${NC}"
    jq -r '
        if .aggregations then
            "Events by source:\n" +
            (.aggregations.events_by_source.buckets // [] | map("  \(.key): \(.doc_count)") | join("\n")) +
            "\n\nEvents by severity:\n" +
            (.aggregations.events_by_severity.buckets // [] | map("  \(.key): \(.doc_count)") | join("\n"))
        else
            "No aggregations available"
        end
    ' "${OUTPUT_FILE}" 2>/dev/null
fi

echo -e "\n${GREEN}Tip: Use jq to parse results:${NC}"
echo -e "  jq '.hits.hits[]._source' ${OUTPUT_FILE}"
echo -e "  jq -r '.hits.hits[]._source | \"[\(.\"@timestamp\")] \(.message)\"' ${OUTPUT_FILE}"
