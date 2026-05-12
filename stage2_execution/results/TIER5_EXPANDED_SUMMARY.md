# Tier-5 Expanded Corpus Summary Report

## Overview

This report compares the deterministic heuristic classifier's behavior on the original 140-file corpus versus the expanded 700-file corpus, answering the key scaling question:

> **Does the 44--51% bias-swing range hold at scale?**

## Key Findings

| Metric | Original (140) | Expanded (700) | Change |
|--------|----------------|----------------|--------|
| Total Files | 140 | 700 | +500 (5x) |
| Theoretical Size-Only Maximum | 32.14% | 32.00% | -0.14pp |
| Bias-Swing Minimum | 44.29% | 44.43% | +0.14pp |
| Bias-Swing Maximum | 51.43% | 51.43% | +0.00pp |
| Bias-Swing Span | 7.14pp | 7.00pp | 0.14pp |

## Overall Accuracy Per Variant

| Variant | Original (140) | Expanded (700) |
|---------|----------------|----------------|
| **Default (AES-128 bias)** | 51.4286% | 51.4286% |
| **AES-256 bias** | 50.0000% | 49.8571% |
| **ChaCha20 bias** | 51.4286% | 51.4286% |
| **3DES bias** | 50.0000% | 50.1429% |
| **DES bias** | 44.2857% | 44.4286% |

## Per-Cipher Accuracy Tables

### Expanded Corpus (700 files) -- Default (AES-128 bias)

| Cipher | Accuracy (700) |
|--------|---------------|
| AES-128 | 100.0% |
| AES-256 | 11.0% |
| 3DES | 40.0% |
| DES | 9.0% |
| ChaCha20 | 0.0% |
| RSA-2048 | 100.0% |
| ML-KEM-768 | 100.0% |

### Comparison: Default Variant Per-Cipher Accuracy

| Cipher | Original (140) | Expanded (700) | Difference |
|--------|---------------|----------------|------------|
| AES-128 | 100.0% | 100.0% | +0.0pp |
| AES-256 | 10.0% | 11.0% | +1.0pp |
| 3DES | 40.0% | 40.0% | +0.0pp |
| DES | 10.0% | 9.0% | -1.0pp |
| ChaCha20 | 0.0% | 0.0% | +0.0pp |
| RSA-2048 | 100.0% | 100.0% | +0.0pp |
| ML-KEM-768 | 100.0% | 100.0% | +0.0pp |

## Size Distribution (Expanded Corpus)

| File Size | Count | Is Unique? |
|-----------|-------|------------|
| 1032 | 24 | No |
| 1040 | 61 | No |
| 1056 | 35 | No |
| 1088 | 100 | Yes |
| 2056 | 21 | No |
| 2064 | 28 | No |
| 2080 | 16 | No |
| 256 | 100 | Yes |
| 264 | 4 | Yes |
| 272 | 67 | No |
| 288 | 15 | No |
| 4104 | 9 | Yes |
| 4112 | 81 | No |
| 4128 | 11 | Yes |
| 520 | 25 | No |
| 528 | 64 | No |
| 544 | 39 | No |

## Unique-Size Identifiability (Expanded Corpus)

| Cipher | Identifiable | Total | Rate |
|--------|-------------|-------|------|
| AES-128 | 0 | 100 | 0.0% |
| AES-256 | 11 | 100 | 11.0% |
| 3DES | 4 | 100 | 4.0% |
| DES | 9 | 100 | 9.0% |
| ChaCha20 | 0 | 100 | 0.0% |
| RSA-2048 | 100 | 100 | 100.0% |
| ML-KEM-768 | 100 | 100 | 100.0% |

## Conclusion

**The bias-swing range holds at scale.**

When scaling from 140 to 700 files (5x), the key metrics remain virtually unchanged:

- The **theoretical size-only maximum** stays at ~32% (32.14% original vs 32.00% expanded).
- The **bias-swing range** remains approximately **44-51%** (44.43%-51.43% expanded vs original range).
- The **span** (max-min) is **7.00 percentage points**, slightly *narrower* than the original's wider range.

This demonstrates that the heuristic's ceiling is fundamentally bounded by information-theoretic limits, not by sample size. The 51.4% ceiling from the original 140-file corpus generalizes directly to the expanded corpus, confirming that the result is not an artifact of small sample size.

The classifier gains exactly zero signal from increased corpus size because the determining factor -- file size over the 17 size classes -- is invariant. With 200/700 files at uniquely identifiable sizes (RSA-2048 at 256B, ML-KEM-768 at 1088B), and the remaining 500 files distributed across 12 ambiguous size classes, the deterministic heuristic's performance is capped regardless of how many samples are drawn.

---

*Generated: 2026-05-10 18:44:13 UTC*
*Corpus: 140 files (original) -> 700 files (expanded)*
