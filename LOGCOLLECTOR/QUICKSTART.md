# Patroni Log Collection - Quick Start Guide

## ✅ Current Cluster Status

**Cluster Health**: ✓ Operational
- **Leader**: patroni2 (running)
- **Replica**: patroni1 (starting - will sync automatically)
- **Timeline**: 6

## 🎯 Ready-to-Use Scripts

All scripts are located in: `/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR/`

### 1. Check Cluster Health (Run First!)

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./check_health.sh
```

### 2. Automated Switchover with Log Collection

**Best for planned leadership changes**

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./trigger_switchover.sh
```

**What it does:**
- ✓ Captures pre-switchover state
- ✓ Performs clean switchover (patroni2 → patroni1 or vice versa)
- ✓ Captures post-switchover state
- ✓ Collects all Patroni & PostgreSQL logs
- ✓ Creates compressed archive

**Output**: `switchover_YYYYMMDD_HHMMSS.tar.gz`

### 3. Automated Failover with Log Collection

**Best for testing failure scenarios**

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./trigger_failover.sh
```

**What it does:**
- ✓ Captures pre-failover state
- ✓ Stops current leader (simulates crash)
- ✓ Monitors automatic failover
- ✓ Captures post-failover state
- ✓ Collects all Patroni & PostgreSQL logs
- ✓ Creates compressed archive
- ✓ Provides recovery instructions

**Output**: `failover_YYYYMMDD_HHMMSS.tar.gz`

**To recover after failover:**
```bash
docker start patroni2  # or patroni1, depending on which failed
```

### 4. Interactive Log Collection

**Best when you want manual control**

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./collect_patroni_logs.sh
```

**Workflow:**
1. Script collects pre-event state
2. You manually trigger event (switchover/failover)
3. Press Enter to collect post-event logs
4. Script creates archive

**Manual switchover command:**
```bash
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover \
  --master patroni2 --candidate patroni1 --force
```

### 5. Continuous Monitoring

**Best for catching unexpected events**

```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
./monitor_and_collect.sh
```

**What it does:**
- ✓ Monitors cluster every 5 seconds
- ✓ Automatically detects leader changes
- ✓ Automatically detects container failures
- ✓ Captures logs when events occur
- ✓ Creates timestamped archives

**Run in background:**
```bash
nohup ./monitor_and_collect.sh > monitor.log 2>&1 &
```

**Stop monitoring:**
```bash
pkill -f monitor_and_collect.sh
```

## 📁 Log Collection Details

### What Gets Collected

#### Patroni Logs (from both nodes)
- Docker container logs
- Patroni daemon logs
- Patroni configuration (patroni.yml)
- Cluster state snapshots
- Failover/switchover history

#### PostgreSQL Logs (from both nodes)
- PostgreSQL server logs
- Replication statistics
- PostgreSQL configuration (SHOW ALL)
- WAL position and lag info

#### Infrastructure Logs
- HAProxy routing logs
- etcd consensus logs
- Container health status

### Output Structure

Each event creates:
```
LOGCOLLECTOR/
├── event_YYYYMMDD_HHMMSS/          # Event directory
│   ├── patroni1/                    # All patroni1 logs
│   ├── patroni2/                    # All patroni2 logs
│   ├── cluster_state/               # Cluster metadata
│   ├── postgres_logs/               # PostgreSQL logs
│   └── SUMMARY.txt                  # Complete summary
│
└── event_YYYYMMDD_HHMMSS.tar.gz    # Compressed archive
```

## 🔍 Quick Commands Reference

### View Cluster Status
```bash
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml list
```

### View Cluster History
```bash
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml history
```

### Check Replication
```bash
docker exec patroni2 psql -U postgres -c "SELECT * FROM pg_stat_replication;"
```

### View Live Logs
```bash
docker logs -f patroni1  # Follow patroni1 logs
docker logs -f patroni2  # Follow patroni2 logs
```

### Manual Switchover
```bash
# Switch from current leader to the other node
docker exec patroni1 patronictl -c /etc/patroni/patroni.yml switchover --force
```

### Manual Failover (Simulate Failure)
```bash
# Stop the current leader
docker stop patroni2  # or patroni1

# Recover
docker start patroni2  # or patroni1
```

## 📊 Example Workflows

### Scenario 1: Test Planned Maintenance
```bash
# 1. Check health
./check_health.sh

# 2. Run automated switchover
./trigger_switchover.sh

# 3. Review logs
ls -lh switchover_*.tar.gz
tar -tzf switchover_*.tar.gz | head -20
```

### Scenario 2: Test Failure Recovery
```bash
# 1. Start continuous monitoring
nohup ./monitor_and_collect.sh > monitor.log 2>&1 &

# 2. Trigger failure
./trigger_failover.sh

# 3. Review captured logs
ls -lh failover_*.tar.gz

# 4. Stop monitoring
pkill -f monitor_and_collect.sh
```

### Scenario 3: Multiple Events Testing
```bash
# Start monitoring in background
nohup ./monitor_and_collect.sh > monitor.log 2>&1 &

# Trigger multiple switchovers
./trigger_switchover.sh
sleep 60
./trigger_switchover.sh
sleep 60
./trigger_switchover.sh

# Review all captured events
ls -lh *_*.tar.gz
```

## 🎓 Log Analysis Tips

### Find All Switchover Events
```bash
grep -i "switched\|switchover\|promoted" */patroni*/*.log
```

### Check Replication Lag During Events
```bash
grep -i "lag\|replay\|receive" */cluster_state/*.txt
```

### View Leader Changes Timeline
```bash
cat */cluster_state/*history.txt | sort -u
```

### Extract Key Patroni Events
```bash
grep -E "promoted|demoted|starting|stopping|replication" */patroni*/*.log
```

## ⚠️ Important Notes

1. **Cluster must be healthy** before triggering events
2. **Wait 30-60 seconds** between consecutive events
3. **Disk space**: Each event capture uses ~10-50MB
4. **Recovery is automatic**: Failed nodes rejoin when restarted
5. **Archives are compressed**: Use `tar -xzf` to extract

## 🚨 Troubleshooting

### Cluster Not Responding
```bash
# Restart both nodes
cd /home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION
docker-compose restart patroni1 patroni2
```

### Script Permissions
```bash
chmod +x /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR/*.sh
```

### Clean Up Old Logs
```bash
cd /home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR
# List old events
ls -lh

# Remove old events (careful!)
rm -rf event_* switchover_* failover_*
```

## 📝 Next Steps

1. ✅ Run `./check_health.sh` to verify cluster health
2. ✅ Try `./trigger_switchover.sh` for your first test
3. ✅ Review the generated logs and summary
4. ✅ Try `./trigger_failover.sh` to test failure scenarios
5. ✅ Set up continuous monitoring for production-like testing

---

**Location**: `/home/swordfish/EveryThing0and1/myDemoSetup/LOGCOLLECTOR/`
**Cluster**: `/home/swordfish/EveryThing0and1/myDemoSetup/DEMOWORKSIMULATION/`
**Current Leader**: patroni2
**Cluster Timeline**: 6
