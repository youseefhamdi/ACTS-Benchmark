# Scaling Comparison — ACTS v2 Corpus

## Question

Does the information-theoretic ceiling hold when the corpus scales from 140 → 700+ files?

## Baseline (140 files)

| Metric | Value |
|--------|-------|
| Total files | 140 |
| Theoretical size-only max | 32.14% |
| Tier-5 LLM heuristic (best bias) | 51.43% |
| Tier-5 LLM heuristic (worst bias) | 44.29% |
| Tier-5 LLM heuristic (Claude default) | 51.43% |
| Tier-6 Random Forest | 42.9% |
| RF symmetric cipher accuracy | Random (~20%) |

## Expanded (700 files)

| Metric | Value |
|--------|-------|
| Total files | 700 |
| Theoretical size-only max | 32.00% |
| Tier-5 heuristic (best bias) | 51.43% |
| Tier-5 heuristic (worst bias) | 44.43% |
| Tier-5 heuristic (AES-256 bias) | 49.86% |
| Tier-5 heuristic (ChaCha20 bias) | 51.43% |
| Tier-5 heuristic (3DES bias) | 50.14% |
| Tier-6 Random Forest | *(awaiting tier6-runner)* |
| RF symmetric cipher accuracy | *(awaiting tier6-runner)* |

## Stability Assessment

**The bias-swing range holds at scale.**

- Original span (best - worst): 51.43% - 44.29% = 7.14pp
- Expanded span (best - worst): 51.43% - 44.43% = 7.00pp
- Theoretical max difference: 32.00% - 32.14% = -0.14pp (unchanged)

The 44-51% bias-swing range is **stable** across 5x scale-up. The theoretical maximum stays at ~32% because the determining factor — file size over 17 size classes — is a structural invariant, not a sampling artifact.

## Per-Cipher Accuracy Comparison (Default Variant)

| Cipher | Original (140) | Expanded (700) | Delta |
|--------|---------------|----------------|-------|
| AES-128 | 100.0% | 100.0% | 0.0pp |
| AES-256 | 10.0% | 11.0% | +1.0pp |
| 3DES | 35.0% | 40.0% | +5.0pp |
| DES | 10.0% | 9.0% | -1.0pp |
| ChaCha20 | 0.0% | 0.0% | 0.0pp |
| RSA-2048 | 100.0% | 100.0% | 0.0pp |
| ML-KEM-768 | 100.0% | 100.0% | 0.0pp |

## Conclusion

The information-theoretic ceiling is **stable under scaling**. The deterministic heuristic's performance is bounded by the same structural constraints (17 size classes, with 5 unique and 12 overlapping) regardless of how many samples are drawn. The 51.4% ceiling from the original 140-file corpus generalizes directly to 700 files, confirming the result is not a small-sample artifact.

Tier-6 Random Forest results will be appended once the tier6-runner agent completes.

---

*Generated: 2026-05-10 18:48:41 UTC*
*Corpus: 140 files (original) → 700 files (expanded)*
