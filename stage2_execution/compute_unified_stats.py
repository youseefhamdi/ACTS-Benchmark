#!/usr/bin/env python3
"""
Unified stats computation across ALL tiers.
Reads Tier 1/2/3 (+ tier3_raw), Tier-4A, and Tier-5 JSONLs.
Computes per (tier × backend × family) and per (tier × overall) k/N + Wilson 95% CI.
Also computes gaps, default-guess rates, and confusion matrices.
"""

import json, math, argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")

TIER_PATHS = {
    "tier1":      WORKSPACE / "stage2_execution/results/live_matrix_full.jsonl",
    "tier2":      WORKSPACE / "stage2_execution/results/live_matrix_full.jsonl",
    "tier3":      WORKSPACE / "stage2_execution/results/live_matrix_full.jsonl",
    "tier3_raw":  WORKSPACE / "stage2_execution/results/live_matrix_full.jsonl",
    "tier4a":     WORKSPACE / "stage2_execution/results/tier4a_full.jsonl",
    "tier5":      WORKSPACE / "stage2_execution/results/tier5_live_full.jsonl",
}

FAMILIES = ["AES-128", "AES-256", "DES", "3DES", "ChaCha20", "RSA-2048", "ML-KEM-768"]


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple:
    if n == 0:
        return (0.0, 0.0)
    p_hat = k / n
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def load_records_for_tier(tier_name: str, jsonl_path: Path):
    """Load records for a specific tier from the JSONL."""
    if not jsonl_path.exists():
        return []
    recs = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                # Filter by tier name
                if r.get("tier") == tier_name:
                    recs.append(r)
            except Exception:
                pass
    return recs


def compute_stats():
    """Compute unified stats across all tiers."""
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tiers": {},
    }

    for tier_name, jsonl_path in TIER_PATHS.items():
        recs = load_records_for_tier(tier_name, jsonl_path)
        if not recs:
            # For tier3_raw, the variant field is "tier3_raw" but tier is "tier3"
            # Re-read with variant filter
            if jsonl_path.exists():
                with open(jsonl_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            r = json.loads(line)
                            v = r.get("variant") or "standard"
                            if tier_name == "tier3_raw" and v == "tier3_raw":
                                recs.append(r)
                            elif tier_name in ("tier1", "tier2", "tier3") and v == "standard" and r.get("tier") == tier_name:
                                recs.append(r)
                        except Exception:
                            pass

        if not recs:
            print(f"⚠️  No records for {tier_name}")
            continue

        backends = sorted(set(r["backend"] for r in recs))

        tier_stats = {
            "total_records": len(recs),
            "backends": backends,
            "overall": {},
            "per_backend": {},
            "per_backend_family": {},
            "confusion_matrix": defaultdict(lambda: defaultdict(int)),
            "default_guess_rate": {},
        }

        # Overall
        k_total = sum(1 for r in recs if r.get("correct"))
        n_total = len(recs)
        lo, hi = wilson_ci(k_total, n_total)
        tier_stats["overall"] = {
            "k": k_total, "n": n_total,
            "accuracy": round(k_total / n_total, 4) if n_total > 0 else 0,
            "ci_lower": round(lo, 4), "ci_upper": round(hi, 4),
        }

        # Per backend
        for backend in backends:
            brecs = [r for r in recs if r["backend"] == backend]
            k = sum(1 for r in brecs if r.get("correct"))
            n = len(brecs)
            lo, hi = wilson_ci(k, n)

            # Default guess rate: % of blind predictions that are the most common label
            pred_counts = defaultdict(int)
            for r in brecs:
                pred_counts[r.get("parsed_prediction", "UNKNOWN")] += 1
            if pred_counts:
                most_common_pred = max(pred_counts, key=lambda x: pred_counts[x])
                default_rate = pred_counts[most_common_pred] / n
            else:
                most_common_pred = "N/A"
                default_rate = 0

            tier_stats["per_backend"][backend] = {
                "k": k, "n": n,
                "accuracy": round(k / n, 4) if n > 0 else 0,
                "ci_lower": round(lo, 4), "ci_upper": round(hi, 4),
                "avg_latency_s": round(sum(r.get("latency_s", 0) for r in brecs) / max(n, 1), 2),
                "default_guess_label": most_common_pred,
                "default_guess_rate": round(default_rate, 4),
                "errors": sum(1 for r in brecs if r.get("error")),
            }

            # Per backend × family
            for family in FAMILIES:
                frecs = [r for r in brecs if r.get("ground_truth") == family]
                if frecs:
                    kf = sum(1 for r in frecs if r.get("correct"))
                    nf = len(frecs)
                    lo_f, hi_f = wilson_ci(kf, nf)
                    tier_stats["per_backend_family"][f"{backend}|{family}"] = {
                        "k": kf, "n": nf,
                        "accuracy": round(kf / nf, 4),
                        "ci_lower": round(lo_f, 4), "ci_upper": round(hi_f, 4),
                    }

            # Confusion matrix
            for r in brecs:
                gt = r.get("ground_truth", "UNKNOWN")
                pred = r.get("parsed_prediction", "UNKNOWN")
                tier_stats["confusion_matrix"][gt][pred] += 1

        stats["tiers"][tier_name] = tier_stats

    # Compute gaps
    stats["gaps"] = {}
    for backend in stats.get("tiers", {}).get("tier1", {}).get("per_backend", {}):
        t1 = stats["tiers"].get("tier1", {}).get("per_backend", {}).get(backend, {})
        t3 = stats["tiers"].get("tier3", {}).get("per_backend", {}).get(backend, {})
        t4a = stats["tiers"].get("tier4a", {}).get("per_backend", {}).get(backend, {})
        t5 = stats["tiers"].get("tier5", {}).get("per_backend", {}).get(backend, {})

        if t1 and t3:
            gap = t1["accuracy"] - t3["accuracy"]
            # CI on difference (approximate)
            se1 = (t1["ci_upper"] - t1["ci_lower"]) / (2 * 1.96)
            se3 = (t3["ci_upper"] - t3["ci_lower"]) / (2 * 1.96)
            se_diff = math.sqrt(se1**2 + se3**2)
            stats["gaps"][f"{backend}|tier1_vs_tier3"] = {
                "gap": round(gap, 4),
                "ci_lower": round(gap - 1.96 * se_diff, 4),
                "ci_upper": round(gap + 1.96 * se_diff, 4),
            }

        if t3 and t4a:
            gap = t4a["accuracy"] - t3["accuracy"]
            se3 = (t3["ci_upper"] - t3["ci_lower"]) / (2 * 1.96) if t3.get("ci_upper") else 0
            se4a = (t4a["ci_upper"] - t4a["ci_lower"]) / (2 * 1.96) if t4a.get("ci_upper") else 0
            se_diff = math.sqrt(se3**2 + se4a**2)
            stats["gaps"][f"{backend}|tier4a_vs_tier3"] = {
                "gap": round(gap, 4),
                "ci_lower": round(gap - 1.96 * se_diff, 4),
                "ci_upper": round(gap + 1.96 * se_diff, 4),
            }

    return stats


def generate_summary_md(stats: dict) -> str:
    """Generate human-readable markdown summary."""
    lines = []
    lines.append("# ACTS v2 — Unified Live Evaluation Results")
    lines.append(f"\nGenerated: {stats.get('generated_at', 'N/A')}")
    lines.append(f"\nAll tiers: Tier-1 (metadata-rich), Tier-2 (filename-only), "
                 f"Tier-3 (blind stats-only), Tier-3-Raw (blind + raw hex), "
                 f"Tier-4A (tool-augmented blind), Tier-5 (forced CoT reasoning)")

    # Per-tier tables
    for tier_name in ["tier1", "tier2", "tier3", "tier3_raw", "tier4a", "tier5"]:
        tier = stats.get("tiers", {}).get(tier_name)
        if not tier:
            continue

        lines.append(f"\n\n## {tier_name.upper()} — Overall")
        lines.append(f"**Records:** {tier['total_records']}")
        ov = tier["overall"]
        if ov:
            lines.append(f"**Accuracy:** {ov['accuracy']:.1%} (Wilson 95% CI: [{ov['ci_lower']:.1%}, {ov['ci_upper']:.1%}])")

        lines.append(f"\n### Per-Backend")
        lines.append("| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |")
        lines.append("|---------|-----|----------|--------|-------------|---------------|")
        for backend, bv in sorted(tier.get("per_backend", {}).items()):
            default_str = f"{bv['default_guess_label']} ({bv['default_guess_rate']:.0%})"
            lines.append(
                f"| {backend} | {bv['k']}/{bv['n']} "
                f"| {bv['accuracy']:.1%} [{bv['ci_lower']:.1%},{bv['ci_upper']:.1%}] "
                f"| {bv['avg_latency_s']:.1f}s "
                f"| {default_str} |"
            )

    # Gaps
    gaps = stats.get("gaps", {})
    if gaps:
        lines.append("\n\n## Gap Analysis")
        lines.append("| Comparison | Backend | Gap | 95% CI |")
        line3 = "|------------|---------|-----|--------|"
        lines.append(line3)
        for gap_key, gv in sorted(gaps.items()):
            parts = gap_key.split("|")
            backend = parts[0]
            comparison = parts[1] if len(parts) > 1 else gap_key
            lines.append(
                f"| {comparison} "
                f"| {backend} "
                f"| {gv['gap']:.1%} [{gv['ci_lower']:.1%},{gv['ci_upper']:.1%}] |"
            )

    # Confusion matrices
    lines.append("\n\n## Confusion Matrices")
    for tier_name in ["tier1", "tier2", "tier3", "tier4a", "tier5"]:
        tier = stats.get("tiers", {}).get(tier_name)
        if not tier:
            continue
        cm = tier.get("confusion_matrix", {})
        if not cm:
            continue

        lines.append(f"\n### {tier_name.upper()}")
        # Build table
        pred_labels = set()
        for gt_dict in cm.values():
            pred_labels.update(gt_dict.keys())
        pred_labels = sorted(pred_labels)

        header = "| True \\ Pred |" + "".join(f" {p[:8]:<8} |" for p in pred_labels)
        sep = "|" + "---|" * (len(pred_labels) + 1)
        lines.append(header)
        lines.append(sep)
        for gt in FAMILIES + ["UNKNOWN"]:
            row = f"| {gt:<12} |"
            for pred in pred_labels:
                count = cm.get(gt, {}).get(pred, 0)
                row += f" {count:<8} |"
            lines.append(row)

    lines.append("\n\n*CI = Wilson score 95% confidence interval*")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-stats", default=str(WORKSPACE / "stage7_assembly/scaled_results/live_stats_all.json"))
    parser.add_argument("--output-summary", default=str(WORKSPACE / "stage7_assembly/scaled_results/live_summary_all.md"))
    args = parser.parse_args()

    print("📊 Computing unified statistics across all tiers...")
    stats = compute_stats()

    stats_path = Path(args.output_stats)
    summary_path = Path(args.output_summary)
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print(f"   Stats saved to: {stats_path}")

    md = generate_summary_md(stats)
    with open(summary_path, "w") as f:
        f.write(md)
    print(f"   Summary saved to: {summary_path}")

    # Print key results
    print("\n" + "=" * 70)
    for tier_name in ["tier1", "tier2", "tier3", "tier3_raw", "tier4a", "tier5"]:
        tier = stats.get("tiers", {}).get(tier_name)
        if tier and tier.get("overall"):
            ov = tier["overall"]
            print(f"  {tier_name:<12} {ov['k']}/{ov['n']} = {ov['accuracy']:.1%} [{ov['ci_lower']:.1%},{ov['ci_upper']:.1%}]")
    print("=" * 70)


if __name__ == "__main__":
    main()
