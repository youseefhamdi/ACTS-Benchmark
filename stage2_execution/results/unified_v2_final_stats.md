# ACTS v2 — FINAL Results (4 Backends, Pure v2)

**Generated:** 2026-06-02T06:16:09.773703+00:00
**Backends:** 4 (gemma4:31b-cloud, gpt-oss:120b-cloud, nemotron-3-super:cloud, openrouter/owl-alpha)
**Excluded:** minimax-m3:cloud (incomplete: T3 at ~39/140 after 1h+, T4A/T5 not started)
**Total good records:** 3320
**Complete cells:** 20/20

## 1. Coverage Grid

| Backend | tier1 | tier2 | tier3 | tier4a | tier5 |
|---------|--------|--------|--------|--------|--------|
| gemma4:31b-cloud | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) |
| gpt-oss:120b-cloud | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) |
| nemotron-3-super:cloud | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) |
| openrouter/owl-alpha | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) | ✅ (140) |

## 2. Overall Per-Tier Accuracy (Wilson 95% CI)

| Tier | k/N | Accuracy | 95% CI |
|------|-----|----------|--------|
| tier1 | 560/560 | 100.0% | [99.3%, 100.0%] |
| tier2 | 560/560 | 100.0% | [99.3%, 100.0%] |
| tier3 | 173/1080 | 16.0% | [14.0%, 18.3%] |
| tier4a | 80/560 | 14.3% | [11.6%, 17.4%] |
| tier5 | 114/560 | 20.4% | [17.2%, 23.9%] |

## 3. Per-Backend × Tier Accuracy

| Backend | tier1 | tier2 | tier3 | tier4a | tier5 |
|---------|--------|--------|--------|--------|--------|
| gemma4:31b-cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 14% [10%,18%] (38/280) | 15% [10%,22%] (21/140) | 19% [13%,26%] (26/140) |
| gpt-oss:120b-cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 20% [16%,25%] (57/280) | 15% [10%,22%] (21/140) | 14% [9%,21%] (20/140) |
| nemotron-3-super:cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 17% [13%,22%] (41/241) | 14% [9%,21%] (20/140) | 14% [9%,20%] (19/140) |
| openrouter/owl-alpha | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 13% [10%,18%] (37/279) | 13% [8%,19%] (18/140) | 35% [28%,43%] (49/140) |

## 4. Newcombe CI Gaps (vs Tier-3 Blind)

| Backend | Gap | Estimate | 95% Newcombe CI | Significant? |
|---------|-----|----------|-----------------|--------------|
| gemma4:31b-cloud | T1_vs_T3 | 86.4% | [81.2%, 90.0%] | ✅ Yes *** |
| gemma4:31b-cloud | T4A_vs_T3 | 1.4% | [-5.3%, 9.1%] | ❌ No (overlap) |
| gemma4:31b-cloud | T5_vs_T3 | 5.0% | [-2.2%, 13.1%] | ❌ No (overlap) |
| gpt-oss:120b-cloud | T1_vs_T3 | 79.6% | [73.9%, 83.9%] | ✅ Yes *** |
| gpt-oss:120b-cloud | T4A_vs_T3 | -5.4% | [-12.5%, 2.7%] | ❌ No (overlap) |
| gpt-oss:120b-cloud | T5_vs_T3 | -6.1% | [-13.1%, 1.9%] | ❌ No (overlap) |
| nemotron-3-super:cloud | T1_vs_T3 | 83.0% | [77.1%, 87.2%] | ✅ Yes *** |
| nemotron-3-super:cloud | T4A_vs_T3 | -2.7% | [-9.9%, 5.2%] | ❌ No (overlap) |
| nemotron-3-super:cloud | T5_vs_T3 | -3.4% | [-10.5%, 4.4%] | ❌ No (overlap) |
| openrouter/owl-alpha | T1_vs_T3 | 86.7% | [81.5%, 90.2%] | ✅ Yes *** |
| openrouter/owl-alpha | T4A_vs_T3 | -0.4% | [-6.8%, 7.0%] | ❌ No (overlap) |
| openrouter/owl-alpha | T5_vs_T3 | 21.7% | [13.1%, 30.6%] | ✅ Yes *** |

## 5. Default Guess Analysis (Tier-3 Blind)

### gemma4:31b-cloud
| Prediction | Count | % |
|------------|-------|---|
| ChaCha20 | 255 | 91.1% |
| AES-256 | 25 | 8.9% |

### gpt-oss:120b-cloud
| Prediction | Count | % |
|------------|-------|---|
| AES-256 | 197 | 70.4% |
| AES-128 | 26 | 9.3% |
| ML-KEM-768 | 24 | 8.6% |
| RSA-2048 | 21 | 7.5% |
| ChaCha20 | 11 | 3.9% |
| 3DES | 1 | 0.4% |

### nemotron-3-super:cloud
| Prediction | Count | % |
|------------|-------|---|
| AES-256 | 188 | 78.0% |
| ML-KEM-768 | 28 | 11.6% |
| AES-128 | 10 | 4.2% |
| RSA-2048 | 9 | 3.7% |
| ChaCha20 | 4 | 1.7% |
| DES | 2 | 0.8% |

### openrouter/owl-alpha
| Prediction | Count | % |
|------------|-------|---|
| ChaCha20 | 183 | 65.6% |
| AES-256 | 92 | 33.0% |
| AES-128 | 4 | 1.4% |

## Notes

- Errors (429/timeout/parse) are EXCLUDED from k/N — never scored incorrect
- UNKNOWN predictions are EXCLUDED from k/N
- All data from live_sample_140_v2 (secrets.SystemRandom, 140 distinct keys)
- No mixing with v1 corpus (seed:42 bug, duplicate key-IV pairs)
- Wilson score 95% CIs; Newcombe hybrid-score CIs for gap tests
- minimax-m3:cloud excluded: T3 only 39/140 after 1h+ (Ollama cloud rate limits, ~2min/file thinking time), T4A/T5 not started

## 6. Per-Family Breakdown (Tier-3 Blind, 20 files/family/backend)

| Backend | Family (normalized) | k/N | Acc | 95% CI |
|---------|-------------------|-----|-----|--------|
| gemma4:31b-cloud | 3des | 0/40 | 0.0% | [0.0%, 8.8%] |
| gemma4:31b-cloud | aes-128 | 0/40 | 0.0% | [0.0%, 8.8%] |
| gemma4:31b-cloud | aes-256 | 2/40 | 5.0% | [1.4%, 16.5%] |
| gemma4:31b-cloud | chacha20 | 36/40 | 90.0% | [76.9%, 96.0%] |
| gemma4:31b-cloud | des | 0/40 | 0.0% | [0.0%, 8.8%] |
| gemma4:31b-cloud | ml-kem-768 | 0/40 | 0.0% | [0.0%, 8.8%] |
| gemma4:31b-cloud | rsa-2048 | 0/40 | 0.0% | [0.0%, 8.8%] |
| | | | | |
| gpt-oss:120b-cloud | 3des | 0/40 | 0.0% | [0.0%, 8.8%] |
| gpt-oss:120b-cloud | aes-128 | 4/40 | 10.0% | [4.0%, 23.1%] |
| gpt-oss:120b-cloud | aes-256 | 33/40 | 82.5% | [68.0%, 91.3%] |
| gpt-oss:120b-cloud | chacha20 | 0/40 | 0.0% | [0.0%, 8.8%] |
| gpt-oss:120b-cloud | des | 0/40 | 0.0% | [0.0%, 8.8%] |
| gpt-oss:120b-cloud | ml-kem-768 | 11/40 | 27.5% | [16.1%, 42.8%] |
| gpt-oss:120b-cloud | rsa-2048 | 9/40 | 22.5% | [12.3%, 37.5%] |
| | | | | |
| nemotron-3-super:cloud | 3des | 0/40 | 0.0% | [0.0%, 8.8%] |
| nemotron-3-super:cloud | aes-128 | 3/23 | 13.0% | [4.5%, 32.1%] |
| nemotron-3-super:cloud | aes-256 | 17/20 | 85.0% | [64.0%, 94.8%] |
| nemotron-3-super:cloud | chacha20 | 1/38 | 2.6% | [0.5%, 13.5%] |
| nemotron-3-super:cloud | des | 0/40 | 0.0% | [0.0%, 8.8%] |
| nemotron-3-super:cloud | ml-kem-768 | 13/40 | 32.5% | [20.1%, 48.0%] |
| nemotron-3-super:cloud | rsa-2048 | 7/40 | 17.5% | [8.7%, 32.0%] |
| | | | | |
| openrouter/owl-alpha | 3des | 0/40 | 0.0% | [0.0%, 8.8%] |
| openrouter/owl-alpha | aes-128 | 0/39 | 0.0% | [0.0%, 9.0%] |
| openrouter/owl-alpha | aes-256 | 14/40 | 35.0% | [22.1%, 50.5%] |
| openrouter/owl-alpha | chacha20 | 23/40 | 57.5% | [42.2%, 71.5%] |
| openrouter/owl-alpha | des | 0/40 | 0.0% | [0.0%, 8.8%] |
| openrouter/owl-alpha | ml-kem-768 | 0/40 | 0.0% | [0.0%, 8.8%] |
| openrouter/owl-alpha | rsa-2048 | 0/40 | 0.0% | [0.0%, 8.8%] |
| | | | | |

## 7. Confusion Matrix — Tier-3 Pooled (4 backends)

| GT \ PRED |       3des |    aes-128 |    aes-256 |   chacha20 |        des | ml-kem-768 |   rsa-2048 |
|------------|------------|------------|------------|------------|------------|------------|------------|
|       3des |          0 |         10 |         66 |         69 |          1 |         10 |          4 |
|    aes-128 |          1 |          7 |         69 |         59 |          1 |          3 |          2 |
|    aes-256 |          0 |          3 |         66 |         66 |          0 |          3 |          2 |
|   chacha20 |          0 |          1 |         92 |         60 |          0 |          2 |          3 |
|        des |          0 |          8 |         69 |         71 |          0 |         10 |          2 |
| ml-kem-768 |          0 |          6 |         70 |         59 |          0 |         24 |          1 |
|   rsa-2048 |          0 |          5 |         70 |         69 |          0 |          0 |         16 |

## 8. Confusion Matrices — Tier-3 Per Backend


### gemma4:31b-cloud

| GT \ PRED |    aes-256 |   chacha20 |
|------------|------------|------------|
|       3des |          3 |         37 |
|    aes-128 |          5 |         35 |
|    aes-256 |          2 |         38 |
|   chacha20 |          4 |         36 |
|        des |          2 |         38 |
| ml-kem-768 |          7 |         33 |
|   rsa-2048 |          2 |         38 |


### gpt-oss:120b-cloud

| GT \ PRED |       3des |    aes-128 |    aes-256 |   chacha20 | ml-kem-768 |   rsa-2048 |
|------------|------------|------------|------------|------------|------------|------------|
|       3des |          0 |          5 |         21 |          5 |          5 |          4 |
|    aes-128 |          1 |          4 |         31 |          1 |          1 |          2 |
|    aes-256 |          0 |          2 |         33 |          2 |          2 |          1 |
|   chacha20 |          0 |          1 |         35 |          0 |          2 |          2 |
|        des |          0 |          8 |         24 |          3 |          3 |          2 |
| ml-kem-768 |          0 |          4 |         24 |          0 |         11 |          1 |
|   rsa-2048 |          0 |          2 |         29 |          0 |          0 |          9 |


### nemotron-3-super:cloud

| GT \ PRED |    aes-128 |    aes-256 |   chacha20 |        des | ml-kem-768 |   rsa-2048 |
|------------|------------|------------|------------|------------|------------|------------|
|       3des |          4 |         29 |          1 |          1 |          5 |          0 |
|    aes-128 |          3 |         17 |          0 |          1 |          2 |          0 |
|    aes-256 |          1 |         17 |          0 |          0 |          1 |          1 |
|   chacha20 |          0 |         36 |          1 |          0 |          0 |          1 |
|        des |          0 |         31 |          2 |          0 |          7 |          0 |
| ml-kem-768 |          1 |         26 |          0 |          0 |         13 |          0 |
|   rsa-2048 |          1 |         32 |          0 |          0 |          0 |          7 |


### openrouter/owl-alpha

| GT \ PRED |    aes-128 |    aes-256 |   chacha20 |
|------------|------------|------------|------------|
|       3des |          1 |         13 |         26 |
|    aes-128 |          0 |         16 |         23 |
|    aes-256 |          0 |         14 |         26 |
|   chacha20 |          0 |         17 |         23 |
|        des |          0 |         12 |         28 |
| ml-kem-768 |          1 |         13 |         26 |
|   rsa-2048 |          2 |          7 |         31 |

## 9. Default-Guess Rates (Tier-3)

| Backend | Top Guess | Rate | 2nd Guess | Rate | 3rd Guess | Rate |
|---------|-----------|------|-----------|------|-----------|------|
| gemma4:31b-cloud | chacha20 | 91.1% | aes-256 | 8.9% | — | — |
| gpt-oss:120b-cloud | aes-256 | 70.4% | aes-128 | 9.3% | ml-kem-768 | 8.6% |
| nemotron-3-super:cloud | aes-256 | 78.0% | ml-kem-768 | 11.6% | aes-128 | 4.1% |
| openrouter/owl-alpha | chacha20 | 65.6% | aes-256 | 33.0% | aes-128 | 1.4% |
