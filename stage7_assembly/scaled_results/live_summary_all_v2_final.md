# ACTS v2 FINAL — Unified Live Evaluation Results

Generated: 2026-06-02T01:10:33.220265+00:00

Errors and UNKNOWN predictions EXCLUDED from all denominators.

Coverage: 140 files × 20/family × 7 families per backend per tier.


## T1

**Records:** 582 | **Accuracy:** 100.0% [99.3%, 100.0%]

| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |
|---------|-----|------|---------------|-------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| nemotron-3-super:cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| openrouter/owl-alpha | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| google/gemma-4-31b-it:free | 22/22 | 100.0% | [85.1%, 100.0%] | 22/140 | 3DES (86.4%) |

## T2

**Records:** 563 | **Accuracy:** 100.0% [99.3%, 100.0%]

| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |
|---------|-----|------|---------------|-------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| nemotron-3-super:cloud | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| openrouter/owl-alpha | 140/140 | 100.0% | [97.3%, 100.0%] | 140/140 | 3DES (14.3%) |
| google/gemma-4-31b-it:free | 3/3 | 100.0% | [43.8%, 100.0%] | 3/140 | ChaCha20 (100.0%) |

## T3

**Records:** 1065 | **Accuracy:** 30.8% [28.1%, 33.6%]

| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |
|---------|-----|------|---------------|-------|---------------|
| gemma4:31b-cloud | 39/280 | 13.9% | [10.4%, 18.5%] | 140/140 | ChaCha20 (90.7%) |
| gpt-oss:120b-cloud | 109/280 | 38.9% | [33.4%, 44.8%] | 140/140 | AES-256 (41.1%) |
| nemotron-3-super:cloud | 137/280 | 48.9% | [43.1%, 54.8%] | 140/140 | AES-256 (25.7%) |
| openrouter/owl-alpha | 43/225 | 19.1% | [14.5%, 24.8%] | 113/140 | ChaCha20 (61.8%) |

## T4A

**Records:** 423 | **Accuracy:** 60.8% [56.0%, 65.3%]

| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |
|---------|-----|------|---------------|-------|---------------|
| gemma4:31b-cloud | 80/140 | 57.1% | [48.9%, 65.0%] | 140/140 | AES-128 (37.9%) |
| gpt-oss:120b-cloud | 82/140 | 58.6% | [50.3%, 66.4%] | 140/140 | AES-128 (34.3%) |
| nemotron-3-super:cloud | 85/132 | 64.4% | [55.9%, 72.0%] | 128/140 | AES-128 (37.9%) |
| openrouter/owl-alpha | 10/11 | 90.9% | [62.3%, 98.4%] | 11/140 | 3DES (90.9%) |

## T5

**Records:** 333 | **Accuracy:** 55.6% [50.2%, 60.8%]

| Backend | k/N | Acc% | Wilson 95% CI | Files | Default Guess |
|---------|-----|------|---------------|-------|---------------|
| gemma4:31b-cloud | 79/140 | 56.4% | [48.2%, 64.4%] | 140/140 | AES-128 (37.9%) |
| gpt-oss:120b-cloud | 65/140 | 46.4% | [38.4%, 54.7%] | 140/140 | 3DES (31.4%) |
| nemotron-3-super:cloud | 28/34 | 82.4% | [66.5%, 91.7%] | 34/140 | 3DES (47.1%) |
| openrouter/owl-alpha | 13/19 | 68.4% | [46.0%, 84.6%] | 19/140 | 3DES (68.4%) |

## Gap Analysis (Newcombe CI)


### T1 vs T3

| Backend | T1 Acc | T2 Acc | Gap | 95% CI | Significant? |
|---------|--------|--------|-----|--------|--------------
| gemma4:31b-cloud | 100.0% | 13.9% | 86.1pp | [80.8, 89.6] | ✅ Yes |
| gpt-oss:120b-cloud | 100.0% | 38.9% | 61.1pp | [54.7, 66.6] | ✅ Yes |
| nemotron-3-super:cloud | 100.0% | 48.9% | 51.1pp | [44.7, 56.9] | ✅ Yes |
| openrouter/owl-alpha | 100.0% | 19.1% | 80.9pp | [74.6, 85.5] | ✅ Yes |

### T4A vs T3

| Backend | T1 Acc | T2 Acc | Gap | 95% CI | Significant? |
|---------|--------|--------|-----|--------|--------------
| gemma4:31b-cloud | 57.1% | 13.9% | 43.2pp | [33.8, 51.9] | ✅ Yes |
| gpt-oss:120b-cloud | 58.6% | 38.9% | 19.6pp | [9.5, 29.2] | ✅ Yes |
| nemotron-3-super:cloud | 64.4% | 48.9% | 15.5pp | [5.2, 25.1] | ✅ Yes |
| openrouter/owl-alpha | 90.9% | 19.1% | 71.8pp | [42.6, 80.5] | ✅ Yes |

### T5 vs T3

| Backend | T1 Acc | T2 Acc | Gap | 95% CI | Significant? |
|---------|--------|--------|-----|--------|--------------
| gemma4:31b-cloud | 56.4% | 13.9% | 42.5pp | [33.1, 51.2] | ✅ Yes |
| gpt-oss:120b-cloud | 46.4% | 38.9% | 7.5pp | [-2.4, 17.4] | ❌ No |
| nemotron-3-super:cloud | 82.4% | 48.9% | 33.4pp | [16.5, 44.4] | ✅ Yes |
| openrouter/owl-alpha | 68.4% | 19.1% | 49.3pp | [26.2, 66.2] | ✅ Yes |