#!/bin/bash

# Automated Patroni Event Monitor and Log Collector
# Continuously monitors the cluster and automatically captures logs when events occur

LOGCOLLECTOR_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR"
DEMOWORK_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION"
MONITORING_INTERVAL=5  # Check every 5 seconds

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Patroni Cluster Event Monitor ===${NC}"
echo -e "Monitoring interval: ${MONITORING_INTERVAL} seconds"
echo -e "Log directory: ${LOGCOLLECTOR_DIR}\n"

# Initialize tracking variables
PREVIOUS_LEADER=""
PREVIOUS_STATE=""
EVENT_DETECTED=false

# Function to get current cluster state
get_cluster_state() {
    docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list 2>/dev/null
}

# Function to extract leader from cluster state
get_current_leader() {
    get_cluster_state | grep "Leader" | awk '{print $2}'
}

# Function to collect logs for an event
collect_event_logs() {
    local EVENT_TYPE=$1
    local TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    local EVENT_DIR="${LOGCOLLECTOR_DIR}/${EVENT_TYPE}_${TIMESTAMP}"
    
    echo -e "\n${RED}>>> ${EVENT_TYPE} DETECTED at ${TIMESTAMP} <<<${NC}\n"
    
    mkdir -p "${EVENT_DIR}"/{patroni1,patroni2,cluster_state,postgres_logs,monitoring}
    
    # Capture cluster state
    echo -e "${YELLOW}Capturing cluster state...${NC}"
    get_cluster_state > "${EVENT_DIR}/cluster_state/cluster_state.txt"
    docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/cluster_state/history.txt" 2>&1
    
    # Collect Docker logs
    echo -e "${YELLOW}Collecting Docker logs...${NC}"
    docker logs --tail 500 patroni1 > "${EVENT_DIR}/patroni1/docker_logs.txt" 2>&1
    docker logs --tail 500 patroni2 > "${EVENT_DIR}/patroni2/docker_logs.txt" 2>&1
    docker logs --tail 500 haproxy > "${EVENT_DIR}/cluster_state/haproxy_logs.txt" 2>&1
    docker logs --tail 500 etcd > "${EVENT_DIR}/cluster_state/etcd_logs.txt" 2>&1
    
    # Copy Patroni and PostgreSQL logs
    echo -e "${YELLOW}Copying log files...${NC}"
    cp -r "${DEMOWORK_DIR}/patroni1-logs"/* "${EVENT_DIR}/patroni1/" 2>/dev/null || true
    cp -r "${DEMOWORK_DIR}/patroni2-logs"/* "${EVENT_DIR}/patroni2/" 2>/dev/null || true
    cp -r "${DEMOWORK_DIR}/postgres-logs"/* "${EVENT_DIR}/postgres_logs/" 2>/dev/null || true
    
    # Get PostgreSQL stats
    echo -e "${YELLOW}Collecting PostgreSQL statistics...${NC}"
    docker exec patroni1 psql -U postgres -c "SELECT * FROM pg_stat_replication;" > "${EVENT_DIR}/patroni1/replication_stats.txt" 2>&1 || true
    docker exec patroni2 psql -U postgres -c "SELECT * FROM pg_stat_replication;" > "${EVENT_DIR}/patroni2/replication_stats.txt" 2>&1 || true
    
    # Create event summary
    cat > "${EVENT_DIR}/EVENT_SUMMARY.txt" << EOF
Event Type: ${EVENT_TYPE}
Timestamp: ${TIMESTAMP}
Detection Time: $(date)

Cluster State at Event Time:
-----------------------------
$(cat "${EVENT_DIR}/cluster_state/cluster_state.txt")

Recent Cluster History:
-----------------------
$(cat "${EVENT_DIR}/cluster_state/history.txt")

Event Details:
--------------
Previous Leader: ${PREVIOUS_LEADER}
Current Leader: $(get_current_leader)

Log Files Collected:
-------------------
- Patroni1 logs: ${EVENT_DIR}/patroni1/
- Patroni2 logs: ${EVENT_DIR}/patroni2/
- PostgreSQL logs: ${EVENT_DIR}/postgres_logs/
- Cluster state: ${EVENT_DIR}/cluster_state/
- HAProxy logs: ${EVENT_DIR}/cluster_state/haproxy_logs.txt
- etcd logs: ${EVENT_DIR}/cluster_state/etcd_logs.txt
EOF
    
    # Compress the event directory
    cd "${LOGCOLLECTOR_DIR}"
    tar -czf "${EVENT_TYPE}_${TIMESTAMP}.tar.gz" "${EVENT_TYPE}_${TIMESTAMP}/" 2>/dev/null
    
    echo -e "${GREEN}✓ Event logs collected and saved to: ${EVENT_DIR}${NC}"
    echo -e "${GREEN}✓ Archive created: ${EVENT_TYPE}_${TIMESTAMP}.tar.gz${NC}\n"
}

# Monitor for container failures
monitor_container_health() {
    local PATRONI1_STATUS=$(docker inspect -f '{{.State.Running}}' patroni1 2>/dev/null)
    local PATRONI2_STATUS=$(docker inspect -f '{{.State.Running}}' patroni2 2>/dev/null)
    
    if [ "$PATRONI1_STATUS" != "true" ] || [ "$PATRONI2_STATUS" != "true" ]; then
        echo -e "${RED}Container failure detected!${NC}"
        echo -e "Patroni1: $PATRONI1_STATUS | Patroni2: $PATRONI2_STATUS"
        collect_event_logs "FAILOVER_CONTAINER_FAILURE"
    fi
}

echo -e "${BLUE}Starting continuous monitoring...${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}\n"

# Main monitoring loop
while true; do
    CURRENT_LEADER=$(get_current_leader)
    CURRENT_STATE=$(get_cluster_state)
    
    # Display current status
    echo -e "${BLUE}[$(date +"%Y-%m-%d %H:%M:%S")]${NC} Current Leader: ${GREEN}${CURRENT_LEADER:-Unknown}${NC}"
    
    # Check for leader change (switchover or failover)
    if [ -n "$PREVIOUS_LEADER" ] && [ -n "$CURRENT_LEADER" ] && [ "$PREVIOUS_LEADER" != "$CURRENT_LEADER" ]; then
        collect_event_logs "LEADER_CHANGE"
        EVENT_DETECTED=true
    fi
    
    # Check for container failures
    monitor_container_health
    
    # Update previous state
    PREVIOUS_LEADER=$CURRENT_LEADER
    PREVIOUS_STATE=$CURRENT_STATE
    
    sleep $MONITORING_INTERVAL
done
