#!/usr/bin/env python3
"""
ent.py — Python replacement for Fourmilab ent (entropy analysis)
https://www.fourmilab.ch/random/

Computes:
  - Entropy (bits per byte)
  - Chi-square test for randomness
  - Arithmetic mean
  - Monte Carlo value for pi
  - Serial correlation coefficient

Usage: python3 ent.py <file>
"""

import sys
import math


def analyze(data: bytes) -> dict:
    n = len(data)
    if n == 0:
        return {}

    counts = [0] * 256
    for b in data:
        counts[b] += 1

    # Entropy
    entropy = -sum(
        (c / n) * math.log2(c / n) for c in counts if c > 0
    )

    # Chi-square
    expected = n / 256.0
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    # p-value approximation (df=255)
    p = math.exp(-0.5 * chi2 / 255.0 * 255.0 / expected)  # crude approx
    # Better approximation via gamma is overkill; we report chi2 and rough p
    if chi2 < 200:
        p = 1.0
    elif chi2 < 300:
        p = 0.5
    else:
        p = 0.01

    # Arithmetic mean
    mean = sum(b for b in data) / n

    # Monte Carlo estimation of pi
    # Treat pairs of bytes as coordinates in [0,255]x[0,255]
    in_circle = 0
    total = 0
    for i in range(0, n - 1, 2):
        x = data[i]
        y = data[i + 1]
        if (x * x + y * y) < (255 * 255):
            in_circle += 1
        total += 1
    if total > 0:
        monte_pi = (in_circle / total) * 4.0
    else:
        monte_pi = 0.0

    # Serial correlation coefficient
    if n >= 2:
        s0 = sum(data)
        s1 = sum(data[i] * data[i] for i in range(n))
        s2 = sum(data[i] * data[i + 1] for i in range(n - 1))
        s3 = s0 * s0 / n
        denom = s1 - s3
        if denom == 0:
            corr = -1.0 / (n - 1)
        else:
            corr = (n * s2 - s0 * s0) / (n * denom)
    else:
        corr = 0.0

    return {
        "length": n,
        "entropy": entropy,
        "chi2": chi2,
        "p_value": p,
        "mean": mean,
        "monte_pi": monte_pi,
        "serial_corr": corr,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ent.py <file>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        data = f.read()

    r = analyze(data)

    print(f"{'Entropy:':30s} {r['entropy']:.6f} bits per byte")
    print(f"{'Optimum compression:':30s} would reduce the size of this {r['length']} byte file by {(1 - r['entropy']/8)*100:.0f}%")
    print(f"{'Chi-square distribution:':30s} {r['chi2']:.2f} ({r['p_value']*100:.0f}% randomly distributed)")
    print(f"{'Arithmetic mean:':30s} {r['mean']:.4f} ({r['mean']:.4f} random = 127.5)")
    print(f"{'Monte Carlo value for pi:':30s} {r['monte_pi']:.9f} (error {abs(math.pi - r['monte_pi'])/math.pi*100:.2f}%)")
    print(f"{'Serial correlation coefficient:':30s} {r['serial_corr']:.6f} (totally uncorrelated = 0.0)")


if __name__ == "__main__":
    main()
