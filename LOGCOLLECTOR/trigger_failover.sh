#!/bin/bash

# Trigger Patroni Failover by Stopping Leader with Log Collection

LOGCOLLECTOR_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EVENT_DIR="${LOGCOLLECTOR_DIR}/failover_${TIMESTAMP}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Patroni Failover Simulation with Log Collection ===${NC}\n"

# Get current cluster state
echo -e "${YELLOW}Current cluster state:${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list

# Determine current leader
CURRENT_LEADER=$(docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list | grep "Leader" | awk '{print $2}')
echo -e "\nCurrent leader: ${GREEN}${CURRENT_LEADER}${NC}"

if [ -z "$CURRENT_LEADER" ]; then
    echo -e "${RED}Error: Could not determine current leader${NC}"
    exit 1
fi

# Create log collection directory
mkdir -p "${EVENT_DIR}"/{patroni1,patroni2,cluster_state,postgres_logs,pre_event,post_event}

# Collect pre-failover state
echo -e "\n${YELLOW}Collecting pre-failover logs...${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/pre_event/cluster_state.txt"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/pre_event/history.txt"
docker logs --tail 200 patroni1 > "${EVENT_DIR}/pre_event/patroni1_logs.txt" 2>&1
docker logs --tail 200 patroni2 > "${EVENT_DIR}/pre_event/patroni2_logs.txt" 2>&1
docker logs --tail 100 haproxy > "${EVENT_DIR}/pre_event/haproxy_logs.txt" 2>&1
docker logs --tail 100 etcd > "${EVENT_DIR}/pre_event/etcd_logs.txt" 2>&1

echo -e "${GREEN}✓ Pre-failover state captured${NC}\n"

# Simulate failure by stopping the leader
echo -e "${RED}Simulating failure by stopping ${CURRENT_LEADER}...${NC}"
docker stop ${CURRENT_LEADER}

echo -e "${YELLOW}Waiting for automatic failover (30 seconds)...${NC}"
for i in {30..1}; do
    echo -ne "\rWaiting... $i seconds remaining "
    sleep 1
done
echo -e "\n"

# Collect post-failover state
echo -e "${YELLOW}Collecting post-failover logs...${NC}"

# Use the running node to check cluster state
if [ "$CURRENT_LEADER" == "patroni1" ]; then
    RUNNING_NODE="patroni2"
else
    RUNNING_NODE="patroni1"
fi

docker exec ${RUNNING_NODE} patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/post_event/cluster_state.txt" 2>&1
docker exec ${RUNNING_NODE} patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/post_event/history.txt" 2>&1

docker logs --tail 200 patroni1 > "${EVENT_DIR}/post_event/patroni1_logs.txt" 2>&1 || true
docker logs --tail 200 patroni2 > "${EVENT_DIR}/post_event/patroni2_logs.txt" 2>&1 || true
docker logs --tail 100 haproxy > "${EVENT_DIR}/post_event/haproxy_logs.txt" 2>&1
docker logs --tail 100 etcd > "${EVENT_DIR}/post_event/etcd_logs.txt" 2>&1

# Copy all log files
echo -e "${YELLOW}Copying log files...${NC}"
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/patroni1-logs/* "${EVENT_DIR}/patroni1/" 2>/dev/null || true
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/patroni2-logs/* "${EVENT_DIR}/patroni2/" 2>/dev/null || true
cp -r /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/postgres-logs/* "${EVENT_DIR}/postgres_logs/" 2>/dev/null || true

# Get new leader
NEW_LEADER=$(docker exec ${RUNNING_NODE} patronictl -c /etc/patroni/patroni.yml list 2>/dev/null | grep "Leader" | awk '{print $2}')

# Create summary
cat > "${EVENT_DIR}/FAILOVER_SUMMARY.txt" << EOF
Failover Event Summary
======================
Timestamp: ${TIMESTAMP}
Failed Node: ${CURRENT_LEADER}
New Leader: ${NEW_LEADER}

Pre-Failover Cluster State:
----------------------------
$(cat "${EVENT_DIR}/pre_event/cluster_state.txt")

Post-Failover Cluster State:
-----------------------------
$(cat "${EVENT_DIR}/post_event/cluster_state.txt")

Cluster History:
----------------
$(cat "${EVENT_DIR}/post_event/history.txt")

Recovery Instructions:
---------------------
To bring back the failed node:
    docker start ${CURRENT_LEADER}

The node will automatically rejoin as a replica.
EOF

echo -e "${GREEN}✓ Post-failover state captured${NC}\n"

# Create archive
cd "${LOGCOLLECTOR_DIR}"
tar -czf "failover_${TIMESTAMP}.tar.gz" "failover_${TIMESTAMP}/"

echo -e "${GREEN}=== Failover Simulation Complete ===${NC}"
echo -e "Logs saved to: ${YELLOW}${EVENT_DIR}${NC}"
echo -e "Archive: ${YELLOW}failover_${TIMESTAMP}.tar.gz${NC}\n"

echo -e "${YELLOW}Final cluster state:${NC}"
docker exec ${RUNNING_NODE} patronictl -c /etc/patroni/patroni.yml list 2>/dev/null

echo -e "\n${RED}Note: ${CURRENT_LEADER} is currently stopped${NC}"
echo -e "To recover: ${YELLOW}docker start ${CURRENT_LEADER}${NC}\n"
