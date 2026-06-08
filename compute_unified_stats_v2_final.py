#!/usr/bin/env python3
"""
ACTS v2 FINAL — Unified statistics from COMPLETE data.
Uses live_matrix_full.jsonl (T1/T2/T3, 5 backends, 140/140 each)
+ tier4a_full.jsonl (T4A, 4 backends)
+ tier5_live_full.jsonl (T5, 4 backends)
Errors EXCLUDED from k/N.
"""

import json, math
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
RESULTS_DIR = WORKSPACE / "stage2_execution/results"
OUT_DIR = WORKSPACE / "stage7_assembly/scaled_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_good(path):
    if not path.exists(): return []
    recs = []
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                if not r.get("error") and r.get("parsed_prediction","UNKNOWN") != "UNKNOWN":
                    recs.append(r)
            except: pass
    return recs

def wilson_ci(k, n, z=1.96):
    if n == 0: return [0.0, 0.0]
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    s = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5) / d
    return [round(max(0.0, c-s)*100, 1), round(min(1.0, c+s)*100, 1)]

def newcombe_ci(k1, n1, k2, n2, z=1.96):
    lo1, hi1 = wilson_ci(k1, n1, z)
    lo2, hi2 = wilson_ci(k2, n2, z)
    diff = (k1/n1 - k2/n2) * 100
    lo = diff - z * math.sqrt((lo1/100)*(1-lo1/100)/n1 + (hi2/100)*(1-hi2/100)/n2) * 100
    hi = diff + z * math.sqrt((hi1/100)*(1-hi1/100)/n1 + (lo2/100)*(1-lo2/100)/n2) * 100
    return [round(lo, 1), round(hi, 1)]

# Load data
main = load_good(RESULTS_DIR / "live_matrix_full.jsonl")
t4a = load_good(RESULTS_DIR / "tier4a_full.jsonl")
t5 = load_good(RESULTS_DIR / "tier5_live_full.jsonl")

all_recs = main + t4a + t5
print(f"Loaded: {len(main)} T1/T2/T3 + {len(t4a)} T4A + {len(t5)} T5 = {len(all_recs)} total")

BACKENDS = ['gemma4:31b-cloud','gpt-oss:120b-cloud','nemotron-3-super:cloud',
            'openrouter/owl-alpha','google/gemma-4-31b-it:free']
TIERS = ['tier1','tier2','tier3','tier4a','tier5']
TIER_LABELS = {'tier1':'T1','tier2':'T2','tier3':'T3','tier4a':'T4A','tier5':'T5'}

stats = {"generated_at": datetime.now(timezone.utc).isoformat(), "tiers": {}}

for tier in TIERS:
    recs = [r for r in all_recs if r.get("tier") == tier]
    if not recs: continue
    
    # Normalize GT
    for r in recs:
        gt = r.get("ground_truth","")
        m = {'3DES':'3des','AES-128':'aes-128','AES-256':'aes-256','DES':'des',
             'ChaCha20':'chacha20','RSA-2048':'rsa-2048','ML-KEM-768':'ml-kem-768'}
        r["gt"] = m.get(gt, gt.lower())
    
    k = sum(1 for r in recs if r.get("correct"))
    n = len(recs)
    ci = wilson_ci(k, n)
    
    stats["tiers"][tier] = {
        "label": TIER_LABELS[tier],
        "total_records": n, "k": k,
        "accuracy": round(k/n*100, 1) if n else 0,
        "ci": ci,
        "per_backend": {},
        "coverage": {}
    }
    
    for b in BACKENDS:
        b_recs = [r for r in recs if r.get("backend") == b]
        if not b_recs: continue
        bk = sum(1 for r in b_recs if r.get("correct"))
        bn = len(b_recs)
        bci = wilson_ci(bk, bn)
        files = set(r.get("filename","") for r in b_recs)
        
        # Default guess
        preds = Counter(r.get("parsed_prediction","?") for r in b_recs)
        modal = preds.most_common(1)[0] if preds else ("none", 0)
        
        stats["tiers"][tier]["per_backend"][b] = {
            "k": bk, "n": bn,
            "accuracy": round(bk/bn*100, 1) if bn else 0,
            "ci": bci,
            "unique_files": len(files),
            "modal_prediction": modal[0],
            "modal_rate": round(modal[1]/bn*100, 1),
        }
        stats["tiers"][tier]["coverage"][b] = len(files)

# Gap analysis
for comp_name, t1_key, t2_key in [
    ("T1 vs T3", "tier1", "tier3"),
    ("T4A vs T3", "tier4a", "tier3"),
    ("T5 vs T3", "tier5", "tier3"),
]:
    for b in BACKENDS:
        t1 = [r for r in all_recs if r.get("backend")==b and r.get("tier")==t1_key]
        t2 = [r for r in all_recs if r.get("backend")==b and r.get("tier")==t2_key]
        if not t1 or not t2: continue
        k1, n1 = sum(1 for r in t1 if r.get("correct")), len(t1)
        k2, n2 = sum(1 for r in t2 if r.get("correct")), len(t2)
        nci = newcombe_ci(k1, n1, k2, n2)
        excludes = (nci[0] > 0 or nci[1] < 0)
        
        if "gaps" not in stats: stats["gaps"] = {}
        if comp_name not in stats["gaps"]: stats["gaps"][comp_name] = {}
        stats["gaps"][comp_name][b] = {
            "t1_acc": round(k1/n1*100, 1),
            "t2_acc": round(k2/n2*100, 1),
            "gap": round((k1/n1 - k2/n2)*100, 1),
            "ci": nci,
            "excludes_zero": excludes,
        }

# Save
with open(OUT_DIR / "live_stats_all_v2_final.json", "w") as f:
    json.dump(stats, f, indent=2, default=str)

# Markdown
lines = ["# ACTS v2 FINAL — Unified Live Evaluation Results\n"]
lines.append(f"Generated: {stats['generated_at']}\n")
lines.append("Errors and UNKNOWN predictions EXCLUDED from all denominators.\n")
lines.append("Coverage: 140 files × 20/family × 7 families per backend per tier.\n")

for tier in TIERS:
    if tier not in stats["tiers"]: continue
    t = stats["tiers"][tier]
    lines.append(f"\n## {t['label']}\n")
    lines.append(f"**Records:** {t['total_records']} | **Accuracy:** {t['accuracy']}% [{t['ci'][0]}%, {t['ci'][1]}%]\n")
    lines.append("| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |")
    lines.append("|---------|-----|------|---------------|-------|---------------|")
    for b in BACKENDS:
        if b not in t["per_backend"]: continue
        pb = t["per_backend"][b]
        lines.append(f"| {b} | {pb['k']}/{pb['n']} | {pb['accuracy']}% | [{pb['ci'][0]}%, {pb['ci'][1]}%] | {pb['unique_files']}/140 | {pb['modal_prediction']} ({pb['modal_rate']}%) |")

if "gaps" in stats:
    lines.append("\n## Gap Analysis (Newcombe CI)\n")
    for comp_name, comp_data in stats["gaps"].items():
        lines.append(f"\n### {comp_name}\n")
        lines.append("| Backend | T1 Acc | T2 Acc | Gap | 95% CI | Significant? |")
        lines.append("|---------|--------|--------|-----|--------|--------------")
        for b in BACKENDS:
            if b not in comp_data: continue
            d = comp_data[b]
            sig = "✅ Yes" if d["excludes_zero"] else "❌ No"
            lines.append(f"| {b} | {d['t1_acc']}% | {d['t2_acc']}% | {d['gap']}pp | [{d['ci'][0]}, {d['ci'][1]}] | {sig} |")

with open(OUT_DIR / "live_summary_all_v2_final.md", "w") as f:
    f.write("\n".join(lines))

# Print summary
print("\n=== SUMMARY ===")
for tier in TIERS:
    if tier in stats["tiers"]:
        t = stats["tiers"][tier]
        print(f"  {TIER_LABELS[tier]:10s}: {t['accuracy']:>6.1f}% [{t['ci'][0]:.1f}%, {t['ci'][1]:.1f}%] ({t['k']}/{t['total_records']})")

print("\n=== GAPS ===")
if "gaps" in stats:
    for comp_name, comp_data in stats["gaps"].items():
        print(f"\n  {comp_name}:")
        for b in BACKENDS:
            if b in comp_data:
                d = comp_data[b]
                sig = "✅" if d["excludes_zero"] else "❌"
                print(f"    {b:40s}: {d['gap']:>6.1f}pp [{d['ci'][0]:.1f}, {d['ci'][1]:.1f}] {sig}")
