#!/bin/bash
# Daily photographer gallery automation
# Usage: bash daily_photographer.sh [count=5]
# Adds N photographers per day from the pending list

COUNT=${1:-5}
BASE="/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[$(date)] Starting daily run: $COUNT photographers"
python3 "$SCRIPT_DIR/auto_add.py" --count "$COUNT" 2>&1 | tee -a "$SCRIPT_DIR/auto_add.log"
echo "[$(date)] Done"
