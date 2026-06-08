# ACTS v2 — Missing Cells Report
## Read-Only Audit of Tier-1/2/3 Live Inference Coverage

**Date:** 2026-05-31  
**Workspace:** `/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc`

---

## 1. Expected Full Matrix

The full expected live inference matrix is:

```
5 model-backends × 3 tiers × 14 corpus files = 210 cells
```

Where:
- **5 backends**: gemma4:31b-cloud, gpt-oss:120b-cloud, nemotron-3-super:cloud, glm-5.1:cloud, minimax-m2.7:cloud
- **3 tiers**: Tier-1 (metadata-rich), Tier-2 (filename-only), Tier-3 (blind)
- **14 files**: 7 cipher families × 2 implementations (OpenSSL + liboqs)

The 14 corpus files (from `corpus_14_sample_mapping.json`):
1. `aes_128_s000_openssl.bin` → AES-128
2. `aes_128_s010_liboqs.bin` → AES-128
3. `aes_256_s020_openssl.bin` → AES-256
4. `aes_256_s030_liboqs.bin` → AES-256
5. `des_s040_openssl.bin` → DES
6. `des_s050_liboqs.bin` → DES
7. `3des_s060_openssl.bin` → 3DES
8. `3des_s070_liboqs.bin` → 3DES
9. `chacha20_s080_openssl.bin` → ChaCha20
10. `chacha20_s090_liboqs.bin` → ChaCha20
11. `rsa_2048_s100_openssl.bin` → RSA-2048
12. `rsa_2048_s110_liboqs.bin` → RSA-2048
13. `ml_kem_768_s120_openssl.bin` → ML-KEM-768
14. `ml_kem_768_s130_liboqs.bin` → ML-KEM-768

---

## 2. What Actually Exists

### Pilot Scale (7 old files: encrypted_aes.bin etc.)

| Model | File | Tiers Run | Cells | Status |
|---|---|---|---|---|
| gemma4:31b-cloud | gemma4_all_tiers.json | T1+T2+T3 × 7 | 21 | COMPLETE |
| gpt-oss:120b-cloud | gptoss_all_tiers.json | T1+T2+T3 × 7 | 21 | COMPLETE |
| nemotron-3-super:cloud | nemotron_all_tiers.json | T1+T2+T3 × 7 | 21 | COMPLETE |
| glm-5.1:cloud | glm51_all_tiers.json | T1+T2+T3 × 7 | 0 | ALL HTTP 403 |
| minimax-m2.7:cloud | minimax_all_tiers.json | T1+T2+T3 × 7 | 0 | ALL HTTP 403 |

**Pilot total: 63 of 105 cells (42 missing from glm + minimax)**

### Corpus-14 Scale (14 new files)

| Model | File | Tiers Run | Cells | Status |
|---|---|---|---|---|
| gemma4:31b-cloud | gemma4_corpus14.json | T1+T2+T3 × 14 | 42 | COMPLETE |
| gpt-oss:120b-cloud | gptoss_corpus14.json | T1+T2+T3 × 14 | 42 | COMPLETE |
| nemotron-3-super:cloud | nemotron_corpus14_tier3only.json | T3 × 14 only | 14 | PARTIAL (T1+T2 missing) |
| nvidia/nemotron-3-super-120b-a12b:free (OpenRouter) | openrouter_nemotron_super_v2.json | T3 × 14 only | 14 | PARTIAL (T1+T2 missing) |
| glm-5.1:cloud | (never run on corpus-14) | — | 0 | NOT RUN |
| minimax-m2.7:cloud | (never run on corpus-14) | — | 0 | NOT RUN |

**Corpus-14 total: 112 of 210 cells (98 missing)**

---

## 3. Precise Missing Cell Inventory

### From Pilot (7-file) runs — 42 missing cells:

**glm-5.1:cloud** — ALL 21 cells missing:
- Tier-1: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)
- Tier-2: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)
- Tier-3: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)

**minimax-m2.7:cloud** — ALL 21 cells missing:
- Tier-1: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)
- Tier-2: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)
- Tier-3: aes, aes256, des, 3des, chacha20, rsa, ml (7 cells)

### From Corpus-14 (14-file) runs — 98 missing cells:

**nemotron-3-super:cloud** — 28 cells missing (Tier-1 + Tier-2):
- Tier-1: all 14 files (aes_128_s000, aes_128_s010, aes_256_s020, aes_256_s030, des_s040, des_s050, 3des_s060, 3des_s070, chacha20_s080, chacha20_s090, rsa_2048_s100, rsa_2048_s110, ml_kem_768_s120, ml_kem_768_s130)
- Tier-2: all 14 files (same list)

**openrouter nemotron (nvidia/nemotron-3-super-120b-a12b:free)** — 28 cells missing (Tier-1 + Tier-2):
- Tier-1: all 14 files
- Tier-2: all 14 files

**glm-5.1:cloud** — 42 cells missing (never run on corpus-14):
- Tier-1: all 14 files
- Tier-2: all 14 files
- Tier-3: all 14 files

**minimax-m2.7:cloud** — 42 cells missing (never run on corpus-14):
- Tier-1: all 14 files
- Tier-2: all 14 files
- Tier-3: all 14 files

---

## 4. The "12 of 28 Missing" from the Paper

The paper states "43% Tier-1 missing (12 of 28 queries)". This refers to the ORIGINAL pilot design:

```
4 model-backends × 7 families = 28 Tier-1 queries
```

The 4 backends in the original design were likely: gemma4, gptoss, nemotron, and one more (possibly glm or minimax). With 2 models failing (glm + minimax), that's 2 × 7 = 14 missing cells, which is 50% of 28. The paper's "12 of 28" (43%) is slightly different — it may reflect that some queries were partially completed before the 403 errors, or the count refers to a specific subset of the 28.

---

## 5. Summary Table

| Metric | Value |
|---|---|
| Total expected cells (5 × 3 × 14) | 210 |
| Total actual cells | 112 |
| Total missing cells | 98 |
| Coverage | 53.3% |
| Models with full coverage | 2 (gemma4, gptoss) |
| Models with partial coverage | 2 (nemotron-ollama, nemotron-openrouter) — T3 only |
| Models with zero coverage | 2 (glm-5.1, minimax-m2.7) — HTTP 403 |

---

## 6. Additional Notes

### raw_results.json does NOT contain Tier-1/2/3 data
The file `stage7_assembly/scaled_results/raw_results.json` contains ONLY:
- Metadata about the ULTRA corpus (7,000 files)
- Tier-4B ablation results (10 configurations with accuracy, confusion matrices, feature importances)

All Tier-1/2/3 live inference results are in separate files under `stage2_execution/results/`.

### Tier-4A has no raw inference data
The Tier-4A accuracy of 41.3% is cited in the rebuttal letter and MASTER_FINDINGS.json, but no raw inference logs, prompt templates, or per-file results for Tier-4A were found in the workspace.

### Tier-5 is deterministic heuristic, not live LLM
Tier-5 results (46.43% accuracy) are from a deterministic 3-rule heuristic (file-size lookup + AES-128 default), NOT from live LLM inference. The three sub-variants (5a CoT, 5b code, 5c self-correct) all returned identical accuracy, confirming deterministic behavior.

### Parsing bug in tier5_runner
The CIPHER_ALIASES dict maps `"3des"` → `"des"` (not `"3DES"`). This means when the model says "3DES", it gets normalized to "des" and compared against ground truth "3DES", causing incorrect classification. This bug affects the gemma4_all_tiers.json results where 3DES tier-1 was marked incorrect despite the model responding "3DES".
