#!/usr/bin/env python3
"""
Merge all v2_final shards into a single unified JSONL, then compute full stats.
This is the SCRIPT OF TRUTH — all final numbers come from here.
"""
import json, math
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")
MANIFEST_PATH = RESULTS_DIR / "live_sample_140_v2/manifest.json"
MERGED_PATH = RESULTS_DIR / "unified_v2_final.jsonl"
STATS_JSON = RESULTS_DIR / "unified_v2_final_stats.json"
STATS_MD = RESULTS_DIR / "unified_v2_final_stats.md"

# All shard files (v2 only — NEVER include v1 files)
SHARD_FILES = [
    "live_matrix_full_v2_final.jsonl",
    "tier4a_full_v2_final.jsonl",
    "tier5_live_full_v2_final.jsonl",
    "minimax_m3_all_v2_final.jsonl",
    "owl_alpha_t4a_t5_v2_final.jsonl",
]

def load_shards():
    """Load all unique good records from all v2_final shards."""
    seen = {}  # key = (backend, tier, filename, variant) -> record
    for shard_name in SHARD_FILES:
        p = RESULTS_DIR / shard_name
        if not p.exists():
            print("  WARNING: %s not found, skipping" % shard_name)
            continue
        n_loaded = 0
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    r = json.loads(line)
                except: continue
                # Skip errors and UNKNOWN predictions
                if r.get("error") and r["error"] not in ("", None):
                    continue
                if r.get("parsed_prediction","UNKNOWN") == "UNKNOWN":
                    continue
                key = (r.get("backend",""), r.get("tier",""), r.get("filename",""), r.get("variant") or "standard")
                # Dedup: keep latest
                if key not in seen or r.get("timestamp","") > seen[key].get("timestamp",""):
                    seen[key] = r
                    n_loaded += 1
        print("  %s: loaded %d unique good records" % (shard_name, n_loaded))
    records = list(seen.values())
    print("Total unique good records: %d" % len(records))
    return records, seen

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

def compute_all_stats(records, seen_keys):
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    all_filenames = set(s["filename"] for s in manifest["samples"])
    samples_by_name = {s["filename"]: s for s in manifest["samples"]}
    
    backends = sorted(set(r["backend"] for r in records))
    tiers = sorted(set(r["tier"] for r in records))
    families = sorted(set(r["ground_truth"] for r in records))
    
    stats = {
        "label": "ACTS v2 FINAL — unified",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backends": backends,
        "tiers": tiers,
        "families": families,
        "total_good_records": len(records),
        "shard_files": SHARD_FILES,
    }
    
    # Per (backend, tier)
    bt_stats = {}
    for b in backends:
        for t in tiers:
            subset = [r for r in records if r["backend"]==b and r["tier"]==t]
            if not subset:
                bt_stats[(b,t)] = {"k":0,"n":0,"accuracy":0.0,"ci_lower":0.0,"ci_upper":0.0,"missing_files":140}
                continue
            k = sum(1 for r in subset if r.get("correct"))
            n = len(subset)
            lo, hi = wilson_ci(k, n)
            have_files = set(r["filename"] for r in subset)
            bt_stats[(b,t)] = {
                "k":k,"n":n,
                "accuracy":round(k/n,4),
                "ci_lower":round(lo,4),"ci_upper":round(hi,4),
                "missing_files": 140 - len(have_files),
            }
    stats["per_backend_tier"] = {f"{b}|{t}": v for (b,t),v in sorted(bt_stats.items())}
    
    # Overall per-tier (pooled)
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
        t1 = bt_stats.get((b,"tier1"),{})
        t2 = bt_stats.get((b,"tier2"),{})
        t3 = bt_stats.get((b,"tier3"),{})
        t4a = bt_stats.get((b,"tier4a"),{})
        t5 = bt_stats.get((b,"tier5"),{})
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
    
    # Default guess analysis per (backend, tier)
    default_guesses = {}
    for b in backends:
        for t in tiers:
            subset = [r for r in records if r["backend"]==b and r["tier"]==t]
            if not subset: continue
            pred_counts = Counter(r.get("parsed_prediction","UNKNOWN") for r in subset)
            total = len(subset)
            default_guesses[f"{b}|{t}"] = {
                pred: {"count": cnt, "pct": round(cnt/total,4)}
                for pred, cnt in pred_counts.most_common(7)
            }
    stats["default_guesses"] = default_guesses
    
    # Confusion matrices per (backend, tier)
    confusion = {}
    for b in backends:
        for t in tiers:
            subset = [r for r in records if r["backend"]==b and r["tier"]==t]
            if not subset: continue
            all_preds = sorted(set(r.get("parsed_prediction","UNKNOWN") for r in subset))
            matrix = {}
            for fam in families:
                row = {}
                for pred in all_preds:
                    cnt = sum(1 for r in subset if r["ground_truth"]==fam and r.get("parsed_prediction")==pred)
                    if cnt > 0: row[pred] = cnt
                matrix[fam] = row
            confusion[f"{b}|{t}"] = matrix
    stats["confusion_matrices"] = confusion
    
    # Coverage grid
    coverage = {}
    for b in backends:
        for t in tiers:
            have = set(r["filename"] for r in records if r["backend"]==b and r["tier"]==t)
            coverage[f"{b}|{t}"] = {"good": len(have), "missing": 140-len(have), "pct": round(len(have)/140*100,1)}
    stats["coverage"] = coverage
    
    # Missing cells summary
    total_cells = len(backends) * len(tiers)
    incomplete = []
    for key, v in coverage.items():
        if v.get("missing", 0) > 0:
            b, t = key.split("|", 1)
            incomplete.append((b, t))
    stats["complete_cells"] = total_cells - len(incomplete)
    stats["total_cells"] = total_cells
    stats["incomplete_cells"] = [{"backend":b,"tier":t,"missing":coverage[f"{b}|{t}"]["missing"]} for b,t in incomplete]
    
    return stats, backends, tiers, families, bt_stats

def generate_md(stats, backends, tiers, families, bt_stats):
    lines = []
    lines.append("# ACTS v2 — FINAL Results (Pure v2, No v1 Mixing)")
    lines.append("")
    lines.append("**Generated:** %s" % stats["generated_at"])
    lines.append("")
    
    # Backend + corpus info
    lines.append("## Experimental Setup")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    lines.append("| Corpus | live_sample_140_v2 (140 distinct files, secrets.SystemRandom) |")
    lines.append("| Backends | %d: %s |" % (len(backends), ", ".join(backends)))
    lines.append("| Total good records | %d |" % stats["total_good_records"])
    lines.append("| Tiers | %s |" % ", ".join(tiers))
    lines.append("| Families | %s |" % ", ".join(families))
    lines.append("")
    
    # Coverage
    lines.append("## Coverage")
    lines.append("")
    lines.append("- Complete cells: %d / %d" % (stats["complete_cells"], stats["total_cells"]))
    if stats.get("incomplete_cells"):
        lines.append("- **INCOMPLETE cells:**")
        for cell in stats["incomplete_cells"]:
            lines.append("  - %s %s: %d missing" % (cell["backend"], cell["tier"], cell["missing"]))
    lines.append("")
    
    # Coverage grid
    lines.append("## Coverage Grid")
    lines.append("")
    header = "| Backend |" + "".join(" %s |" % t for t in tiers)
    sep = "|---------|" + "--------|" * len(tiers)
    lines.append(header); lines.append(sep)
    for b in backends:
        row = "| %s |" % b
        for t in tiers:
            cov = stats["coverage"].get(f"{b}|{t}",{})
            if cov.get("missing",0) == 0:
                row += " ✅ (%d) |" % cov.get("good",0)
            else:
                row += " 🔄 %d/140 (%d miss) |" % (cov.get("good",0), cov.get("missing",0))
        lines.append(row)
    lines.append("")
    
    # Overall per-tier
    lines.append("## Overall Per-Tier Accuracy (Wilson 95% CI)")
    lines.append("")
    lines.append("| Tier | k/N | Accuracy | 95% CI |")
    lines.append("|------|-----|----------|--------|")
    for t in tiers:
        key = f"overall_{t}"
        if key in stats and stats[key]["n"] > 0:
            v = stats[key]
            lines.append("| %s | %d/%d | %.1f%% | [%.1f%%, %.1f%%] |" % (t, v["k"], v["n"], v["accuracy"]*100, v["ci_lower"]*100, v["ci_upper"]*100))
    lines.append("")
    
    # Per-backend × tier
    lines.append("## Per-Backend × Tier Accuracy")
    lines.append("")
    header2 = "| Backend |" + "".join(" %s |" % t for t in tiers)
    sep2 = "|---------|" + "--------|" * len(tiers)
    lines.append(header2); lines.append(sep2)
    for b in backends:
        row = "| %s |" % b
        for t in tiers:
            v = bt_stats.get((b,t),{})
            if v.get("n",0) > 0:
                note = " [%d miss]" % v.get("missing_files",0) if v.get("missing_files",0) > 0 else ""
                row += " %.0f%% [%.0f%%,%.0f%%] (%d/%d)%s |" % (v["accuracy"]*100, v["ci_lower"]*100, v["ci_upper"]*100, v["k"], v["n"], note)
            else:
                row += " N/A |"
        lines.append(row)
    lines.append("")
    
    # Newcombe gaps
    lines.append("## Newcombe CI Gaps (vs Tier-3 Blind)")
    lines.append("")
    lines.append("| Backend | Gap | Estimate | 95% Newcombe CI | Significant? |")
    lines.append("|---------|-----|----------|-----------------|--------------|")
    for b in backends:
        g = stats.get("newcombe_gaps",{}).get(b,{})
        for gap_name in ["T1_vs_T3","T4A_vs_T3","T5_vs_T3"]:
            if gap_name in g:
                v = g[gap_name]
                sig = "Yes ***" if v["significant"] else "No (overlap)"
                lines.append("| %s | %s | %.1fpp | [%.1fpp, %.1fpp] | %s |" % (b, gap_name, v["gap"]*100, v["newcombe_ci"][0]*100, v["newcombe_ci"][1]*100, sig))
    lines.append("")
    
    # Default guess patterns
    lines.append("## Default Guess Analysis (Tier-3 Blind)")
    lines.append("")
    for b in backends:
        dg = stats["default_guesses"].get(f"{b}|tier3",{})
        if dg:
            lines.append("### %s" % b)
            lines.append("| Prediction | Count | % |")
            lines.append("|------------|-------|---|")
            for pred, info in sorted(dg.items(), key=lambda x: -x[1]["count"]):
                lines.append("| %s | %d | %.1f%% |" % (pred, info["count"], info["pct"]*100))
            lines.append("")
    
    lines.append("## Notes")
    lines.append("")
    lines.append("- Errors (429/timeout/parse) are EXCLUDED from k/N — never scored incorrect")
    lines.append("- All data from live_sample_140_v2 (secrets.SystemRandom, 140 distinct keys)")
    lines.append("- No mixing with v1 corpus (seed:42 bug, duplicate key-IV pairs)")
    lines.append("- Wilson score 95% CIs; Newcombe hybrid-score CIs for gap tests")
    
    return "\n".join(lines)

def main():
    print("=== Merging v2_final shards ===")
    records, seen_keys = load_shards()
    
    # Write merged JSONL
    with open(MERGED_PATH, "w") as f:
        for r in sorted(records, key=lambda x: (x.get("backend",""), x.get("tier",""), x.get("filename",""))):
            f.write(json.dumps(r, default=str) + "\n")
    print("Merged JSONL: %s (%d records)" % (MERGED_PATH, len(records)))
    
    # Compute stats
    print("\n=== Computing stats ===")
    stats, backends, tiers, families, bt_stats = compute_all_stats(records, seen_keys)
    
    with open(STATS_JSON, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print("Stats JSON: %s" % STATS_JSON)
    
    md = generate_md(stats, backends, tiers, families, bt_stats)
    with open(STATS_MD, "w") as f:
        f.write(md)
    print("Stats MD: %s" % STATS_MD)
    
    # Print key tables
    print("\n" + "="*70)
    for line in md.split("\n"):
        if line.startswith("|") and "---" not in line and line.count("|") > 3:
            print(line)
    print("="*70)
    
    return stats

if __name__ == "__main__":
    main()
