#!/bin/bash
cd /home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc

# Source OpenRouter key from Hermes .env into environment
if [ -f /home/elaref/.hermes/.env ]; then
    while IFS= read -r line; do
        case "$line" in
            OPENROUTER_API_KEY=*)
                export "$line"
                echo "[INFO] OPENROUTER_API_KEY loaded from .env (length=${#line})"
                break
                ;;
        esac
    done < /home/elaref/.hermes/.env
fi

echo ""
echo "STEP 1: Running Tier-4A (tool-augmented blind)..."
echo "============================================"
python3 stage2_execution/run_tier4a_t5.py --tier4a --delay 0.5 2>&1 | tee stage2_execution/results/tier4a_run.log

echo ""
echo "STEP 2: Running Tier-5 (forced CoT reasoning)..."
echo "============================================"
python3 stage2_execution/run_tier4a_t5.py --tier5 --delay 0.5 2>&1 | tee stage2_execution/results/tier5_run.log

echo ""
echo "STEP 3: Computing unified statistics..."
echo "============================================"
python3 stage2_execution/compute_unified_stats.py \
    --output-stats stage7_assembly/scaled_results/live_stats_all.json \
    --output-summary stage7_assembly/scaled_results/live_summary_all.md \
    2>&1 | tee stage2_execution/results/unified_stats.log

echo ""
echo "ALL COMPLETE"
echo "============================================"
echo "Stats:   stage7_assembly/scaled_results/live_stats_all.json"
echo "Summary: stage7_assembly/scaled_results/live_summary_all.md"
