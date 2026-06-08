#!/bin/bash
# Combined Tier-4A + Tier-5 + Unified Stats launcher
# Waits for main matrix completion, then runs Tier-4A and Tier-5,
# then computes unified statistics.
set -e
cd /home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc

# Load OpenRouter key
KEY=$(grep '^OPENROUTER_API_KEY=' /home/elaref/.hermes/.env | head -1 | cut -d= -f2-)
if [ -z "$KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY not found in .env" >&2
    exit 1
fi
export OPENROUTER_API_KEY="$KEY"

echo "============================================"
echo "STEP 1: Wait for main matrix completion..."
echo "============================================"

# Poll until live_matrix_full.jsonl has all 5 backends done
# Expected: 5 backends × (140 tier1 + 140 tier2 + 140 tier3 + 140 tier3_raw) = 2800 records
while true; do
    if [ -f stage2_execution/results/live_matrix_full.jsonl ]; then
        LINES=$(wc -l < stage2_execution/results/live_matrix_full.jsonl)
        # Count unique backends in tier3 standard (the last tier to complete)
        BACKENDS_DONE=$(python3 -c "
import json
from pathlib import Path
from collections import defaultdict
p = Path('stage2_execution/results/live_matrix_full.jsonl')
recs = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
bt = defaultdict(int)
for r in recs:
    v = r.get('variant') or 'standard'
    if r.get('tier') == 'tier3' and v == 'standard':
        bt[r['backend']] += 1
done = [b for b, n in bt.items() if n >= 140]
print(len(done))
" 2>/dev/null || echo 0)
        echo "[$(date +%H:%M:%S)] Main matrix: $LINES records, $BACKENDS_DONE/5 backends done with tier3"
        if [ "$BACKENDS_DONE" -ge 5 ] 2>/dev/null; then
            echo "Main matrix COMPLETE!"
            break
        fi
    fi
    sleep 60
done

echo ""
echo "============================================"
echo "COMPUTE UNIFIED STATS + TIER-4A + TIER-5"
echo "============================================"

# First compute partial unified stats (will be recomputed after T4A/T5)
echo ""
echo ">>> Running Tier-4A (tool-augmented blind)..."
python3 stage2_execution/run_tier4a_t5.py --tier4a --delay 0.5 2>&1 | tee stage2_execution/results/tier4a_run.log

echo ""
echo ">>> Running Tier-5 (forced CoT reasoning)..."
python3 stage2_execution/run_tier4a_t5.py --tier5 --delay 0.5 2>&1 | tee stage2_execution/results/tier5_run.log

echo ""
echo ">>> Computing unified statistics across all tiers..."
python3 stage2_execution/compute_unified_stats.py \
    --output-stats stage7_assembly/scaled_results/live_stats_all.json \
    --output-summary stage7_assembly/scaled_results/live_summary_all.md \
    2>&1 | tee stage2_execution/results/unified_stats.log

echo ""
echo "============================================"
echo "ALL COMPLETE"
echo "============================================"
echo "Stats:   stage7_assembly/scaled_results/live_stats_all.json"
echo "Summary: stage7_assembly/scaled_results/live_summary_all.md"
echo "Raw:     stage2_execution/results/live_matrix_full.jsonl"
echo "         stage2_execution/results/tier4a_full.jsonl"
echo "         stage2_execution/results/tier5_live_full.jsonl"
