#!/usr/bin/env python3
"""
Interim stats: 3-backend pure v2 (gemma4, gpt-oss, nemotron)
Per-tier k/N + Wilson 95% CI, gaps T1-T3 / T4A-T3 / T5-T3 with Newcombe CIs.
"""
import json, math
from pathlib import Path
from datetime import datetime, timezone

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")
OUTPUT_JSON = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/live_stats_3backend_v2.json")
OUTPUT_MD = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/live_stats_3backend_v2.md")

BACKENDS = ["gemma4:31b-cloud", "gpt-oss:120b-cloud", "nemotron-3-super:cloud"]
# Load all v2_final JSONL files
records = []
for path in ["live_matrix_full_v2_final.jsonl", "tier4a_full_v2_final.jsonl", "tier5_live_full_v2_final.jsonl"]:
    p = RESULTS_DIR / path
    if not p.exists(): continue
    with open(p) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("backend") in BACKENDS:
                    if not r.get("error") and r.get("parsed_prediction","UNKNOWN") != "UNKNOWN":
                        records.append(r)
            except: pass

print(f"Loaded {len(records)} good records for {BACKENDS}")

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    spread = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / denom
    return (max(0.0, center-spread), min(1.0, center+spread))

def newcombe_ci(p1, n1, p2, n2, z=1.96):
    """Newcombe CI for difference of two proportions."""
    lo1, hi1 = wilson_ci(int(round(p1*n1)), n1, z)
    lo2, hi2 = wilson_ci(int(round(p2*n2)), n2, z)
    diff = p1 - p2
    lo = diff - math.sqrt((p1-lo1)**2 + (hi2-p2)**2)
    hi = diff + math.sqrt((hi1-p1)**2 + (p2-lo2)**2)
    return (lo, hi)

tiers = ["tier1", "tier2", "tier3", "tier4a", "tier5"]
families = sorted(set(r["ground_truth"] for r in records))

stats = {
    "label": "3-backend interim, pure v2",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "backends": BACKENDS,
    "tiers": tiers,
    "families": families,
    "total_records": len(records),
}

# Per (backend, tier)
bt_stats = {}
for b in BACKENDS:
    for t in tiers:
        subset = [r for r in records if r["backend"]==b and r["tier"]==t]
        if not subset:
            bt_stats[(b,t)] = {"k":0,"n":0,"accuracy":0.0,"ci_lower":0.0,"ci_upper":0.0}
            continue
        k = sum(1 for r in subset if r.get("correct"))
        n = len(subset)
        lo, hi = wilson_ci(k, n)
        bt_stats[(b,t)] = {"k":k,"n":n,"accuracy":round(k/n,4),"ci_lower":round(lo,4),"ci_upper":round(hi,4)}
stats["per_backend_tier"] = {f"{b}|{t}": v for (b,t),v in sorted(bt_stats.items())}

# Overall per-tier (pooled across 3 backends)
for t in tiers:
    subset = [r for r in records if r["tier"]==t]
    k = sum(1 for r in subset if r.get("correct"))
    n = len(subset)
    lo, hi = wilson_ci(k, n)
    stats[f"overall_{t}"] = {"k":k,"n":n,"accuracy":round(k/n,4),"ci_lower":round(lo,4),"ci_upper":round(hi,4)}

# Newcombe gaps per backend
gaps = {}
for b in BACKENDS:
    t1 = bt_stats.get(("gemma4:31b-cloud" if False else b, "tier1"), {})  # use actual backend
    # fix: use the loop var
    t1 = bt_stats.get((b, "tier1"), {})
    t3 = bt_stats.get((b, "tier3"), {})
    t4a = bt_stats.get((b, "tier4a"), {})
    t5 = bt_stats.get((b, "tier5"), {})
    
    gap_info = {}
    if t1 and t3 and t1.get("n",0)>0 and t3.get("n",0)>0:
        lo, hi = newcombe_ci(t1["accuracy"], t1["n"], t3["accuracy"], t3["n"])
        gap_info["T1_minus_T3"] = {
            "gap": round(t1["accuracy"]-t3["accuracy"], 4),
            "newcombe_ci": [round(lo,4), round(hi,4)],
            "significant": not (lo <= 0 <= hi)
        }
    if t4a and t3 and t4a.get("n",0)>0 and t3.get("n",0)>0:
        lo, hi = newcombe_ci(t4a["accuracy"], t4a["n"], t3["accuracy"], t3["n"])
        gap_info["T4A_minus_T3"] = {
            "gap": round(t4a["accuracy"]-t3["accuracy"], 4),
            "newcombe_ci": [round(lo,4), round(hi,4)],
            "significant": not (lo <= 0 <= hi)
        }
    if t5 and t3 and t5.get("n",0)>0 and t3.get("n",0)>0:
        lo, hi = newcombe_ci(t5["accuracy"], t5["n"], t3["accuracy"], t3["n"])
        gap_info["T5_minus_T3"] = {
            "gap": round(t5["accuracy"]-t3["accuracy"], 4),
            "newcombe_ci": [round(lo,4), round(hi,4)],
            "significant": not (lo <= 0 <= hi)
        }
    gaps[b] = gap_info
stats["newcombe_gaps"] = gaps

# Save JSON
with open(OUTPUT_JSON, "w") as f:
    json.dump(stats, f, indent=2)
print(f"Stats saved to {OUTPUT_JSON}")

# Generate markdown
lines = []
lines.append("# ACTS v2 — 3-Backend Interim Results (Pure v2)")
lines.append(f"\nGenerated: {stats['generated_at']}")
lines.append(f"Backends: {', '.join(BACKENDS)}")
lines.append(f"Total good records: {len(records)}")
lines.append("\n## Overall Per-Tier Accuracy\n")
lines.append("| Tier | k/N | Accuracy | 95% Wilson CI |")
lines.append("|------|-----|----------|---------------|")
for t in tiers:
    key = f"overall_{t}"
    if key in stats:
        v = stats[key]
        if v["n"] > 0:
            lines.append(f"| {t} | {v['k']}/{v['n']} | {v['accuracy']:.1%} | [{v['ci_lower']:.1%}, {v['ci_upper']:.1%}] |")

lines.append("\n## Per-Backend × Tier Accuracy\n")
header = "| Backend |" + "".join(f" {t} |" for t in tiers)
sep = "|---------|" + "--------|" * len(tiers)
lines.append(header)
lines.append(sep)
for b in BACKENDS:
    row = f"| {b} |"
    for t in tiers:
        v = bt_stats.get((b,t), {})
        if v.get("n", 0) > 0:
            row += f" {v['accuracy']:.0%} [{v['ci_lower']:.0%},{v['ci_upper']:.0%}] ({v['k']}/{v['n']}) |"
        else:
            row += " N/A |"
    lines.append(row)

lines.append("\n## Newcombe CI Gaps\n")
lines.append("| Backend | Gap | Estimate | 95% Newcombe CI | Significant? |")
lines.append("|---------|-----|----------|-----------------|--------------|")
for b in BACKENDS:
    g = gaps.get(b, {})
    for gap_name in ["T1_minus_T3", "T4A_minus_T3", "T5_minus_T3"]:
        if gap_name in g:
            v = g[gap_name]
            sig = "✅ Yes" if v["significant"] else "❌ No"
            lines.append(f"| {b} | {gap_name} | {v['gap']:.1%} | [{v['newcombe_ci'][0]:.1%}, {v['newcombe_ci'][1]:.1%}] | {sig} |")

md = "\n".join(lines)
with open(OUTPUT_MD, "w") as f:
    f.write(md)
print(f"Summary saved to {OUTPUT_MD}")
print("\n" + md)
