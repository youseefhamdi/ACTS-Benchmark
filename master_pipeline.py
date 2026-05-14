#!/usr/bin/env python3
"""
ACTS v2 — MASTER INTEGRATED PIPELINE
Runs ALL experiments on a given corpus and regenerates ALL summary files.
Usage: python3 master_pipeline.py --corpus stage1_data/corpus_ultra
"""

import os
import sys
import json
import math
import random
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, confusion_matrix
import warnings
warnings.filterwarnings("ignore")

random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# Feature extraction (shared)
# ---------------------------------------------------------------------------

def compute_entropy(data: bytes) -> float:
    if not data: return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def compute_chi2(data: bytes) -> float:
    if not data: return 0.0
    counts = Counter(data)
    length = len(data)
    expected = length / 256.0
    return sum(((counts.get(i, 0) - expected) ** 2) / expected for i in range(256))


def compute_ngram_entropy(data: bytes, n: int) -> float:
    if len(data) < n: return 0.0
    ngrams = Counter(tuple(data[i:i+n]) for i in range(len(data) - n + 1))
    total = sum(ngrams.values())
    if total == 0: return 0.0
    return -sum((c / total) * math.log2(c / total) for c in ngrams.values())


def compute_block_entropy_std(data: bytes, block_size: int) -> float:
    if len(data) < block_size: return 0.0
    entropies = []
    for i in range(0, len(data) - block_size + 1, block_size):
        block = data[i:i+block_size]
        entropies.append(compute_entropy(block))
    return float(np.std(entropies)) if entropies else 0.0


def compute_runs_test(data: bytes) -> int:
    if not data: return 0
    runs = 1
    for i in range(1, len(data)):
        if data[i] != data[i-1]: runs += 1
    return runs


def compute_serial_correlation(data: bytes) -> float:
    if len(data) < 2: return 0.0
    n = len(data)
    mean = sum(data) / n
    numerator = sum((data[i] - mean) * (data[i+1] - mean) for i in range(n - 1))
    denominator = sum((b - mean) ** 2 for b in data)
    return numerator / denominator if denominator else 0.0


def extract_features(filepath: Path) -> Dict[str, Any]:
    with open(filepath, "rb") as f:
        data = f.read()
    size = len(data)
    entropy = compute_entropy(data)
    chi2 = compute_chi2(data)
    bigram_ent = compute_ngram_entropy(data, 2)
    trigram_ent = compute_ngram_entropy(data, 3)
    block_std_8 = compute_block_entropy_std(data, 8)
    block_std_16 = compute_block_entropy_std(data, 16)
    runs = compute_runs_test(data)
    serial_corr = compute_serial_correlation(data)
    byte_counts = Counter(data)
    max_byte_freq = max(byte_counts.values()) / size if size else 0
    zero_ratio = byte_counts.get(0, 0) / size if size else 0
    ff_ratio = byte_counts.get(0xFF, 0) / size if size else 0
    mod8 = size % 8
    mod16 = size % 16
    is_256b = 1 if size == 256 else 0
    is_1088b = 1 if size == 1088 else 0
    size_1000_1200 = 1 if 1000 <= size <= 1200 else 0

    return {
        "file_size": size, "entropy": entropy, "chi2": chi2,
        "bigram_entropy": bigram_ent, "trigram_entropy": trigram_ent,
        "block_std_8": block_std_8, "block_std_16": block_std_16,
        "runs": runs, "serial_corr": serial_corr,
        "max_byte_freq": max_byte_freq, "zero_ratio": zero_ratio, "ff_ratio": ff_ratio,
        "mod8": mod8, "mod16": mod16,
        "is_256b": is_256b, "is_1088b": is_1088b, "size_1000_1200": size_1000_1200,
    }


FEATURE_NAMES = [
    "file_size", "entropy", "chi2", "bigram_entropy", "trigram_entropy",
    "block_std_8", "block_std_16", "runs", "serial_corr",
    "max_byte_freq", "zero_ratio", "ff_ratio",
    "mod8", "mod16", "is_256b", "is_1088b", "size_1000_1200",
]

FAMILY_LABELS = {
    "AES-128": 0, "AES-256": 1, "3DES": 2, "DES": 3,
    "ChaCha20": 4, "RSA-2048": 5, "ML-KEM-768": 6,
}
LABEL_FAMILIES = {v: k for k, v in FAMILY_LABELS.items()}


# ---------------------------------------------------------------------------
# Load corpus
# ---------------------------------------------------------------------------

def load_corpus(corpus_dir: Path, manifest_path: Path):
    with open(manifest_path) as f:
        manifest = json.load(f)

    X_list, y_list, filenames = [], [], []
    for sample in manifest["samples"]:
        fp = corpus_dir / sample["filename"]
        if not fp.exists():
            continue
        feats = extract_features(fp)
        feats_arr = np.array([feats[n] for n in FEATURE_NAMES])
        X_list.append(feats_arr)
        y_list.append(FAMILY_LABELS[sample["cipher_family"]])
        filenames.append(sample["filename"])

    return np.array(X_list), np.array(y_list), filenames, manifest


# ---------------------------------------------------------------------------
# Tier-4B Ablation (10 configs, 70/30 split)
# ---------------------------------------------------------------------------

ABLATION_CONFIGS = {
    "full_pipeline": list(range(len(FEATURE_NAMES))),
    "no_chi2": [i for i, n in enumerate(FEATURE_NAMES) if n != "chi2"],
    "no_entropy": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("entropy", "bigram_entropy", "trigram_entropy")],
    "no_block": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("block_std_8", "block_std_16")],
    "no_bytefreq": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("max_byte_freq", "zero_ratio", "ff_ratio")],
    "entropy_only": [i for i, n in enumerate(FEATURE_NAMES) if n in ("entropy", "bigram_entropy", "trigram_entropy")],
    "chi2_only": [i for i, n in enumerate(FEATURE_NAMES) if n == "chi2"],
    "structural_only": [i for i, n in enumerate(FEATURE_NAMES) if n in ("file_size", "mod8", "mod16", "is_256b", "is_1088b", "size_1000_1200")],
    "no_file_size": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("file_size", "is_256b", "is_1088b", "size_1000_1200")],
    "no_modulo": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("mod8", "mod16")],
}


def run_ablation(X, y, test_size=0.30, random_state=42):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    configs = []
    for cfg_name, feature_indices in ABLATION_CONFIGS.items():
        X_tr = X_train_s[:, feature_indices]
        X_te = X_test_s[:, feature_indices]

        model = RandomForestClassifier(
            n_estimators=200, max_depth=20, random_state=random_state, n_jobs=-1
        )
        model.fit(X_tr, y_train)
        y_pred = model.predict(X_te)
        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred).tolist()

        per_class = {}
        for label_idx in range(7):
            mask = y_test == label_idx
            if mask.sum() > 0:
                per_class[LABEL_FAMILIES[label_idx]] = float(accuracy_score(y_test[mask], y_pred[mask]))

        importances = None
        if cfg_name == "full_pipeline":
            importances = {FEATURE_NAMES[i]: float(v) for i, v in zip(feature_indices, model.feature_importances_)}

        configs.append({
            "config_name": cfg_name,
            "features_used": [FEATURE_NAMES[i] for i in feature_indices],
            "n_features": len(feature_indices),
            "test_accuracy": float(acc),
            "per_class_accuracy": per_class,
            "confusion_matrix": cm,
            "feature_importances": importances,
        })
        print(f"  {cfg_name}: {acc:.4f}")

    # Size-only baseline
    size_correct = 0
    for xi, yi in zip(X_test, y_test):
        feats = {FEATURE_NAMES[j]: xi[j] for j in range(len(FEATURE_NAMES))}
        pred = None
        if feats["is_256b"] == 1:
            pred = FAMILY_LABELS["RSA-2048"]
        elif feats["is_1088b"] == 1:
            pred = FAMILY_LABELS["ML-KEM-768"]
        else:
            pred = random.choice([
                FAMILY_LABELS["AES-128"], FAMILY_LABELS["AES-256"],
                FAMILY_LABELS["3DES"], FAMILY_LABELS["DES"], FAMILY_LABELS["ChaCha20"]
            ])
        if pred == yi:
            size_correct += 1
    size_only_acc = size_correct / len(y_test)

    return {
        "metadata": {
            "train_samples": len(y_train),
            "test_samples": len(y_test),
            "test_size": test_size,
            "model": "RandomForestClassifier(n_estimators=200, max_depth=20)",
            "scaler": "StandardScaler",
        },
        "configs": configs,
        "baseline": {"size_only_accuracy": float(size_only_acc)},
    }


# ---------------------------------------------------------------------------
# Tier-6 Classical ML (5-fold CV)
# ---------------------------------------------------------------------------

def run_tier6(X, y):
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    models = {
        "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1),
        "LogisticRegression": LogisticRegression(max_iter=10000, random_state=42),
        "LinearSVM": SVC(kernel="linear", probability=False, random_state=42),
    }

    results = {}
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    for mname, model in models.items():
        accs = []
        fold_preds, fold_true = [], []
        importances = None

        for train_idx, test_idx in skf.split(X_scaled, y):
            X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            accs.append(accuracy_score(y_test, preds))
            fold_preds.extend(preds.tolist())
            fold_true.extend(y_test.tolist())
            if hasattr(model, "feature_importances_") and importances is None:
                importances = {n: float(v) for n, v in zip(FEATURE_NAMES, model.feature_importances_)}

        overall = accuracy_score(fold_true, fold_preds)
        cm = confusion_matrix(fold_true, fold_preds).tolist()

        per_class = {}
        for label_idx in range(7):
            mask = np.array(fold_true) == label_idx
            if mask.sum() > 0:
                per_class[LABEL_FAMILIES[label_idx]] = float(accuracy_score(np.array(fold_true)[mask], np.array(fold_preds)[mask]))

        results[mname] = {
            "overall_accuracy": float(overall),
            "fold_accuracies": [float(a) for a in accs],
            "per_class_accuracy": per_class,
            "confusion_matrix": cm,
            "feature_importances": importances,
        }
        print(f"  {mname}: {overall:.4f} (folds: {[f'{a:.3f}' for a in accs]})")

    return results


# ---------------------------------------------------------------------------
# Tier-5 Deterministic Heuristic on full corpus
# ---------------------------------------------------------------------------

def run_tier5(X, y, filenames):
    """Deterministic size-based heuristic."""
    correct = 0
    per_class = {f: {"correct": 0, "total": 0} for f in FAMILY_LABELS}

    for xi, yi, fn in zip(X, y, filenames):
        feats = {FEATURE_NAMES[j]: xi[j] for j in range(len(FEATURE_NAMES))}
        pred = None
        if feats["is_256b"] == 1:
            pred = FAMILY_LABELS["RSA-2048"]
        elif feats["is_1088b"] == 1:
            pred = FAMILY_LABELS["ML-KEM-768"]
        elif feats["mod16"] == 0:
            pred = FAMILY_LABELS["AES-128"]  # biased default
        else:
            pred = random.choice(list(FAMILY_LABELS.values()))

        true_family = LABEL_FAMILIES[yi]
        if pred == yi:
            correct += 1
            per_class[true_family]["correct"] += 1
        per_class[true_family]["total"] += 1

    acc = correct / len(y)
    per_class_acc = {f: (v["correct"] / v["total"] if v["total"] > 0 else 0) for f, v in per_class.items()}

    return {
        "accuracy": float(acc),
        "per_class_accuracy": per_class_acc,
        "n": len(y),
        "mechanism": "file-size heuristic + biased AES-128 default for mod16==0",
    }


# ---------------------------------------------------------------------------
# Wilson CI helper
# ---------------------------------------------------------------------------

def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    if n == 0: return (0.0, 0.0)
    p = successes / n
    z = 1.96  # approx for 95%
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


# ---------------------------------------------------------------------------
# Regenerate all summary files
# ---------------------------------------------------------------------------

def regenerate_summaries(corpus_label: str, ablation: dict, tier6: dict, tier5: dict,
                         output_dir: Path, n_total: int):
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. MASTER_RESULTS_V2.json
    full_cfg = next(c for c in ablation["configs"] if c["config_name"] == "full_pipeline")

    master = {
        "metadata": {
            "project": "ACTS v2 Major Revision (ESWA-D-26-11044R1)",
            "date": datetime.now(timezone.utc).isoformat(),
            "corpus_label": corpus_label,
            "total_samples": n_total,
            "single_source_of_truth": True,
        },
        "datasets": {corpus_label: {"files": n_total, "per_family": n_total // 7}},
        "tier4b_ablation": {
            "corpus": corpus_label,
            "split": "70/30 stratified",
            "train_samples": ablation["metadata"]["train_samples"],
            "test_samples": ablation["metadata"]["test_samples"],
            "configs": [
                {
                    "name": c["config_name"],
                    "accuracy": c["test_accuracy"],
                    "n_features": c["n_features"],
                }
                for c in ablation["configs"]
            ],
            "baseline": ablation["baseline"],
        },
        "tier6_classical_ml": {
            "corpus": corpus_label,
            "method": "5-fold stratified CV",
            "models": {
                k: {
                    "overall_accuracy": v["overall_accuracy"],
                    "fold_accuracies": v["fold_accuracies"],
                }
                for k, v in tier6.items()
            },
        },
        "tier5_deterministic": tier5,
    }
    with open(output_dir / "MASTER_RESULTS_SCALED.json", "w") as f:
        json.dump(master, f, indent=2)

    # 2. Update GROUND_TRUTH.json (merge dataset counts)
    gt_path = Path("GROUND_TRUTH.json")
    if gt_path.exists():
        with open(gt_path) as f:
            gt = json.load(f)
        gt["dataset_ultra_files"] = n_total
        gt["dataset_ultra_per_family"] = {f.lower().replace("-", ""): n_total // 7 for f in FAMILY_LABELS}
        gt["tier4b_ablation"] = ablation
        gt["tier6_ultra"] = tier6
        gt["tier5_ultra"] = tier5
        with open(gt_path, "w") as f:
            json.dump(gt, f, indent=2)

    # 3. FINAL_RESULTS_SUMMARY.json
    final_summary = {
        "metadata": {
            "project": "ACTS v2 Major Revision (ESWA-D-26-11044R1)",
            "date": datetime.now(timezone.utc).isoformat(),
            "corpus": corpus_label,
            "total_samples": n_total,
        },
        "tier4b_ablation_full_pipeline": {
            "test_accuracy": full_cfg["test_accuracy"],
            "per_class_accuracy": full_cfg.get("per_class_accuracy", {}),
        },
        "tier6_best_model": {
            "name": "RandomForest",
            "accuracy": tier6["RandomForest"]["overall_accuracy"],
        },
        "tier5_deterministic": {
            "accuracy": tier5["accuracy"],
            "per_class": tier5["per_class_accuracy"],
        },
    }
    with open(output_dir / "FINAL_RESULTS_SCALED.json", "w") as f:
        json.dump(final_summary, f, indent=2)

    # 4. Statistical summary markdown
    md_lines = [
        "# ACTS v2 — Scaled Statistical Summary",
        f"**Corpus:** {corpus_label} ({n_total} files)",
        f"**Date:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Tier-4B Ablation (10 configs, 70/30 held-out)",
        "",
        "| Config | Features | Test Accuracy |",
        "|--------|----------|---------------|",
    ]
    for c in ablation["configs"]:
        md_lines.append(f"| {c['config_name']} | {c['n_features']} | {c['test_accuracy']:.2%} |")
    md_lines.append(f"| size_only baseline | 1 | {ablation['baseline']['size_only_accuracy']:.2%} |")

    md_lines.extend([
        "",
        "## Tier-6 Classical ML (5-fold CV)",
        "",
        "| Model | Overall Accuracy | Fold Accuracies |",
        "|-------|------------------|-----------------|",
    ])
    for k, v in tier6.items():
        folds = ", ".join(f"{a:.2%}" for a in v["fold_accuracies"])
        md_lines.append(f"| {k} | {v['overall_accuracy']:.2%} | {folds} |")

    md_lines.extend([
        "",
        "## Tier-5 Deterministic Heuristic",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Accuracy | {tier5['accuracy']:.2%} |",
        f"| N | {tier5['n']} |",
        f"| Mechanism | {tier5['mechanism']} |",
        "",
        "## Per-Cipher Accuracy (Tier-4B Full Pipeline)",
        "",
        "| Cipher | Accuracy |",
        "|--------|----------|",
    ])
    for fam, acc in full_cfg.get("per_class_accuracy", {}).items():
        md_lines.append(f"| {fam} | {acc:.2%} |")

    with open(output_dir / "SCALED_SUMMARY.md", "w") as f:
        f.write("\n".join(md_lines))

    print(f"\nSummary files written to {output_dir}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="stage1_data/corpus_ultra", help="Path to corpus directory")
    parser.add_argument("--label", default="ultra", help="Label for this corpus run")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus)
    manifest_path = corpus_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}")
        print("Trying mega corpus fallback...")
        corpus_dir = Path("stage1_data/corpus_mega")
        manifest_path = corpus_dir / "manifest.json"
        if not manifest_path.exists():
            print(f"ERROR: Also not found at {manifest_path}")
            sys.exit(1)
        args.label = "mega"

    print("=" * 60)
    print(f"ACTS v2 MASTER PIPELINE — Corpus: {args.label}")
    print("=" * 60)

    # Load
    print(f"\n[1/4] Loading corpus from {corpus_dir}...")
    X, y, filenames, manifest = load_corpus(corpus_dir, manifest_path)
    n_total = len(y)
    print(f"Loaded {n_total} samples. Features: {X.shape[1]}")

    # Tier-4B Ablation
    print(f"\n[2/4] Running Tier-4B Ablation (10 configs, 70/30 split)...")
    ablation = run_ablation(X, y)

    # Tier-6
    print(f"\n[3/4] Running Tier-6 Classical ML (5-fold CV)...")
    tier6 = run_tier6(X, y)

    # Tier-5
    print(f"\n[4/4] Running Tier-5 Deterministic Heuristic...")
    tier5 = run_tier5(X, y, filenames)

    # Regenerate all summaries
    print(f"\n[5/5] Regenerating summary files...")
    output_dir = Path("stage7_assembly/scaled_results")
    regenerate_summaries(args.label, ablation, tier6, tier5, output_dir, n_total)

    # Save raw results
    raw_output = {
        "metadata": {"corpus": str(corpus_dir), "label": args.label, "n_total": n_total,
                     "generated_at": datetime.now(timezone.utc).isoformat()},
        "ablation": ablation,
        "tier6": tier6,
        "tier5": tier5,
    }
    raw_path = output_dir / "raw_results.json"
    with open(raw_path, "w") as f:
        json.dump(raw_output, f, indent=2)

    print(f"\nRaw results saved to {raw_path}")
    print("=" * 60)
    print("ALL DONE.")
    print("=" * 60)


if __name__ == "__main__":
    main()
