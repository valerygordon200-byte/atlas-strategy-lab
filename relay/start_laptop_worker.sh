#!/bin/bash
# launchd wrapper: start the laptop autonomous relay worker.
# launchd passes absolute paths; the space in "/Volumes/ATLAS /Atlas" must be
# handled inside the script, not in the launchd plist ProgramArguments.
exec /usr/bin/python3 "/Volumes/ATLAS /Atlas/dourmouse-4.0.0/atlas-strategy-lab/relay/autonomous_worker.py"
