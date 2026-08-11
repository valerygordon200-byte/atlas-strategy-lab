#!/bin/bash
# Secret comes from relay_config.txt (gitignored) - never hardcode.
RELAY_TOKEN=$(grep "^TOKEN=" "$(dirname "$0")/relay_config.txt" | cut -d= -f2-)
cd "/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab" || exit 1
exec python3 relay/agent_bridge.py --relay http://100.98.97.23:8787 \
    --token "$RELAY_TOKEN" --me laptop-dourmouse \
    >> relay/bridge_laptop.log 2>&1
