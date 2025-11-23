#!/bin/bash
set -e

# Start SSH server
service ssh start

# Run the official postgres entrypoint
exec /usr/local/bin/docker-entrypoint.sh "$@"