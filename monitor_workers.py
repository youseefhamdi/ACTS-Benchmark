#!/usr/bin/env python3
"""
Monitor: wait for minimax-m3 (PID 1010031) and owl-alpha T4A+T5 (PID 1010406).
When both done, merge all shards into final coverage grid and run final stats.
Runs as a one-shot check every 5 minutes.
"""
import json, subprocess, time, sys
from pathlib import Path
from datetime import datetime, timezone

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")
MANIFEST_PATH = RESULTS_DIR / "live_sample_140_v2/manifest.json"
LOG = RESULTS_DIR / "monitor_v2_r3.log"

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def check_pid(pid):
    r = subprocess.run(['ps', '-p', str(pid), '-o', 'pid,etime', '--no-headers'], capture_output=True, text=True)
    return r.stdout.strip() or None

def count_shard(path):
    if not path.exists(): return 0
    return sum(1 for _ in open(path))

def coverage_grid():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    all_files = set(s['filename'] for s in manifest['samples'])
    BACKENDS = ['gemma4:31b-cloud','gpt-oss:120b-cloud','nemotron-3-super:cloud',
                'minimax-m3:cloud','openrouter/owl-alpha']
    TIERS = ['tier1','tier2','tier3','tier4a','tier5']
    existing = {}
    for path in ['live_matrix_full_v2_final.jsonl','tier4a_full_v2_final.jsonl',
                 'tier5_live_full_v2_final.jsonl','minimax_m3_all_v2_final.jsonl',
                 'owl_alpha_t4a_t5_v2_final.jsonl']:
        p = RESULTS_DIR / path
        if not p.exists(): continue
        with open(p) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if not r.get('error') and r.get('parsed_prediction','UNKNOWN')!='UNKNOWN':
                        key = (r['backend'], r['tier'])
                        if key not in existing: existing[key] = set()
                        existing[key].add(r['filename'])
                except: pass
    lines = []
    complete_cells = 0
    total_cells = len(BACKENDS) * len(TIERS)
    for b in BACKENDS:
        row = b.ljust(40)
        for t in TIERS:
            have = existing.get((b,t), set())
            n = len(have)
            if n == 140: row += "  OK   "; complete_cells += 1
            elif n > 0: row += "  %3d  " % n
            else: row += "   0   "
        lines.append(row)
    return lines, complete_cells, total_cells

# Main check
log("=== Monitor check ===")

mm3 = check_pid(1010031)
owl = check_pid(1010406)

mm3_count = count_shard(RESULTS_DIR / "minimax_m3_all_v2_final.jsonl")
owl_count = count_shard(RESULTS_DIR / "owl_alpha_t4a_t5_v2_final.jsonl")

log("minimax-m3 (1010031): %s, shard=%d records" % (mm3 or "DONE", mm3_count))
log("owl-alpha T4A+T5 (1010406): %s, shard=%d records" % (owl or "DONE", owl_count))

grid, ok, total = coverage_grid()
log("Coverage: %d/%d cells complete" % (ok, total))
for line in grid:
    log("  " + line)

if mm3 is None and owl is None:
    log("ALL WORKERS DONE — ready for merge + final stats")
    sys.exit(0)  # Signal: done
else:
    log("Still running — check again later")
    sys.exit(1)  # Signal: not done
