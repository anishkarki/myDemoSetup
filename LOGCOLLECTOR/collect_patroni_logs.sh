#!/bin/bash

# Patroni Log Collector for Switchover and Failover Events
# This script collects logs from both Patroni nodes and PostgreSQL during cluster events

LOGCOLLECTOR_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR"
DEMOWORK_DIR="/home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EVENT_DIR="${LOGCOLLECTOR_DIR}/event_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Patroni Cluster Log Collector ===${NC}"
echo -e "Timestamp: ${TIMESTAMP}"
echo -e "Event directory: ${EVENT_DIR}\n"

# Create event directory structure
mkdir -p "${EVENT_DIR}"/{patroni1,patroni2,cluster_state,postgres_logs}

echo -e "${YELLOW}Step 1: Collecting cluster state before event...${NC}"

# Capture current cluster state
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/cluster_state/pre_event_cluster_state.txt" 2>&1
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/cluster_state/pre_event_history.txt" 2>&1

echo -e "${GREEN}✓ Cluster state captured${NC}\n"

echo -e "${YELLOW}Step 2: Copying existing Patroni logs...${NC}"

# Copy Patroni logs from both nodes
if [ -d "${DEMOWORK_DIR}/patroni1-logs" ]; then
    cp -r "${DEMOWORK_DIR}/patroni1-logs"/* "${EVENT_DIR}/patroni1/" 2>/dev/null || true
    echo -e "${GREEN}✓ Patroni1 logs copied${NC}"
fi

if [ -d "${DEMOWORK_DIR}/patroni2-logs" ]; then
    cp -r "${DEMOWORK_DIR}/patroni2-logs"/* "${EVENT_DIR}/patroni2/" 2>/dev/null || true
    echo -e "${GREEN}✓ Patroni2 logs copied${NC}"
fi

# Copy PostgreSQL logs
if [ -d "${DEMOWORK_DIR}/postgres-logs" ]; then
    cp -r "${DEMOWORK_DIR}/postgres-logs"/* "${EVENT_DIR}/postgres_logs/" 2>/dev/null || true
    echo -e "${GREEN}✓ PostgreSQL logs copied${NC}"
fi

echo ""
echo -e "${YELLOW}Step 3: Collecting Docker container logs...${NC}"

# Collect Docker logs for Patroni containers
docker logs patroni1 > "${EVENT_DIR}/patroni1/docker_container.log" 2>&1
docker logs patroni2 > "${EVENT_DIR}/patroni2/docker_container.log" 2>&1
docker logs haproxy > "${EVENT_DIR}/cluster_state/haproxy.log" 2>&1
docker logs etcd > "${EVENT_DIR}/cluster_state/etcd.log" 2>&1

echo -e "${GREEN}✓ Docker logs collected${NC}\n"

echo -e "${YELLOW}Step 4: Collecting PostgreSQL configuration and stats...${NC}"

# Get PostgreSQL configuration from both nodes
docker exec patroni1 psql -U postgres -c "SHOW ALL;" > "${EVENT_DIR}/patroni1/postgres_config.txt" 2>&1
docker exec patroni2 psql -U postgres -c "SHOW ALL;" > "${EVENT_DIR}/patroni2/postgres_config.txt" 2>&1

# Get replication status
docker exec patroni1 psql -U postgres -c "SELECT * FROM pg_stat_replication;" > "${EVENT_DIR}/patroni1/replication_status.txt" 2>&1
docker exec patroni2 psql -U postgres -c "SELECT * FROM pg_stat_replication;" > "${EVENT_DIR}/patroni2/replication_status.txt" 2>&1

echo -e "${GREEN}✓ PostgreSQL configuration collected${NC}\n"

echo -e "${YELLOW}Step 5: Collecting Patroni configuration...${NC}"

# Copy Patroni configuration files
docker exec patroni1 cat /etc/patroni/patroni.yml > "${EVENT_DIR}/patroni1/patroni_config.yml" 2>&1
docker exec patroni2 cat /etc/patroni/patroni.yml > "${EVENT_DIR}/patroni2/patroni_config.yml" 2>&1

echo -e "${GREEN}✓ Patroni configuration collected${NC}\n"

echo -e "${GREEN}=== Pre-Event Data Collection Complete ===${NC}"
echo -e "${YELLOW}Event directory ready at: ${EVENT_DIR}${NC}\n"

echo -e "${RED}>>> You can now trigger the switchover/failover event <<<${NC}"
echo -e "Suggested commands:"
echo -e "  Switchover: ${YELLOW}docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover --master patroni2 --candidate patroni1 --force${NC}"
echo -e "  Failover:   ${YELLOW}docker stop patroni2${NC} (simulate failure)\n"

read -p "Press Enter after triggering the event to collect post-event logs..."

echo -e "\n${YELLOW}Step 6: Collecting post-event cluster state...${NC}"

# Wait a bit for cluster to stabilize
sleep 5

# Capture post-event cluster state
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list > "${EVENT_DIR}/cluster_state/post_event_cluster_state.txt" 2>&1
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history > "${EVENT_DIR}/cluster_state/post_event_history.txt" 2>&1

echo -e "${GREEN}✓ Post-event cluster state captured${NC}\n"

echo -e "${YELLOW}Step 7: Collecting post-event logs...${NC}"

# Collect updated Docker logs
docker logs patroni1 > "${EVENT_DIR}/patroni1/docker_container_post_event.log" 2>&1
docker logs patroni2 > "${EVENT_DIR}/patroni2/docker_container_post_event.log" 2>&1
docker logs haproxy > "${EVENT_DIR}/cluster_state/haproxy_post_event.log" 2>&1
docker logs etcd > "${EVENT_DIR}/cluster_state/etcd_post_event.log" 2>&1

# Copy updated Patroni logs
if [ -d "${DEMOWORK_DIR}/patroni1-logs" ]; then
    cp -r "${DEMOWORK_DIR}/patroni1-logs"/* "${EVENT_DIR}/patroni1/post_event_logs/" 2>/dev/null || true
fi

if [ -d "${DEMOWORK_DIR}/patroni2-logs" ]; then
    cp -r "${DEMOWORK_DIR}/patroni2-logs"/* "${EVENT_DIR}/patroni2/post_event_logs/" 2>/dev/null || true
fi

echo -e "${GREEN}✓ Post-event logs collected${NC}\n"

echo -e "${YELLOW}Step 8: Creating summary report...${NC}"

# Create a summary file
cat > "${EVENT_DIR}/SUMMARY.txt" << EOF
Patroni Cluster Event Log Collection Summary
============================================
Timestamp: ${TIMESTAMP}
Collection Directory: ${EVENT_DIR}

Directory Structure:
-------------------
${EVENT_DIR}/
├── patroni1/                    # Patroni1 node logs
│   ├── docker_container.log         # Container logs (pre-event)
│   ├── docker_container_post_event.log  # Container logs (post-event)
│   ├── patroni_config.yml          # Patroni configuration
│   ├── postgres_config.txt         # PostgreSQL configuration
│   ├── replication_status.txt      # Replication status
│   ├── post_event_logs/            # Log files after event
│   └── [PostgreSQL log files]      # PostgreSQL logs from patroni1
│
├── patroni2/                    # Patroni2 node logs
│   ├── docker_container.log         # Container logs (pre-event)
│   ├── docker_container_post_event.log  # Container logs (post-event)
│   ├── patroni_config.yml          # Patroni configuration
│   ├── postgres_config.txt         # PostgreSQL configuration
│   ├── replication_status.txt      # Replication status
│   ├── post_event_logs/            # Log files after event
│   └── [PostgreSQL log files]      # PostgreSQL logs from patroni2
│
├── cluster_state/               # Cluster state information
│   ├── pre_event_cluster_state.txt  # Cluster state before event
│   ├── post_event_cluster_state.txt # Cluster state after event
│   ├── pre_event_history.txt       # Cluster history before event
│   ├── post_event_history.txt      # Cluster history after event
│   ├── haproxy.log                 # HAProxy logs (pre-event)
│   ├── haproxy_post_event.log      # HAProxy logs (post-event)
│   ├── etcd.log                    # etcd logs (pre-event)
│   └── etcd_post_event.log         # etcd logs (post-event)
│
├── postgres_logs/               # PostgreSQL logs
│   └── [PostgreSQL log files]      # Logs from standalone postgres container
│
└── SUMMARY.txt                  # This summary file

Cluster State Before Event:
---------------------------
EOF

cat "${EVENT_DIR}/cluster_state/pre_event_cluster_state.txt" >> "${EVENT_DIR}/SUMMARY.txt"

cat >> "${EVENT_DIR}/SUMMARY.txt" << EOF

Cluster State After Event:
--------------------------
EOF

cat "${EVENT_DIR}/cluster_state/post_event_cluster_state.txt" >> "${EVENT_DIR}/SUMMARY.txt"

cat >> "${EVENT_DIR}/SUMMARY.txt" << EOF

Recent Cluster History:
----------------------
EOF

cat "${EVENT_DIR}/cluster_state/post_event_history.txt" >> "${EVENT_DIR}/SUMMARY.txt"

echo -e "${GREEN}✓ Summary report created${NC}\n"

echo -e "${GREEN}=== Log Collection Complete ===${NC}"
echo -e "All logs have been collected in: ${YELLOW}${EVENT_DIR}${NC}\n"
echo -e "View summary: ${YELLOW}cat ${EVENT_DIR}/SUMMARY.txt${NC}"

# Create a compressed archive
echo -e "${YELLOW}Creating compressed archive...${NC}"
cd "${LOGCOLLECTOR_DIR}"
tar -czf "event_${TIMESTAMP}.tar.gz" "event_${TIMESTAMP}/"
echo -e "${GREEN}✓ Archive created: event_${TIMESTAMP}.tar.gz${NC}\n"

echo -e "${GREEN}Done!${NC}"
