#!/usr/bin/env python3
"""Check if we have enough data to produce final results."""
import json
from pathlib import Path
from collections import Counter

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")
MANIFEST_PATH = RESULTS_DIR / "live_sample_140_v2/manifest.json"

# Load all good records from ALL shards (partial or complete)
records = []
seen = {}
for path in ["live_matrix_full_v2_final.jsonl","tier4a_full_v2_final.jsonl",
             "tier5_live_full_v2_final.jsonl","minimax_m3_all_v2_final.jsonl",
             "owl_alpha_t4a_t5_v2_final.jsonl"]:
    p = RESULTS_DIR / path
    if not p.exists(): continue
    with open(p) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("error") and r["error"] not in ("", None): continue
                if r.get("parsed_prediction","UNKNOWN") == "UNKNOWN": continue
                key = (r.get("backend",""), r.get("tier",""), r.get("filename",""), r.get("variant") or "standard")
                if key not in seen or r.get("timestamp","") > seen[key].get("timestamp",""):
                    seen[key] = r
            except: pass

records = list(seen.values())
backends = sorted(set(r["backend"] for r in records))
tiers = sorted(set(r["tier"] for r in records))

print(f"Total good records: {len(records)}")
print(f"Backends: {backends}")
print(f"Tiers: {tiers}")

# Per-backend coverage
print("\n=== Per-Backend Coverage ===")
for b in backends:
    for t in tiers:
        subset = [r for r in records if r["backend"]==b and r["tier"]==t]
        if subset:
            k = sum(1 for r in subset if r.get("correct"))
            n = len(subset)
            families = Counter(r["ground_truth"] for r in subset)
            print(f"  {b:40s} {t}: {n:>3d}/140 good, {k}/{n} correct ({k/n*100:.1f}%) | families: {dict(families)}")

# Cells with >= 100 good records (usable for stats)
print("\n=== Usable Cells (>= 100 good records) ===")
usable = 0
for b in backends:
    for t in tiers:
        n = sum(1 for r in records if r["backend"]==b and r["tier"]==t)
        if n >= 100:
            usable += 1
            print(f"  ✅ {b} {t}: {n}/140")
        elif n > 0:
            print(f"  🔄 {b} {t}: {n}/140 (partial)")
        else:
            print(f"  ❌ {b} {t}: 0/140")
print(f"\nUsable cells: {usable}/{len(backends)*len(tiers)}")
