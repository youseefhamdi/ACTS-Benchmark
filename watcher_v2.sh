#!/bin/bash
# Watcher script: checks if main matrix v2 completed, then launches Tier-4A + Tier5
LOG="/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/watcher_v2.log"
JSONL="/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/live_matrix_full_v2.jsonl"
PID_FILE="/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/main_matrix_v2.pid"

echo "$(date): Watcher started" >> "$LOG"

# Check if main matrix process is still running
MAIN_PID=$(cat "$PID_FILE" 2>/dev/null)
if [ -z "$MAIN_PID" ]; then
    # Try to find it
    MAIN_PID=$(pgrep -f "run_live_matrix_v2.py" | head -1)
fi

if [ -n "$MAIN_PID" ] && kill -0 "$MAIN_PID" 2>/dev/null; then
    echo "$(date): Main matrix still running (PID $MAIN_PID)" >> "$LOG"
    exit 0
fi

# Main matrix completed - check record count
RECORD_COUNT=$(wc -l < "$JSONL" 2>/dev/null || echo 0)
echo "$(date): Main matrix completed with $RECORD_COUNT records" >> "$LOG"

# Launch Tier-4A + Tier-5
cd /home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc
nohup python3 stage2_execution/run_tier4a_t5_v2.py --both >> stage2_execution/results/tier4a_t5_v2.log 2>&1 &
echo "$(date): Launched Tier-4A + Tier-5 (PID $!)" >> "$LOG"
