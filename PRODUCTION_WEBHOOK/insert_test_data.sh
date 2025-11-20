#!/bin/bash
# Insert fresh dummy data with multiple hostnames

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

for i in {1..3}; do
  HOSTNAME="db-server-0${i}"
  
  # Division by zero error (22012)
  curl -s -X POST "http://localhost:19200/postgresdata/_doc" -H 'Content-Type: application/json' -d "{
    \"@timestamp\": \"$TIMESTAMP\",
    \"host.name\": \"$HOSTNAME\",
    \"_raw\": \"2025-01-20 10:30:0${i} UTC [12345]: [1-1] user=postgres,db=testdb,app=psql,client=127.0.0.1 e=22012,m=division by zero,s=ERROR,v=16,x=0 LOG: ERROR: division by zero\"
  }"
  
  # Numeric overflow error (22003)
  curl -s -X POST "http://localhost:19200/postgresdata/_doc" -H 'Content-Type: application/json' -d "{
    \"@timestamp\": \"$TIMESTAMP\",
    \"host.name\": \"$HOSTNAME\",
    \"_raw\": \"2025-01-20 10:30:0${i} UTC [12346]: [1-1] user=postgres,db=testdb,app=psql,client=127.0.0.1 e=22003,m=numeric field overflow,s=ERROR,v=16,x=0 LOG: ERROR: numeric field overflow\"
  }"
  
  # Unique violation (23505)
  curl -s -X POST "http://localhost:19200/postgresdata/_doc" -H 'Content-Type: application/json' -d "{
    \"@timestamp\": \"$TIMESTAMP\",
    \"host.name\": \"$HOSTNAME\",
    \"_raw\": \"2025-01-20 10:30:0${i} UTC [12347]: [1-1] user=postgres,db=testdb,app=psql,client=127.0.0.1 e=23505,m=duplicate key value violates unique constraint,s=ERROR,v=16,x=0 LOG: ERROR: duplicate key value\"
  }"
done

echo "✓ Inserted 9 test documents across 3 hostnames"
