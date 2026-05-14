#!/usr/bin/env python3
"""
Tier-4B Tool-Augmented Pipeline + 10-Configuration Ablation Study
Proper 70/30 train-test split with threshold calibration on training data ONLY.
"""

import os
import json
import math
import random
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple, Any

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

random.seed(42)
np.random.seed(42)


def compute_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def compute_chi2(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    expected = length / 256.0
    return sum(((counts.get(i, 0) - expected) ** 2) / expected for i in range(256))


def compute_ngram_entropy(data: bytes, n: int) -> float:
    if len(data) < n:
        return 0.0
    ngrams = Counter(tuple(data[i:i+n]) for i in range(len(data) - n + 1))
    total = sum(ngrams.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in ngrams.values())


def compute_block_entropy_std(data: bytes, block_size: int) -> float:
    if len(data) < block_size:
        return 0.0
    entropies = []
    for i in range(0, len(data) - block_size + 1, block_size):
        block = data[i:i+block_size]
        entropies.append(compute_entropy(block))
    return float(np.std(entropies)) if entropies else 0.0


def compute_runs_test(data: bytes) -> int:
    """Count number of runs (sequences of same byte)."""
    if not data:
        return 0
    runs = 1
    for i in range(1, len(data)):
        if data[i] != data[i-1]:
            runs += 1
    return runs


def compute_serial_correlation(data: bytes) -> float:
    if len(data) < 2:
        return 0.0
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

    # Structural heuristics
    mod8 = size % 8
    mod16 = size % 16
    is_256b = 1 if size == 256 else 0
    is_1088b = 1 if size == 1088 else 0
    size_between_1000_1200 = 1 if 1000 <= size <= 1200 else 0

    return {
        "file_size": size,
        "entropy": entropy,
        "chi2": chi2,
        "bigram_entropy": bigram_ent,
        "trigram_entropy": trigram_ent,
        "block_std_8": block_std_8,
        "block_std_16": block_std_16,
        "runs": runs,
        "serial_corr": serial_corr,
        "max_byte_freq": max_byte_freq,
        "zero_ratio": zero_ratio,
        "ff_ratio": ff_ratio,
        "mod8": mod8,
        "mod16": mod16,
        "is_256b": is_256b,
        "is_1088b": is_1088b,
        "size_1000_1200": size_between_1000_1200,
    }


# Map cipher family names to labels
FAMILY_LABELS = {
    "AES-128": 0, "AES-256": 1, "3DES": 2, "DES": 3,
    "ChaCha20": 4, "RSA-2048": 5, "ML-KEM-768": 6,
}
LABEL_FAMILIES = {v: k for k, v in FAMILY_LABELS.items()}


def load_corpus(corpus_dir: Path, manifest_path: Path) -> Tuple[np.ndarray, np.ndarray, List[str], List[int]]:
    """Load corpus and return feature matrix X, label vector y, filenames, indices."""
    with open(manifest_path) as f:
        manifest = json.load(f)

    samples = manifest["samples"]
    X_list = []
    y_list = []
    filenames = []
    indices = []

    for idx, sample in enumerate(samples):
        fp = corpus_dir / sample["filename"]
        if not fp.exists():
            continue
        feats = extract_features(fp)
        feats_arr = np.array([
            feats["file_size"], feats["entropy"], feats["chi2"],
            feats["bigram_entropy"], feats["trigram_entropy"],
            feats["block_std_8"], feats["block_std_16"],
            feats["runs"], feats["serial_corr"],
            feats["max_byte_freq"], feats["zero_ratio"], feats["ff_ratio"],
            feats["mod8"], feats["mod16"],
            feats["is_256b"], feats["is_1088b"], feats["size_1000_1200"],
        ])
        X_list.append(feats_arr)
        y_list.append(FAMILY_LABELS[sample["cipher_family"]])
        filenames.append(sample["filename"])
        indices.append(idx)

    return np.array(X_list), np.array(y_list), filenames, indices


FEATURE_NAMES = [
    "file_size", "entropy", "chi2", "bigram_entropy", "trigram_entropy",
    "block_std_8", "block_std_16", "runs", "serial_corr",
    "max_byte_freq", "zero_ratio", "ff_ratio",
    "mod8", "mod16", "is_256b", "is_1088b", "size_1000_1200",
]

ABLATION_CONFIGS = {
    "full_pipeline": list(range(len(FEATURE_NAMES))),
    "no_chi2": [i for i, n in enumerate(FEATURE_NAMES) if n != "chi2"],
    "no_entropy": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("entropy", "bigram_entropy", "trigram_entropy")],
    "no_block": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("block_std_8", "block_std_16")],
    "no_bytefreq": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("max_byte_freq", "zero_ratio", "ff_ratio")],
    "entropy_only": [i for i, n in enumerate(FEATURE_NAMES) if n in ("entropy", "bigram_entropy", "trigram_entropy")],
    "chi2_only": [i for i, n in enumerate(FEATURE_NAMES) if n == "chi2"],
    "structural_only": [i for i, n in enumerate(FEATURE_NAMES) if n in ("file_size", "is_256b", "is_1088b", "size_1000_1200", "mod8", "mod16")],
    "no_file_size": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("file_size", "is_256b", "is_1088b", "size_1000_1200")],
    "no_modulo": [i for i, n in enumerate(FEATURE_NAMES) if n not in ("mod8", "mod16")],
}


def run_ablation(
    corpus_dir: Path,
    manifest_path: Path,
    output_path: Path,
    test_size: float = 0.30,
    random_state: int = 42,
) -> Dict[str, Any]:
    print(f"Loading corpus from {corpus_dir}...")
    X, y, filenames, _ = load_corpus(corpus_dir, manifest_path)
    print(f"Loaded {len(y)} samples. Feature dim = {X.shape[1]}")

    # Stratified 70/30 split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    print(f"Train: {len(y_train)}, Test: {len(y_test)}")
    print(f"Train class distribution: {dict(Counter(y_train))}")
    print(f"Test class distribution: {dict(Counter(y_test))}")

    results = {}
    all_configs = []

    for cfg_name, feature_indices in ABLATION_CONFIGS.items():
        print(f"\n{'='*50}")
        print(f"Running ablation config: {cfg_name}")
        print(f"Features used: {[FEATURE_NAMES[i] for i in feature_indices]}")

        X_tr = X_train_s[:, feature_indices]
        X_te = X_test_s[:, feature_indices]

        # Train Random Forest on training data only
        model = RandomForestClassifier(
            n_estimators=200, max_depth=20, random_state=random_state, n_jobs=-1
        )
        model.fit(X_tr, y_train)

        # Evaluate on held-out test data exactly once
        y_pred = model.predict(X_te)
        acc = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred).tolist()
        per_class = {}
        for label_idx in range(7):
            mask = y_test == label_idx
            if mask.sum() > 0:
                per_class[LABEL_FAMILIES[label_idx]] = float(
                    accuracy_score(y_test[mask], y_pred[mask])
                )
            else:
                per_class[LABEL_FAMILIES[label_idx]] = None

        # Feature importances (for full pipeline)
        importances = None
        if cfg_name == "full_pipeline":
            importances = {
                FEATURE_NAMES[i]: float(v)
                for i, v in zip(feature_indices, model.feature_importances_)
            }

        cfg_result = {
            "config_name": cfg_name,
            "features_used": [FEATURE_NAMES[i] for i in feature_indices],
            "n_features": len(feature_indices),
            "test_accuracy": float(acc),
            "per_class_accuracy": per_class,
            "confusion_matrix": cm,
            "feature_importances": importances,
        }
        all_configs.append(cfg_result)
        print(f"Test accuracy: {acc:.4f}")

    # Also run size-only rule-based baseline for completeness
    size_correct = 0
    for xi, yi in zip(X_test, y_test):
        feats = {FEATURE_NAMES[j]: xi[j] for j in range(len(FEATURE_NAMES))}
        pred = None
        if feats["is_256b"] == 1:
            pred = FAMILY_LABELS["RSA-2048"]
        elif feats["is_1088b"] == 1:
            pred = FAMILY_LABELS["ML-KEM-768"]
        else:
            # Random guess among symmetric ciphers
            pred = random.choice([
                FAMILY_LABELS["AES-128"], FAMILY_LABELS["AES-256"],
                FAMILY_LABELS["3DES"], FAMILY_LABELS["DES"], FAMILY_LABELS["ChaCha20"]
            ])
        if pred == yi:
            size_correct += 1
    size_only_acc = size_correct / len(y_test)
    print(f"\nSize-only baseline accuracy: {size_only_acc:.4f}")

    results = {
        "metadata": {
            "corpus_dir": str(corpus_dir),
            "manifest": str(manifest_path),
            "total_samples": len(y),
            "train_samples": len(y_train),
            "test_samples": len(y_test),
            "test_size": test_size,
            "random_state": random_state,
            "scaler": "StandardScaler",
            "model": "RandomForestClassifier(n_estimators=200, max_depth=20)",
        },
        "configs": all_configs,
        "baseline": {
            "size_only_accuracy": float(size_only_acc),
        },
    }

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")
    return results


def main():
    corpus_dir = Path("stage1_data/corpus_mega")
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"Mega corpus not found at {manifest_path}. Trying expanded corpus...")
        corpus_dir = Path("stage1_data/corpus_expanded")
        manifest_path = corpus_dir / "manifest.json"

    output_path = Path("stage4_ablation/results/ablation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = run_ablation(corpus_dir, manifest_path, output_path)

    # Print summary table
    print("\n" + "=" * 70)
    print("ABLATION SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Config':<25} {'Features':>10} {'Test Acc':>12}")
    print("-" * 70)
    for cfg in results["configs"]:
        print(f"{cfg['config_name']:<25} {cfg['n_features']:>10} {cfg['test_accuracy']:>11.2%}")
    print("-" * 70)
    print(f"{'size_only (baseline)':<25} {'1':>10} {results['baseline']['size_only_accuracy']:>11.2%}")


if __name__ == "__main__":
    main()
