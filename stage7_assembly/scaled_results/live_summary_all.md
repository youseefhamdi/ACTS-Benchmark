# ACTS v2 — Unified Live Evaluation Results

Generated: 2026-06-01T09:56:31.077457+00:00

All tiers: Tier-1 (metadata-rich), Tier-2 (filename-only), Tier-3 (blind stats-only), Tier-3-Raw (blind + raw hex), Tier-4A (tool-augmented blind), Tier-5 (forced CoT reasoning)


## TIER1 — Overall
**Records:** 700
**Accuracy:** 83.1% (Wilson 95% CI: [80.2%, 85.7%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.8s | 3DES (14%) |
| google/gemma-4-31b-it:free | 22/140 | 15.7% [10.6%,22.7%] | 1.4s | UNKNOWN (84%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.9s | 3DES (14%) |
| nemotron-3-super:cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.7s | 3DES (14%) |
| openrouter/owl-alpha | 140/140 | 100.0% [97.3%,100.0%] | 5.9s | 3DES (14%) |


## TIER2 — Overall
**Records:** 700
**Accuracy:** 80.4% (Wilson 95% CI: [77.3%, 83.2%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.1s | 3DES (14%) |
| google/gemma-4-31b-it:free | 3/140 | 2.1% [0.7%,6.1%] | 0.9s | UNKNOWN (98%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.9s | 3DES (14%) |
| nemotron-3-super:cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.8s | 3DES (14%) |
| openrouter/owl-alpha | 140/140 | 100.0% [97.3%,100.0%] | 4.5s | 3DES (14%) |


## TIER3 — Overall
**Records:** 1400
**Accuracy:** 23.4% (Wilson 95% CI: [21.3%, 25.7%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 39/280 | 13.9% [10.4%,18.5%] | 1.5s | ChaCha20 (91%) |
| google/gemma-4-31b-it:free | 0/280 | 0.0% [0.0%,1.4%] | 0.9s | UNKNOWN (100%) |
| gpt-oss:120b-cloud | 109/280 | 38.9% [33.4%,44.8%] | 4.7s | AES-256 (41%) |
| nemotron-3-super:cloud | 137/280 | 48.9% [43.1%,54.8%] | 10.8s | AES-256 (26%) |
| openrouter/owl-alpha | 43/280 | 15.4% [11.6%,20.1%] | 4.1s | ChaCha20 (50%) |


## TIER3_RAW — Overall
**Records:** 700
**Accuracy:** 22.9% (Wilson 95% CI: [19.9%, 26.1%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 20/140 | 14.3% [9.4%,21.0%] | 1.3s | ChaCha20 (91%) |
| google/gemma-4-31b-it:free | 0/140 | 0.0% [0.0%,2.7%] | 0.8s | UNKNOWN (100%) |
| gpt-oss:120b-cloud | 52/140 | 37.1% [29.6%,45.4%] | 5.0s | AES-256 (42%) |
| nemotron-3-super:cloud | 69/140 | 49.3% [41.1%,57.5%] | 13.7s | AES-256 (28%) |
| openrouter/owl-alpha | 19/140 | 13.6% [8.9%,20.2%] | 4.5s | ChaCha20 (57%) |


## TIER4A — Overall
**Records:** 435
**Accuracy:** 59.1% (Wilson 95% CI: [54.4%, 63.6%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 80/140 | 57.1% [48.9%,65.0%] | 7.9s | AES-128 (38%) |
| gpt-oss:120b-cloud | 82/140 | 58.6% [50.3%,66.4%] | 9.7s | AES-128 (34%) |
| nemotron-3-super:cloud | 85/144 | 59.0% [50.9%,66.7%] | 43.5s | AES-128 (35%) |
| openrouter/owl-alpha | 10/11 | 90.9% [62.3%,98.4%] | 21.3s | 3DES (91%) |


## TIER5 — Overall
**Records:** 700
**Accuracy:** 26.4% (Wilson 95% CI: [23.3%, 29.8%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 79/140 | 56.4% [48.1%,64.4%] | 9.8s | AES-128 (38%) |
| google/gemma-4-31b-it:free | 0/140 | 0.0% [0.0%,2.7%] | 0.0s | UNKNOWN (100%) |
| gpt-oss:120b-cloud | 65/140 | 46.4% [38.4%,54.7%] | 27.4s | 3DES (31%) |
| nemotron-3-super:cloud | 28/140 | 20.0% [14.2%,27.4%] | 15.4s | UNKNOWN (76%) |
| openrouter/owl-alpha | 13/140 | 9.3% [5.5%,15.2%] | 11.8s | UNKNOWN (86%) |


## Gap Analysis
| Comparison | Backend | Gap | 95% CI |
|------------|---------|-----|--------|
| tier1_vs_tier3 | gemma4:31b-cloud | 86.1% [81.8%,90.3%] |
| tier4a_vs_tier3 | gemma4:31b-cloud | 43.2% [34.2%,52.3%] |
| tier1_vs_tier3 | google/gemma-4-31b-it:free | 15.7% [9.7%,21.8%] |
| tier1_vs_tier3 | gpt-oss:120b-cloud | 61.1% [55.2%,66.9%] |
| tier4a_vs_tier3 | gpt-oss:120b-cloud | 19.6% [9.8%,29.5%] |
| tier1_vs_tier3 | nemotron-3-super:cloud | 51.1% [45.1%,57.0%] |
| tier4a_vs_tier3 | nemotron-3-super:cloud | 10.1% [0.3%,19.9%] |
| tier1_vs_tier3 | openrouter/owl-alpha | 84.6% [80.2%,89.1%] |
| tier4a_vs_tier3 | openrouter/owl-alpha | 75.5% [57.0%,94.1%] |


## Confusion Matrices

### TIER1
| True \ Pred | 3DES     | AES-128  | AES-256  | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 83       | 0        | 0        | 0        | 0        | 0        | 17       |
| AES-256      | 0        | 0        | 80       | 0        | 0        | 0        | 0        | 20       |
| DES          | 0        | 0        | 0        | 0        | 80       | 0        | 0        | 20       |
| 3DES         | 99       | 0        | 0        | 0        | 0        | 0        | 0        | 1        |
| ChaCha20     | 0        | 0        | 0        | 80       | 0        | 0        | 0        | 20       |
| RSA-2048     | 0        | 0        | 0        | 0        | 0        | 0        | 80       | 20       |
| ML-KEM-768   | 0        | 0        | 0        | 0        | 0        | 80       | 0        | 20       |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER2
| True \ Pred | 3DES     | AES-128  | AES-256  | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 80       | 0        | 0        | 0        | 0        | 0        | 20       |
| AES-256      | 0        | 0        | 80       | 0        | 0        | 0        | 0        | 20       |
| DES          | 0        | 0        | 0        | 0        | 80       | 0        | 0        | 20       |
| 3DES         | 80       | 0        | 0        | 0        | 0        | 0        | 0        | 20       |
| ChaCha20     | 0        | 0        | 0        | 83       | 0        | 0        | 0        | 17       |
| RSA-2048     | 0        | 0        | 0        | 0        | 0        | 0        | 80       | 20       |
| ML-KEM-768   | 0        | 0        | 0        | 0        | 0        | 80       | 0        | 20       |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER3
| True \ Pred | 3DES     | AES-128  | AES-256  | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 21       | 75       | 64       | 0        | 0        | 0        | 40       |
| AES-256      | 0        | 25       | 67       | 68       | 0        | 0        | 0        | 40       |
| DES          | 24       | 1        | 33       | 92       | 9        | 0        | 1        | 40       |
| 3DES         | 21       | 1        | 28       | 93       | 15       | 1        | 1        | 40       |
| ChaCha20     | 0        | 4        | 51       | 81       | 0        | 2        | 22       | 40       |
| RSA-2048     | 0        | 0        | 4        | 39       | 0        | 0        | 78       | 79       |
| ML-KEM-768   | 0        | 1        | 40       | 52       | 0        | 51       | 0        | 56       |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER4A
| True \ Pred | 3DES     | AES-128  | AES-256  | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 59       | 1        | 0        | 0        | 0        | 0        | 0        |
| AES-256      | 0        | 62       | 0        | 2        | 0        | 0        | 0        | 0        |
| DES          | 47       | 0        | 0        | 0        | 1        | 0        | 0        | 12       |
| 3DES         | 65       | 0        | 0        | 3        | 3        | 0        | 0        | 0        |
| ChaCha20     | 0        | 30       | 3        | 12       | 0        | 0        | 15       | 0        |
| RSA-2048     | 0        | 0        | 0        | 0        | 0        | 0        | 60       | 0        |
| ML-KEM-768   | 0        | 0        | 0        | 0        | 0        | 60       | 0        | 0        |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER5
| True \ Pred | 3DES     | AES-128  | AES-256  | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 3        | 45       | 0        | 1        | 3        | 1        | 1        | 46       |
| AES-256      | 1        | 37       | 0        | 1        | 1        | 0        | 0        | 60       |
| DES          | 38       | 0        | 0        | 0        | 2        | 0        | 0        | 60       |
| 3DES         | 66       | 1        | 0        | 8        | 4        | 0        | 0        | 21       |
| ChaCha20     | 2        | 21       | 1        | 5        | 0        | 0        | 11       | 60       |
| RSA-2048     | 2        | 1        | 0        | 3        | 1        | 0        | 33       | 60       |
| ML-KEM-768   | 1        | 0        | 0        | 2        | 3        | 34       | 0        | 60       |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |


*CI = Wilson score 95% confidence interval*