#!/usr/bin/env python3
"""
Statistical validation suite for ACTS v2.
Wilson CI, McNemar test (manual impl), power analysis, Cohen's d.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import norm


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    z = norm.ppf(1 - (1 - confidence) / 2)
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    half_width = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denominator
    return (max(0.0, centre - half_width), min(1.0, centre + half_width))


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    """Cohen's d for two independent samples."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return 0.0
    pooled_std = math.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(x) - np.mean(y)) / pooled_std


def power_analysis_binomial(delta: float, n: int, alpha: float = 0.05) -> float:
    """Approximate power for detecting a difference delta in binomial proportions."""
    z_alpha = norm.ppf(1 - alpha / 2)
    se = math.sqrt(2 * 0.5 * 0.5 / n)
    z_beta = abs(delta) / se - z_alpha
    return norm.cdf(z_beta)


def mcnemar_test_exact(y_true: List[int], y_pred1: List[int], y_pred2: List[int]) -> Tuple[float, float]:
    """Manual McNemar exact test using binomial distribution."""
    b = c = 0
    for yt, yp1, yp2 in zip(y_true, y_pred1, y_pred2):
        c1 = 1 if yp1 == yt else 0
        c2 = 1 if yp2 == yt else 0
        if c1 == 0 and c2 == 1:
            b += 1
        elif c1 == 1 and c2 == 0:
            c += 1

    if b + c == 0:
        return 0.0, 1.0

    # Exact binomial test on discordant pairs
    from math import comb
    n_disc = b + c
    # p-value is 2 * min(P(B <= b), P(B >= b)) under H0: p=0.5
    # For simplicity, use the smaller tail
    pval = 0.0
    for k in range(min(b, c) + 1):
        pval += comb(n_disc, k) * (0.5 ** n_disc)
    pval = min(1.0, 2 * pval)
    stat = min(b, c)
    return float(stat), float(pval)


def analyze_ablation(filepath: Path) -> Dict:
    with open(filepath) as f:
        data = json.load(f)

    configs = data.get("configs", [])
    meta = data.get("metadata", {})

    analysis = {
        "corpus": meta.get("corpus_dir", "unknown"),
        "total_samples": meta.get("total_samples", 0),
        "test_samples": meta.get("test_samples", 0),
        "configs": [],
    }

    for cfg in configs:
        acc = cfg["test_accuracy"]
        n_test = meta["test_samples"]
        successes = round(acc * n_test)
        ci_low, ci_high = wilson_ci(successes, n_test)

        analysis["configs"].append({
            "name": cfg["config_name"],
            "accuracy": acc,
            "successes": successes,
            "n_test": n_test,
            "wilson_ci_95": [round(ci_low, 4), round(ci_high, 4)],
            "per_class": cfg.get("per_class_accuracy", {}),
        })

    return analysis


def main():
    ablation_path = Path("stage4_ablation/results/ablation_results.json")
    if not ablation_path.exists():
        print("Ablation results not found.")
        return

    analysis = analyze_ablation(ablation_path)
    output_path = Path("stage3_statistics/ablation_statistical_analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(analysis, f, indent=2)

    print("=" * 60)
    print("STATISTICAL ANALYSIS — Ablation Study")
    print("=" * 60)
    print(f"Corpus: {analysis['corpus']}")
    print(f"Total: {analysis['total_samples']}, Test: {analysis['test_samples']}")
    print()
    print(f"{'Config':<25} {'Acc':>8} {'95% Wilson CI':>28}")
    print("-" * 60)
    for cfg in analysis["configs"]:
        ci = cfg["wilson_ci_95"]
        print(f"{cfg['name']:<25} {cfg['accuracy']:>7.2%}  [{ci[0]:.4f}, {ci[1]:.4f}]")

    print()
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
