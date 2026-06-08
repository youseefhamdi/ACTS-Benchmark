# ACTS R3 Revision — v2 Results Summary

## Main Matrix (T1/T2/T3) on Regenerated Corpus

### Headline Results

| Tier | Records | Accuracy | 95% CI | vs v1 |
|------|---------|----------|--------|-------|
| T1 (metadata-rich) | 611 | 88.4% | [85.6%, 90.7%] | +5.3pp |
| T2 (filename-only) | 560 | 96.4% | [94.5%, 97.7%] | +16.0pp |
| T3 (blind stats-only) | 973 | 20.2% | [17.8%, 22.9%] | -3.2pp |
| T3-Raw (blind + hex) | 486 | 19.8% | [16.5%, 23.5%] | — |
| T4A (tool-augmented) | 32 | 0.0% | [0.0%, 10.7%] | incomplete |
| T5 (forced CoT) | 0 | N/A | N/A | incomplete |

### Per-Backend T1/T2/T3

| Backend | T1 | T2 | T3 | Metadata Gap |
|---------|----|----|----|-------------|
| gemma4 | 100% | 100% | 13.2% | 86.8pp |
| gpt-oss | 100% | 100% | 41.4% | 58.6pp |
| nemotron | 100% | 100% | 39.6%‡ | 60.4pp |
| owl-alpha | 85.7% | 85.7% | 0.0%† | 85.7pp |

‡ Nemotron T3 only 56/140 files (40% coverage) due to OpenRouter 429s
† Owl-alpha T3 only 40/140 files (29% coverage) — all predictions were wrong (0/79 records, but 429s on 39 files)

### T3 Per-Family Accuracy (pooled)

| Family | k/N | Acc | 95% CI |
|--------|-----|-----|--------|
| chacha20 | 41/80 | 51.2% | [40.5%, 61.9%] |
| rsa-2048 | 38/80 | 47.5% | [36.9%, 58.3%] |
| aes-256 | 51/111 | 45.9% | [37.0%, 55.2%] |
| ml-kem-768 | 17/80 | 21.2% | [13.7%, 31.4%] |
| aes-128 | 25/159 | 15.7% | [10.9%, 22.2%] |
| 3des | 25/160 | 15.6% | [10.8%, 22.0%] |
| des | 0/80 | 0.0% | [0.0%, 4.6%] |

### T3 Default Guess Rates

| Backend | Modal Prediction | Rate |
|---------|-----------------|------|
| gemma4 | chacha20 | 91.1% |
| gpt-oss | aes-256 | 41.8% |
| nemotron | aes-256 | 34.2% |
| owl-alpha | chacha20 | 64.6% |

### Key Findings

1. **Massive metadata gap confirmed**: 59-87pp drop from T1→T3 across all backends
2. **T3 ranking**: chacha20 (51%) > rsa-2048 (48%) > aes-256 (46%) > ml-kem-768 (21%) > aes-128 (17%) > 3des (16%) > des (0%)
3. **Cross-backend variance**: T3 accuracy ranges from 13% (gemma4) to 41% (gpt-oss)
4. **Default guess diversity**: gemma4→chacha20, gpt-oss→aes-256, nemotron→aes-256
5. **Corpus quality**: v2 results are consistent with v1 — the seed/duplicate fix did not change conclusions

### Data Quality Notes
- Nemotron and gemma-free backends hit OpenRouter rate limits (HTTP 429)
- Owl-alpha T3 has partial coverage (40/140 files with errors, 0/79 good records correct)
- T4A and T5 could not be run on v2 due to rate limits
- v1 T4A/T5 results remain the best available for those tiers
