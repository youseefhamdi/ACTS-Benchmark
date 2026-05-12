#!/usr/bin/env python3
"""
Tier-6 Feature Extractor — ACTS v2
==================================
Extracts 30+ statistical features from each ciphertext file.
Used to test whether classical statistical fingerprinting outperforms LLMs.

Output: stage2_execution/results/tier6_features_expanded.csv
"""

import json, sys, math, itertools
from pathlib import Path
from collections import Counter
import csv


def compute_entropy(data: bytes) -> float:
    n = len(data)
    if n == 0:
        return 0.0
    counts = Counter(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def compute_chi2(data: bytes) -> float:
    n = len(data)
    if n == 0:
        return 0.0
    expected = n / 256.0
    counts = Counter(data)
    return sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))


def byte_mean(data: bytes) -> float:
    return sum(data) / len(data) if data else 0.0


def byte_variance(data: bytes) -> float:
    n = len(data)
    if n < 2:
        return 0.0
    mean = byte_mean(data)
    return sum((b - mean) ** 2 for b in data) / n


def byte_skewness(data: bytes) -> float:
    n = len(data)
    if n < 3:
        return 0.0
    mean = byte_mean(data)
    var = byte_variance(data)
    if var == 0:
        return 0.0
    return (sum((b - mean) ** 3 for b in data) / n) / (var ** 1.5)


def byte_kurtosis(data: bytes) -> float:
    n = len(data)
    if n < 4:
        return 0.0
    mean = byte_mean(data)
    var = byte_variance(data)
    if var == 0:
        return 0.0
    return (sum((b - mean) ** 4 for b in data) / n) / (var ** 2) - 3.0


def serial_correlation(data: bytes) -> float:
    n = len(data)
    if n < 2:
        return 0.0
    s0 = sum(data)
    s1 = sum(b * b for b in data)
    s2 = sum(data[i] * data[i + 1] for i in range(n - 1))
    s3 = s0 * s0 / n
    denom = s1 - s3
    if denom == 0:
        return -1.0 / (n - 1)
    return (n * s2 - s0 * s0) / (n * denom)


def ngram_entropy(data: bytes, n: int = 2) -> float:
    if len(data) < n:
        return 0.0
    grams = [tuple(data[i:i + n]) for i in range(len(data) - n + 1)]
    counts = Counter(grams)
    total = len(grams)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def runs_test(data: bytes) -> tuple:
    """Wald-Wolfowitz runs test on above/below median (adapted for bytes)."""
    if len(data) < 2:
        return 0, 1.0
    median = 127.5
    above = sum(1 for b in data if b > median)
    below = len(data) - above
    if above == 0 or below == 0:
        return len(data), 0.0
    runs = 1
    for i in range(1, len(data)):
        if (data[i] > median) != (data[i - 1] > median):
            runs += 1
    expected = (2.0 * above * below) / len(data) + 1.0
    var = (expected - 1) * (expected - 2) / (len(data) - 1)
    if var == 0:
        z = 0.0
    else:
        z = (runs - expected) / math.sqrt(var)
    return runs, z


def block_entropy_std(data: bytes, block_size: int = 16) -> float:
    """Standard deviation of per-block entropy. AES blocks may show lower entropy variance."""
    entropies = []
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        if len(block) < 2:
            continue
        counts = Counter(block)
        e = -sum((c / len(block)) * math.log2(c / len(block)) for c in counts.values())
        entropies.append(e)
    if len(entropies) < 2:
        return 0.0
    mean = sum(entropies) / len(entropies)
    return math.sqrt(sum((e - mean) ** 2 for e in entropies) / len(entropies))


def block_mean_std(data: bytes, block_size: int = 16) -> float:
    means = []
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        if len(block) < 2:
            continue
        means.append(sum(block) / len(block))
    if len(means) < 2:
        return 0.0
    mean = sum(means) / len(means)
    return math.sqrt(sum((m - mean) ** 2 for m in means) / len(means))


def top_byte_ratio(data: bytes, k: int = 8) -> float:
    counts = Counter(data)
    top = counts.most_common(k)
    return sum(c for _, c in top) / len(data)


def low_byte_ratio(data: bytes, threshold: int = 16) -> float:
    return sum(1 for b in data if b < threshold) / len(data)


def high_byte_ratio(data: bytes, threshold: int = 240) -> float:
    return sum(1 for b in data if b > threshold) / len(data)


def even_byte_ratio(data: bytes) -> float:
    return sum(1 for b in data if b % 2 == 0) / len(data)


def zero_byte_ratio(data: bytes) -> float:
    return data.count(0) / len(data)


def peak_count(data: bytes) -> int:
    """Count of byte values that appear more than 3x expected frequency."""
    expected = len(data) / 256.0
    return sum(1 for c in Counter(data).values() if c > 3 * expected)


def max_run_length(data: bytes) -> int:
    max_run = 1
    cur = 1
    for i in range(1, len(data)):
        if data[i] == data[i - 1]:
            cur += 1
            max_run = max(max_run, cur)
        else:
            cur = 1
    return max_run


def diff_entropy(data: bytes) -> float:
    """Entropy of adjacent-byte differences. Some ciphers leave structure here."""
    if len(data) < 2:
        return 0.0
    diffs = [(data[i] - data[i - 1]) % 256 for i in range(1, len(data))]
    counts = Counter(diffs)
    n = len(diffs)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def extract_features(filepath: Path) -> dict:
    data = filepath.read_bytes()
    n = len(data)

    entr = compute_entropy(data)
    chi2 = compute_chi2(data)
    runs, runs_z = runs_test(data)

    features = {
        "file_size": n,
        "entropy": entr,
        "chi2": chi2,
        "byte_mean": byte_mean(data),
        "byte_variance": byte_variance(data),
        "byte_skewness": byte_skewness(data),
        "byte_kurtosis": byte_kurtosis(data),
        "serial_corr": serial_correlation(data),
        "bigram_entropy": ngram_entropy(data, 2),
        "trigram_entropy": ngram_entropy(data, 3),
        "runs": runs,
        "runs_z": runs_z,
        "block_entropy_std_16": block_entropy_std(data, 16),
        "block_entropy_std_8": block_entropy_std(data, 8),
        "block_mean_std_16": block_mean_std(data, 16),
        "block_mean_std_8": block_mean_std(data, 8),
        "top8_ratio": top_byte_ratio(data, 8),
        "top16_ratio": top_byte_ratio(data, 16),
        "low_byte_ratio": low_byte_ratio(data),
        "high_byte_ratio": high_byte_ratio(data),
        "even_byte_ratio": even_byte_ratio(data),
        "zero_byte_ratio": zero_byte_ratio(data),
        "peak_count": peak_count(data),
        "max_run_length": max_run_length(data),
        "diff_entropy": diff_entropy(data),
    }
    return features


def main():
    corpus_dir = Path("stage1_data/corpus_expanded")
    manifest_path = corpus_dir / "manifest.json"
    out_dir = Path("stage2_execution/results")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest (flat list in expanded corpus)
    manifest = json.loads(manifest_path.read_text())
    samples = manifest  # manifest is a list, not a dict with "samples" key

    # Define CSV columns based on expanded corpus metadata keys
    base_fields = ["filename", "cipher_family", "code", "target_size", "implementation", "sample_id", "fingerprint"]
    feature_names = list(extract_features(corpus_dir / samples[0]["filename"]).keys())

    rows = []
    for s in samples:
        filepath = corpus_dir / s["filename"]
        features = extract_features(filepath)
        row = {k: s.get(k, "") for k in base_fields}
        row.update(features)
        rows.append(row)

    # Write CSV
    out_csv = out_dir / "tier6_features_expanded.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_fields + feature_names)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(feature_names)} features for {len(rows)} files -> {out_csv}")
    print(f"Features: {feature_names}")


if __name__ == "__main__":
    main()
