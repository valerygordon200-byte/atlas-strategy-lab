#!/bin/bash
cd "/Volumes/ATLAS /dourmouse-4.0.0/atlas-strategy-lab" || exit 1
exec python3 relay/agent_bridge.py --relay http://100.98.97.23:8787 \
    --token jXVXaHAeG721UkhMYRSq3rRXAK-iBIAY --me laptop-dourmouse \
    >> relay/bridge_laptop.log 2>&1
