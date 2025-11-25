#!/bin/bash

# Quick Patroni Cluster Health Check

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Patroni Cluster Health Check ===${NC}\n"

# Check if containers are running
echo -e "${YELLOW}Container Status:${NC}"
for container in patroni1 patroni2 etcd haproxy; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "  ${GREEN}✓${NC} ${container} - Running"
    else
        echo -e "  ${RED}✗${NC} ${container} - Not Running"
    fi
done
echo ""

# Check cluster state
echo -e "${YELLOW}Cluster State:${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list 2>/dev/null || \
docker exec patroni2 patronictl -c /etc/patroni/patroni.yml list 2>/dev/null
echo ""

# Check cluster history
echo -e "${YELLOW}Recent Cluster History:${NC}"
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history 2>/dev/null | tail -10 || \
docker exec patroni2 patronictl -c /etc/patroni/patroni.yml history 2>/dev/null | tail -10
echo ""

# Check replication from leader
LEADER=$(docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list 2>/dev/null | grep "Leader" | awk '{print $2}' || \
         docker exec patroni2 patronictl -c /etc/patroni/patroni.yml list 2>/dev/null | grep "Leader" | awk '{print $2}')

if [ -n "$LEADER" ]; then
    echo -e "${YELLOW}Replication Status from Leader (${LEADER}):${NC}"
    docker exec ${LEADER} psql -U postgres -c "SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;" 2>/dev/null
    echo ""
fi

# Health summary
echo -e "${BLUE}=== Health Summary ===${NC}"

PATRONI1_RUNNING=$(docker ps --format '{{.Names}}' | grep -c "^patroni1$" || echo "0")
PATRONI2_RUNNING=$(docker ps --format '{{.Names}}' | grep -c "^patroni2$" || echo "0")

if [ "$PATRONI1_RUNNING" -eq 1 ] && [ "$PATRONI2_RUNNING" -eq 1 ] && [ -n "$LEADER" ]; then
    echo -e "${GREEN}✓ Cluster is operational${NC}"
    echo -e "  Leader: ${GREEN}${LEADER}${NC}"
elif [ -n "$LEADER" ]; then
    echo -e "${YELLOW}⚠ Cluster is partially operational${NC}"
    echo -e "  Leader: ${GREEN}${LEADER}${NC}"
    echo -e "  ${YELLOW}Some nodes may be starting or recovering${NC}"
else
    echo -e "${RED}✗ Cluster has issues - no clear leader${NC}"
fi
echo ""

echo -e "${BLUE}Cluster ready for log collection tests!${NC}"
