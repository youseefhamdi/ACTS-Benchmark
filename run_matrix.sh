#!/bin/bash
# Wrapper to load OpenRouter key from Hermes .env and run the matrix
set -e
cd /home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc

# Extract key from .env — find the line with OPENROUTER_API_KEY= and extract value
KEY=$(grep '^OPENROUTER_API_KEY=' /home/elaref/.hermes/.env | head -1 | cut -d= -f2-)
if [ -z "$KEY" ]; then
    echo "ERROR: OPENROUTER_API_KEY not found in .env" >&2
    exit 1
fi

export OPENROUTER_API_KEY="$KEY"
exec python3 stage2_execution/run_live_matrix.py "$@"
