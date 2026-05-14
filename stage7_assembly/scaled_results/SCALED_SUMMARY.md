# ACTS v2 — Scaled Statistical Summary
**Corpus:** ultra (7000 files)
**Date:** 2026-05-13T12:46:22.206744+00:00

## Tier-4B Ablation (10 configs, 70/30 held-out)

| Config | Features | Test Accuracy |
|--------|----------|---------------|
| full_pipeline | 17 | 69.81% |
| no_chi2 | 16 | 69.48% |
| no_entropy | 14 | 70.62% |
| no_block | 15 | 70.81% |
| no_bytefreq | 14 | 68.62% |
| entropy_only | 3 | 69.90% |
| chi2_only | 1 | 44.14% |
| structural_only | 6 | 68.05% |
| no_file_size | 13 | 69.38% |
| no_modulo | 15 | 70.10% |
| size_only baseline | 1 | 43.38% |

## Tier-6 Classical ML (5-fold CV)

| Model | Overall Accuracy | Fold Accuracies |
|-------|------------------|-----------------|
| RandomForest | 69.21% | 69.50%, 68.43%, 69.21%, 68.86%, 70.07% |
| LogisticRegression | 56.86% | 56.36%, 57.29%, 58.57%, 55.43%, 56.64% |
| LinearSVM | 55.81% | 54.86%, 56.57%, 57.43%, 54.86%, 55.36% |

## Tier-5 Deterministic Heuristic

| Metric | Value |
|--------|-------|
| Accuracy | 47.23% |
| N | 7000 |
| Mechanism | file-size heuristic + biased AES-128 default for mod16==0 |

## Per-Cipher Accuracy (Tier-4B Full Pipeline)

| Cipher | Accuracy |
|--------|----------|
| AES-128 | 51.00% |
| AES-256 | 50.33% |
| 3DES | 52.33% |
| DES | 45.00% |
| ChaCha20 | 90.33% |
| RSA-2048 | 99.67% |
| ML-KEM-768 | 100.00% |