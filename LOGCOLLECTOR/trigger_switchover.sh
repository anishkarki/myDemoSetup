#!/bin/bash

# Trigger Patroni Switchover with Log Collection

LOGCOLLECTOR_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EVENT_DIR="${LOGCOLLECTOR_DIR}/switchover_${TIMESTAMP}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Patroni Switchover with Log Collection ===${NC}\n"

# Get current cluster state
echo -e "${YELLOW}Current cluster state:${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list

# Determine current leader and replica
CURRENT_LEADER=$(docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list | grep "Leader" | awk '{print $2}')
echo -e "\nCurrent leader: ${GREEN}${CURRENT_LEADER}${NC}"

# Create log collection directory
mkdir -p "${EVENT_DIR}"/{patroni1,patroni2,cluster_state,postgres_logs,pre_event,post_event}

# Collect pre-switchover state
echo -e "\n${YELLOW}Collecting pre-switchover logs...${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/pre_event/cluster_state.txt"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/pre_event/history.txt"
docker logs --tail 200 patroni1 > "${EVENT_DIR}/pre_event/patroni1_logs.txt" 2>&1
docker logs --tail 200 patroni2 > "${EVENT_DIR}/pre_event/patroni2_logs.txt" 2>&1

echo -e "${GREEN}✓ Pre-switchover state captured${NC}\n"

# Perform switchover
if [ "$CURRENT_LEADER" == "patroni2" ]; then
    NEW_LEADER="patroni1"
elif [ "$CURRENT_LEADER" == "patroni1" ]; then
    NEW_LEADER="patroni2"
else
    echo -e "${RED}Error: Could not determine current leader${NC}"
    exit 1
fi

echo -e "${YELLOW}Performing switchover from ${CURRENT_LEADER} to ${NEW_LEADER}...${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover --master ${CURRENT_LEADER} --candidate ${NEW_LEADER} --force

echo -e "${YELLOW}Waiting for switchover to complete...${NC}"
sleep 10

# Collect post-switchover state
echo -e "\n${YELLOW}Collecting post-switchover logs...${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/post_event/cluster_state.txt"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/post_event/history.txt"
docker logs --tail 200 patroni1 > "${EVENT_DIR}/post_event/patroni1_logs.txt" 2>&1
docker logs --tail 200 patroni2 > "${EVENT_DIR}/post_event/patroni2_logs.txt" 2>&1

# Copy all log files
echo -e "${YELLOW}Copying log files...${NC}"
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/patroni1-logs/* "${EVENT_DIR}/patroni1/" 2>/dev/null || true
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/patroni2-logs/* "${EVENT_DIR}/patroni2/" 2>/dev/null || true
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/postgres-logs/* "${EVENT_DIR}/postgres_logs/" 2>/dev/null || true

# Create summary
cat > "${EVENT_DIR}/SWITCHOVER_SUMMARY.txt" << EOF
Switchover Event Summary
========================
Timestamp: ${TIMESTAMP}
Previous Leader: ${CURRENT_LEADER}
New Leader: ${NEW_LEADER}

Pre-Switchover Cluster State:
------------------------------
$(cat "${EVENT_DIR}/pre_event/cluster_state.txt")

Post-Switchover Cluster State:
-------------------------------
$(cat "${EVENT_DIR}/post_event/cluster_state.txt")

Cluster History:
----------------
$(cat "${EVENT_DIR}/post_event/history.txt")
EOF

echo -e "${GREEN}✓ Post-switchover state captured${NC}\n"

# Create archive
cd "${LOGCOLLECTOR_DIR}"
tar -czf "switchover_${TIMESTAMP}.tar.gz" "switchover_${TIMESTAMP}/"

echo -e "${GREEN}=== Switchover Complete ===${NC}"
echo -e "Logs saved to: ${YELLOW}${EVENT_DIR}${NC}"
echo -e "Archive: ${YELLOW}switchover_${TIMESTAMP}.tar.gz${NC}\n"

echo -e "${YELLOW}Final cluster state:${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list
