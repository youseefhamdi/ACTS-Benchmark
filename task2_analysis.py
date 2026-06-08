#!/usr/bin/env python3
"""
Task 2: Per-family accuracy tables + confusion matrices + default guess analysis.
Works with any set of per-record JSONL results.

Usage:
    python3 task2_analysis.py \
        --matrix stage2_execution/results/live_matrix_full_v2.jsonl \
        --tier4a stage2_execution/results/tier4a_full_v2.jsonl \
        --tier5 stage2_execution/results/tier5_live_full_v2.jsonl \
        --output-dir stage7_assembly/scaled_results/
"""

import json
import argparse
import os
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

# Canonical label normalization
LABEL_MAP = {
    "3DES": "3des",
    "3des": "3des",
    "AES-128": "aes-128",
    "aes-128": "aes-128",
    "AES-256": "aes-256",
    "aes-256": "aes-256",
    "DES": "des",
    "des": "des",
    "ChaCha20": "chacha20",
    "chacha20": "chacha20",
    "RSA-2048": "rsa-2048",
    "rsa-2048": "rsa-2048",
    "ML-KEM-768": "ml-kem-768",
    "ml-kem-768": "ml-kem-768",
    "UNKNOWN": "unknown",
    "UNK": "unknown",
}

CANONICAL_LABELS = ["3des", "aes-128", "aes-256", "chacha20", "des", "ml-kem-768", "rsa-2048"]


def normalize(label):
    label = label.strip()
    return LABEL_MAP.get(label, label.lower())


def wilson_ci(k, n, z=1.96):
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p_hat = k / n
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    spread = z * ((p_hat * (1 - p_hat) / n + z * z / (4 * n * n)) ** 0.5) / denom
    lo = max(0.0, center - spread)
    hi = min(1.0, center + spread)
    return (lo, hi)


def load_jsonl(path):
    if not path or not Path(path).exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def compute_per_family(records, tier_name):
    """Per-family accuracy table: family | k/N | acc% | Wilson 95% CI."""
    family_results = defaultdict(list)
    for r in records:
        gt = normalize(r.get("ground_truth", r.get("gt", "")))
        pred = normalize(r.get("parsed_prediction", r.get("prediction", r.get("pred", ""))))
        family_results[gt].append(1 if gt == pred else 0)

    table = []
    for fam in sorted(family_results.keys()):
        results = family_results[fam]
        n = len(results)
        k = sum(results)
        acc = k / n if n > 0 else 0
        lo, hi = wilson_ci(k, n)
        table.append({
            "family": fam,
            "k": k,
            "n": n,
            "accuracy": round(acc * 100, 1),
            "ci_lo": round(lo * 100, 1),
            "ci_hi": round(hi * 100, 1),
        })
    return table


def compute_confusion_matrix(records, tier_name):
    """Confusion matrix: true x predicted."""
    matrix = defaultdict(lambda: defaultdict(int))
    for r in records:
        gt = normalize(r.get("ground_truth", r.get("gt", "")))
        pred = normalize(r.get("parsed_prediction", r.get("prediction", r.get("pred", ""))))
        matrix[gt][pred] += 1

    return matrix


def compute_default_guess(records, tier_name):
    """Default guess analysis: modal prediction per backend."""
    backend_preds = defaultdict(list)
    for r in records:
        backend = r.get("backend", "unknown")
        pred = normalize(r.get("parsed_prediction", r.get("prediction", r.get("pred", ""))))
        backend_preds[backend].append(pred)

    result = {}
    for backend, preds in sorted(backend_preds.items()):
        counter = Counter(preds)
        total = len(preds)
        modal_pred, modal_count = counter.most_common(1)[0]
        result[backend] = {
            "modal_prediction": modal_pred,
            "modal_count": modal_count,
            "total": total,
            "modal_share": round(modal_count / total * 100, 1) if total > 0 else 0,
            "distribution": {k: round(v / total * 100, 1) for k, v in counter.most_common()},
        }
    return result


def matrix_to_dict(matrix):
    """Convert nested defaultdict to plain dict for JSON serialization."""
    return {k: dict(v) for k, v in matrix.items()}


def main():
    parser = argparse.ArgumentParser(description="Task 2: Per-family + confusion + default guess")
    parser.add_argument("--matrix", help="Path to main matrix JSONL (T1/T2/T3)")
    parser.add_argument("--tier4a", help="Path to Tier-4A JSONL")
    parser.add_argument("--tier5", help="Path to Tier-5 JSONL")
    parser.add_argument("--output-dir", default="stage7_assembly/scaled_results/")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load all data
    matrix_records = load_jsonl(args.matrix)
    tier4a_records = load_jsonl(args.tier4a)
    tier5_records = load_jsonl(args.tier5)

    # Split matrix into tiers
    tier_records = defaultdict(list)
    for r in matrix_records:
        tier = r.get("tier", "unknown")
        tier_records[tier].append(r)

    all_tiers = {}
    for tier_name, records in tier_records.items():
        all_tiers[tier_name] = records
    if tier4a_records:
        all_tiers["tier4a"] = tier4a_records
    if tier5_records:
        all_tiers["tier5"] = tier5_records

    print("=" * 60)
    print("TASK 2: Per-Family Accuracy + Confusion Matrices + Default Guess")
    print("=" * 60)
    print()

    # 1. Per-family accuracy tables
    print("--- 1. Per-Family Accuracy Tables ---")
    per_family_all = {}
    for tier_name in sorted(all_tiers.keys()):
        records = all_tiers[tier_name]
        table = compute_per_family(records, tier_name)
        per_family_all[tier_name] = table
        print(f"\n{tier_name}:")
        print(f"  {'Family':<14} {'k/N':<10} {'Acc%':<8} {'Wilson 95% CI'}")
        for row in table:
            print(f"  {row['family']:<14} {row['k']}/{row['n']:<8} {row['accuracy']:<8.1f} [{row['ci_lo']:.1f}%, {row['ci_hi']:.1f}%]")

    # Save per-family
    with open(out_dir / "per_family_accuracy.json", "w") as f:
        json.dump(per_family_all, f, indent=2)
    print(f"\nSaved: {out_dir / 'per_family_accuracy.json'}")

    # 2. Confusion matrices (focus on Tier-3)
    print("\n--- 2. Confusion Matrices ---")
    confusion_all = {}
    for tier_name in sorted(all_tiers.keys()):
        records = all_tiers[tier_name]
        matrix = compute_confusion_matrix(records, tier_name)
        confusion_all[tier_name] = matrix_to_dict(matrix)

        # Also per-backend confusion for tier3
        if "tier3" in tier_name:
            backend_records = defaultdict(list)
            for r in records:
                backend_records[r.get("backend", "unknown")].append(r)
            for backend, brecords in sorted(backend_records.items()):
                bmatrix = compute_confusion_matrix(brecords, f"{tier_name}_{backend}")
                confusion_all[f"{tier_name}_{backend}"] = matrix_to_dict(bmatrix)

    # Save confusion matrices
    confusion_path = out_dir / "confusion_matrices.json"
    with open(confusion_path, "w") as f:
        json.dump(confusion_all, f, indent=2)
    print(f"Saved: {confusion_path}")

    # Print Tier-3 confusion (pooled)
    if "tier3" in confusion_all:
        print("\nTier-3 Confusion Matrix (pooled):")
        matrix = confusion_all["tier3"]
        labels = sorted(set(list(matrix.keys()) + [v for d in matrix.values() for v in d.keys()]))
        header = "True\\Pred  " + "  ".join(f"{l:<10}" for l in labels)
        print(header)
        for true_label in labels:
            row_counts = []
            for pred_label in labels:
                count = matrix.get(true_label, {}).get(pred_label, 0)
                row_counts.append(f"{count:<10}")
            print(f"  {true_label:<10} " + "  ".join(row_counts))

    # 3. Default guess analysis
    print("\n--- 3. Default Guess Analysis ---")
    default_guess_all = {}
    for tier_name in sorted(all_tiers.keys()):
        records = all_tiers[tier_name]
        dg = compute_default_guess(records, tier_name)
        default_guess_all[tier_name] = dg
        print(f"\n{tier_name}:")
        for backend, info in sorted(dg.items()):
            print(f"  {backend}: modal={info['modal_prediction']} ({info['modal_count']}/{info['total']} = {info['modal_share']}%)")
            print(f"    distribution: {info['distribution']}")

    # Save default guess
    dg_path = out_dir / "default_guess_rates.json"
    with open(dg_path, "w") as f:
        json.dump(default_guess_all, f, indent=2)
    print(f"\nSaved: {dg_path}")

    # 4. Label normalization report
    print("\n--- 4. Label Normalization ---")
    all_raw_labels = set()
    for records in all_tiers.values():
        for r in records:
            all_raw_labels.add(r.get("ground_truth", r.get("gt", "")))
            all_raw_labels.add(r.get("prediction", r.get("pred", "")))

    fixes = []
    for label in sorted(all_raw_labels):
        normalized = normalize(label)
        if label != normalized:
            fixes.append({"original": label, "normalized": normalized})

    if fixes:
        print(f"  {len(fixes)} label fixes applied:")
        for fix in fixes:
            print(f"    '{fix['original']}' -> '{fix['normalized']}'")
    else:
        print("  No label fixes needed — all labels already normalized.")

    norm_report = {
        "fixes": fixes,
        "canonical_labels": CANONICAL_LABELS,
    }
    with open(out_dir / "label_normalization.json", "w") as f:
        json.dump(norm_report, f, indent=2)

    print("\n" + "=" * 60)
    print("TASK 2 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
