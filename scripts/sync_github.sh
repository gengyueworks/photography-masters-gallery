#!/bin/bash
# Sync gallery progress to GitHub (private repo)
# 1. Recompute PROGRESS.md from disk truth
# 2. Fix index.html counts
# 3. git commit + push (no-op if nothing changed)
BASE="/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
cd "$BASE" || exit 1

# Step 1+2: regenerate PROGRESS.md and sync counts
python3 "$BASE/scripts/generate_progress.py" >>"$BASE/daily_progress.log" 2>&1

# Step 3: commit if changed, always push (no-op if up-to-date, auto-retries next run)
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "auto-sync: $(date '+%Y-%m-%d') gallery progress" >/dev/null 2>&1
fi
if git push -q origin main >>"$BASE/daily_progress.log" 2>&1; then
  echo "[$(date)] GitHub synced" >>"$BASE/daily_progress.log"
else
  echo "[$(date)] Push failed (network?), will retry next run" >>"$BASE/daily_progress.log"
fi
