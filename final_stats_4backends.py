#!/usr/bin/env python3
"""
FINAL unified stats — 4 backends only (minimax excluded), pure v2, errors excluded.
Overwrites unified_v2_final_stats.json with clean 4-backend data.
"""
import json, math
from pathlib import Path
from datetime import datetime, timezone

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")
MERGED_PATH = RESULTS_DIR / "unified_v2_final.jsonl"
STATS_JSON = RESULTS_DIR / "unified_v2_final_stats.json"
STATS_MD = RESULTS_DIR / "unified_v2_final_stats.md"

# Allowed backends — minimax EXCLUDED
ALLOWED_BACKENDS = {"gemma4:31b-cloud", "gpt-oss:120b-cloud", "nemotron-3-super:cloud", "openrouter/owl-alpha"}

# Shard files (minimax shard is ARCHIVED, not in this list)
SHARDS = [
    "live_matrix_full_v2_final.jsonl",
    "tier4a_full_v2_final.jsonl",
    "tier5_live_full_v2_final.jsonl",
    "owl_alpha_t4a_t5_v2_final.jsonl",
]

# Load and filter
records = []
seen = {}
for shard in SHARDS:
    p = RESULTS_DIR / shard
    if not p.exists():
        print(f"  WARNING: {shard} not found")
        continue
    with open(p) as f:
        for line in f:
            try:
                r = json.loads(line)
            except:
                continue
            # HARD FILTER: exclude minimax and any other non-allowed backend
            if r.get("backend") not in ALLOWED_BACKENDS:
                continue
            # Exclude errors and UNKNOWN predictions
            if r.get("error") and r["error"] not in ("", None):
                continue
            if r.get("parsed_prediction", "UNKNOWN") == "UNKNOWN":
                continue
            key = (r.get("backend",""), r.get("tier",""), r.get("filename",""), r.get("variant") or "standard")
            if key not in seen or r.get("timestamp","") > seen[key].get("timestamp",""):
                seen[key] = r

records = list(seen.values())
backends = sorted(set(r["backend"] for r in records))
tiers = sorted(set(r["tier"] for r in records))
families = sorted(set(r["ground_truth"] for r in records))

print(f"4-backend records: {len(records)}")
print(f"Backends: {backends}")
print(f"Tiers: {tiers}")

# Verify no minimax sneaked in
for r in records:
    assert r["backend"] in ALLOWED_BACKENDS, f"FOREIGN BACKEND: {r['backend']}"

# ── ShardSizes ──
for shard in SHARDS:
    p = RESULTS_DIR / shard
    if p.exists():
        lines = sum(1 for _ in open(p))
        print(f"  {shard}: {lines} lines")

def wilson_ci(k, n, z=1.96):
    if n == 0: return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    spread = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / denom
    return (max(0.0, center-spread), min(1.0, center+spread))

def newcombe_ci(p1, n1, p2, n2, z=1.96):
    lo1, hi1 = wilson_ci(int(round(p1*n1)), n1, z)
    lo2, hi2 = wilson_ci(int(round(p2*n2)), n2, z)
    diff = p1 - p2
    lo = diff - math.sqrt((p1-lo1)**2 + (hi2-p2)**2)
    hi = diff + math.sqrt((hi1-p1)**2 + (p2-lo2)**2)
    return (lo, hi)

stats = {
    "label": "ACTS v2 FINAL — 4 backends, pure v2, minimax excluded",
    "note": "Errors (429/timeout/parse) excluded from k/N. UNKNOWN predictions excluded.",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "backends": backends,
    "tiers": tiers,
    "families": families,
    "total_good_records": len(records),
    "excluded_backends": ["minimax-m3:cloud (incomplete, too slow)"],
}

# Per (backend, tier)
bt_stats = {}
for b in backends:
    for t in tiers:
        subset = [r for r in records if r["backend"]==b and r["tier"]==t]
        if not subset:
            bt_stats[(b,t)] = {"k":0,"n":0,"missing":140,"accuracy":0.0,"ci_lower":0.0,"ci_upper":0.0}
            continue
        k = sum(1 for r in subset if r.get("correct"))
        n = len(subset)
        lo, hi = wilson_ci(k, n)
        have = set(r["filename"] for r in subset)
        bt_stats[(b,t)] = {
            "k":k,"n":n,"missing":140-len(have),
            "accuracy":round(k/n,4),"ci_lower":round(lo,4),"ci_upper":round(hi,4),
        }
stats["per_backend_tier"] = {f"{b}|{t}": v for (b,t),v in sorted(bt_stats.items())}

# Overall per-tier (pooled across 4 backends)
for t in tiers:
    subset = [r for r in records if r["tier"]==t]
    k = sum(1 for r in subset if r.get("correct"))
    n = len(subset)
    lo, hi = wilson_ci(k, n)
    stats[f"overall_{t}"] = {"k":k,"n":n,"accuracy":round(k/n,4),"ci_lower":round(lo,4),"ci_upper":round(hi,4)}

# Per (backend, tier, family)
btf_stats = {}
for b in backends:
    for t in tiers:
        for fam in families:
            subset = [r for r in records if r["backend"]==b and r["tier"]==t and r["ground_truth"]==fam]
            if not subset:
                btf_stats[(b,t,fam)] = {"k":0,"n":0,"accuracy":0.0,"ci_lower":0.0,"ci_upper":0.0}
                continue
            k = sum(1 for r in subset if r.get("correct"))
            n = len(subset)
            lo, hi = wilson_ci(k, n)
            btf_stats[(b,t,fam)] = {"k":k,"n":n,"accuracy":round(k/n,4),"ci_lower":round(lo,4),"ci_upper":round(hi,4)}
stats["per_backend_tier_family"] = {f"{b}|{t}|{f}": v for (b,t,f),v in sorted(btf_stats.items())}

# Newcombe gaps per backend
gaps = {}
for b in backends:
    gap_info = {}
    for n1,n2,label in [("tier1","tier3","T1_vs_T3"),("tier4a","tier3","T4A_vs_T3"),("tier5","tier3","T5_vs_T3")]:
        s1 = bt_stats.get((b,n1),{})
        s2 = bt_stats.get((b,n2),{})
        if s1.get("n",0)>0 and s2.get("n",0)>0:
            lo,hi = newcombe_ci(s1["accuracy"],s1["n"],s2["accuracy"],s2["n"])
            gap_info[label] = {
                "gap": round(s1["accuracy"]-s2["accuracy"],4),
                "newcombe_ci": [round(lo,4),round(hi,4)],
                "significant": not (lo <= 0 <= hi)
            }
    gaps[b] = gap_info
stats["newcombe_gaps"] = gaps

# Default guess analysis per (backend, tier3)
dg = {}
for b in backends:
    subset = [r for r in records if r["backend"]==b and r["tier"]=="tier3"]
    if not subset: continue
    total = len(subset)
    counts = {}
    for r in subset:
        pred = r.get("parsed_prediction","UNKNOWN")
        counts[pred] = counts.get(pred,0) + 1
    dg[b] = {pred:{"count":cnt,"pct":round(cnt/total,4)} for pred,cnt in sorted(counts.items(), key=lambda x:-x[1])[:8]}
stats["default_guesses_t3"] = dg

# Coverage grid
coverage = {}
for b in backends:
    for t in tiers:
        have = set(r["filename"] for r in records if r["backend"]==b and r["tier"]==t)
        coverage[f"{b}|{t}"] = {"good":len(have),"missing":140-len(have),"pct":round(len(have)/140*100,1)}
stats["coverage"] = coverage
stats["complete_cells"] = sum(1 for v in coverage.values() if v["missing"]==0)
stats["total_cells"] = len(backends) * len(tiers)

# Write JSON
with open(STATS_JSON, "w") as f:
    json.dump(stats, f, indent=2, default=str)
print(f"\nStats JSON overwritten: {STATS_JSON}")

# ── Generate Markdown ──
lines = []
lines.append("# ACTS v2 — FINAL Results (4 Backends, Pure v2)")
lines.append(f"\n**Generated:** {stats['generated_at']}")
lines.append(f"**Backends:** {len(backends)} ({', '.join(backends)})")
lines.append(f"**Excluded:** minimax-m3:cloud (incomplete: T3 at ~39/140 after 1h+, T4A/T5 not started)")
lines.append(f"**Total good records:** {len(records)}")
lines.append(f"**Complete cells:** {stats['complete_cells']}/{stats['total_cells']}")
lines.append("")

# Coverage
lines.append("## 1. Coverage Grid\n")
header = "| Backend |" + "".join(f" {t} |" for t in tiers)
sep = "|---------|" + "--------|" * len(tiers)
lines.append(header); lines.append(sep)
for b in backends:
    row = f"| {b} |"
    for t in tiers:
        cov = coverage[f"{b}|{t}"]
        if cov["missing"] == 0:
            row += f" ✅ ({cov['good']}) |"
        else:
            row += f" 🔄 {cov['good']}/140 ({cov['missing']} miss) |"
    lines.append(row)
lines.append("")

# Overall per-tier
lines.append("## 2. Overall Per-Tier Accuracy (Wilson 95% CI)\n")
lines.append("| Tier | k/N | Accuracy | 95% CI |")
lines.append("|------|-----|----------|--------|")
for t in tiers:
    v = stats[f"overall_{t}"]
    if v["n"] > 0:
        lines.append(f"| {t} | {v['k']}/{v['n']} | {v['accuracy']:.1%} | [{v['ci_lower']:.1%}, {v['ci_upper']:.1%}] |")
lines.append("")

# Per-backend × tier
lines.append("## 3. Per-Backend × Tier Accuracy\n")
header2 = "| Backend |" + "".join(f" {t} |" for t in tiers)
sep2 = "|---------|" + "--------|" * len(tiers)
lines.append(header2); lines.append(sep2)
for b in backends:
    row = f"| {b} |"
    for t in tiers:
        v = bt_stats.get((b,t),{})
        if v.get("n",0) > 0:
            note = f" [{v['missing']} miss]" if v.get("missing",0) > 0 else ""
            row += f" {v['accuracy']:.0%} [{v['ci_lower']:.0%},{v['ci_upper']:.0%}] ({v['k']}/{v['n']}){note} |"
        else:
            row += " N/A |"
    lines.append(row)
lines.append("")

# Newcombe gaps
lines.append("## 4. Newcombe CI Gaps (vs Tier-3 Blind)\n")
lines.append("| Backend | Gap | Estimate | 95% Newcombe CI | Significant? |")
lines.append("|---------|-----|----------|-----------------|--------------|")
for b in backends:
    g = gaps.get(b,{})
    for gap_name in ["T1_vs_T3","T4A_vs_T3","T5_vs_T3"]:
        if gap_name in g:
            v = g[gap_name]
            sig = "✅ Yes ***" if v["significant"] else "❌ No (overlap)"
            lines.append(f"| {b} | {gap_name} | {v['gap']:.1%} | [{v['newcombe_ci'][0]:.1%}, {v['newcombe_ci'][1]:.1%}] | {sig} |")
lines.append("")

# Default guesses
lines.append("## 5. Default Guess Analysis (Tier-3 Blind)\n")
for b in backends:
    d = dg.get(b,{})
    if d:
        lines.append(f"### {b}")
        lines.append("| Prediction | Count | % |")
        lines.append("|------------|-------|---|")
        for pred, info in d.items():
            lines.append(f"| {pred} | {info['count']} | {info['pct']:.1%} |")
        lines.append("")

# Notes
lines.append("## Notes\n")
lines.append("- Errors (429/timeout/parse) are EXCLUDED from k/N — never scored incorrect")
lines.append("- UNKNOWN predictions are EXCLUDED from k/N")
lines.append("- All data from live_sample_140_v2 (secrets.SystemRandom, 140 distinct keys)")
lines.append("- No mixing with v1 corpus (seed:42 bug, duplicate key-IV pairs)")
lines.append("- Wilson score 95% CIs; Newcombe hybrid-score CIs for gap tests")
lines.append("- minimax-m3:cloud excluded: T3 only 39/140 after 1h+ (Ollama cloud rate limits, ~2min/file thinking time), T4A/T5 not started")

md = "\n".join(lines)
with open(STATS_MD, "w") as f:
    f.write(md)
print(f"Stats MD overwritten: {STATS_MD}")

# Print key tables
print("\n" + "="*70)
for line in md.split("\n"):
    if line.startswith("|") and "---" not in line and line.count("|") > 3:
        print(line)
print("="*70)
