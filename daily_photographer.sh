#!/bin/bash
# Daily photographer gallery automation
# Usage: bash daily_photographer.sh [count=10]
# Adds N photographers per day from the pending list

COUNT=${1:-10}
BASE="/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# TCC 铁律：launchd 跑外置盘脚本必须用 Framework python（/usr/bin/python3 无外置卷授权 + 无 PIL）
PY="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"

echo "[$(date)] Starting daily run: $COUNT photographers"
"$PY" "$SCRIPT_DIR/auto_add.py" --count "$COUNT" 2>&1 | tee -a "$SCRIPT_DIR/auto_add.log"
echo "[$(date)] Syncing to GitHub..."
bash "$SCRIPT_DIR/scripts/sync_github.sh"
echo "[$(date)] Done"
