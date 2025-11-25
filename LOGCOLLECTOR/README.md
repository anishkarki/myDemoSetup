# Patroni Cluster Log Collection Suite

Complete toolkit for collecting Patroni and PostgreSQL logs during switchover and failover events.

## 📋 Overview

This directory contains scripts to monitor, trigger, and collect comprehensive logs from your Patroni cluster during various events:
- **Switchover**: Planned promotion of a replica to leader
- **Failover**: Automatic promotion when the leader fails

## 🗂️ Files

### Core Scripts

1. **`collect_patroni_logs.sh`** - Interactive log collector
   - Collects pre-event state
   - Waits for you to trigger an event
   - Collects post-event state
   - Creates comprehensive archives

2. **`monitor_and_collect.sh`** - Automated event monitor
   - Continuously monitors cluster state
   - Automatically detects and logs events
   - Captures leader changes and failures
   - Runs in the background

3. **`trigger_switchover.sh`** - Automated switchover with logging
   - Performs a clean switchover
   - Collects logs before and after
   - Creates summary reports

4. **`trigger_failover.sh`** - Simulated failover with logging
   - Simulates node failure
   - Captures automatic failover process
   - Documents recovery steps

## 🚀 Quick Start

### Check Cluster Health

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list
```

### Option 1: Automated Switchover

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./trigger_switchover.sh
```

### Option 2: Automated Failover

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./trigger_failover.sh
```

### Option 3: Interactive Collection

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./collect_patroni_logs.sh
# Follow prompts to trigger event manually
```

### Option 4: Continuous Monitoring

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./monitor_and_collect.sh
# Runs in foreground, press Ctrl+C to stop
```

## 📁 Output Structure

Each event creates a timestamped directory with:

```
event_YYYYMMDD_HHMMSS/
├── patroni1/
│   ├── docker_logs.txt              # Container logs
│   ├── patroni_config.yml           # Patroni configuration
│   ├── postgres_config.txt          # PostgreSQL settings
│   ├── replication_stats.txt        # Replication status
│   └── [PostgreSQL log files]       # All PG logs
│
├── patroni2/
│   ├── docker_logs.txt
│   ├── patroni_config.yml
│   ├── postgres_config.txt
│   ├── replication_stats.txt
│   └── [PostgreSQL log files]
│
├── cluster_state/
│   ├── pre_event_cluster_state.txt  # Before event
│   ├── post_event_cluster_state.txt # After event
│   ├── pre_event_history.txt        # History before
│   ├── post_event_history.txt       # History after
│   ├── haproxy_logs.txt             # HAProxy logs
│   └── etcd_logs.txt                # etcd logs
│
├── postgres_logs/
│   └── [PostgreSQL logs]            # Standalone postgres
│
└── SUMMARY.txt or EVENT_SUMMARY.txt # Complete summary
```

Plus a compressed archive: `event_YYYYMMDD_HHMMSS.tar.gz`

## 🔍 What Gets Collected

### Patroni Logs
- Patroni daemon logs from both nodes
- Patroni configuration files
- Cluster state and topology
- Failover/switchover history
- REST API responses

### PostgreSQL Logs
- PostgreSQL server logs from both nodes
- Replication status and statistics
- PostgreSQL configuration (SHOW ALL)
- WAL and replication lag information

### Infrastructure Logs
- HAProxy connection routing logs
- etcd consensus logs
- Docker container logs
- Network connectivity information

## 📊 Usage Examples

### Planned Switchover
```bash
# Automated with log collection
./trigger_switchover.sh

# Manual with interactive collection
./collect_patroni_logs.sh
# Then run: docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover --force
```

### Failure Simulation
```bash
# Automated failover simulation
./trigger_failover.sh

# Manual failure simulation
./collect_patroni_logs.sh
# Then run: docker stop patroni2
```

### Background Monitoring
```bash
# Start continuous monitoring
nohup ./monitor_and_collect.sh > monitor.log 2>&1 &

# Check the background process
tail -f monitor.log

# Stop monitoring
pkill -f monitor_and_collect.sh
```

## 🔧 Manual Commands

### Check Cluster Status
```bash
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list
```

### View Cluster History
```bash
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history
```

### Manual Switchover
```bash
# Switch from patroni2 to patroni1
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover \
  --master patroni2 --candidate patroni1 --force
```

### Check Replication Status
```bash
docker exec patroni1 psql -U postgres -c "SELECT * FROM pg_stat_replication;"
docker exec patroni2 psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### Recover Failed Node
```bash
# Start the stopped container
docker start patroni1  # or patroni2

# It will automatically rejoin as a replica
```

## 📝 Log Analysis Tips

### Find Switchover Events
```bash
grep -i "switched\|switchover\|promoted" event_*/patroni*/*.log
```

### Find Failover Events
```bash
grep -i "failover\|demoted\|promoted" event_*/patroni*/*.log
```

### Check Replication Lag
```bash
grep -i "lag\|replay\|receive" event_*/patroni*/*.txt
```

### View Leader Changes
```bash
cat event_*/cluster_state/*history.txt
```

## ⚠️ Important Notes

1. **Cluster Health**: Always verify cluster health before triggering events
2. **Disk Space**: Ensure sufficient space in LOGCOLLECTOR directory
3. **Timing**: Wait for cluster to stabilize between events (30-60 seconds)
4. **Recovery**: Failed nodes automatically rejoin when restarted
5. **Archives**: Compressed archives are created for easy transport

## 🎯 Cluster Health Indicators

**Healthy Cluster:**
- Both nodes show "running" state
- Replication lag is minimal (<1MB)
- Leader is clearly identified
- Timeline numbers match

**Issues to Watch:**
- Node in "starting" state
- High replication lag
- Frequent leader changes
- "unknown" LSN values

## 📞 Troubleshooting

### Script Not Executable
```bash
chmod +x *.sh
```

### Cannot Connect to Patroni
```bash
# Check containers are running
docker ps | grep patroni

# Check patroni1 logs
docker logs patroni1
```

### No Logs Collected
```bash
# Verify log directories exist
ls -la /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/patroni*-logs/
```

### Switchover Fails
```bash
# Check both nodes are healthy
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list

# Ensure replica is in sync
docker exec patroni1 psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

## 🔄 Cluster Operations

### Reset Cluster to Initial State
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION
docker-compose restart patroni1 patroni2
```

### View Real-time Logs
```bash
docker logs -f patroni1  # or patroni2
```

### Clean Old Event Logs
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
rm -rf event_* switchover_* failover_*  # Be careful!
```

---

**Last Updated**: 2025-11-25
**Cluster Location**: `/home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION`
