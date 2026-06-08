# ACTS v2 — Unified Live Evaluation Results

Generated: 2026-06-01T16:19:14.164061+00:00

All tiers: Tier-1 (metadata-rich), Tier-2 (filename-only), Tier-3 (blind stats-only), Tier-3-Raw (blind + raw hex), Tier-4A (tool-augmented blind), Tier-5 (forced CoT reasoning)


## TIER1 — Overall
**Records:** 611
**Accuracy:** 88.4% (Wilson 95% CI: [85.6%, 90.7%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.8s | 3DES (14%) |
| google/gemma-4-31b-it:free | 0/51 | 0.0% [0.0%,7.0%] | 0.7s | UNKNOWN (100%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.5s | 3DES (14%) |
| nemotron-3-super:cloud | 140/140 | 100.0% [97.3%,100.0%] | 0.9s | 3DES (14%) |
| openrouter/owl-alpha | 120/140 | 85.7% [79.0%,90.6%] | 3.2s | 3DES (14%) |


## TIER2 — Overall
**Records:** 560
**Accuracy:** 96.4% (Wilson 95% CI: [94.5%, 97.7%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.1s | 3DES (14%) |
| gpt-oss:120b-cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.4s | 3DES (14%) |
| nemotron-3-super:cloud | 140/140 | 100.0% [97.3%,100.0%] | 1.1s | 3DES (14%) |
| openrouter/owl-alpha | 120/140 | 85.7% [79.0%,90.6%] | 4.2s | 3DES (14%) |


## TIER3 — Overall
**Records:** 973
**Accuracy:** 20.2% (Wilson 95% CI: [17.8%, 22.9%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 37/280 | 13.2% [9.7%,17.7%] | 1.7s | ChaCha20 (91%) |
| gpt-oss:120b-cloud | 116/280 | 41.4% [35.8%,47.3%] | 8.3s | AES-256 (42%) |
| nemotron-3-super:cloud | 44/313 | 14.1% [10.6%,18.4%] | 7.0s | UNKNOWN (65%) |
| openrouter/owl-alpha | 0/100 | 0.0% [0.0%,3.7%] | 3.2s | CHACHA20 (51%) |


## TIER3_RAW — Overall
**Records:** 486
**Accuracy:** 19.8% (Wilson 95% CI: [16.5%, 23.5%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 17/140 | 12.1% [7.7%,18.6%] | 1.0s | ChaCha20 (92%) |
| gpt-oss:120b-cloud | 54/140 | 38.6% [30.9%,46.8%] | 8.7s | AES-256 (44%) |
| nemotron-3-super:cloud | 25/156 | 16.0% [11.1%,22.6%] | 8.4s | UNKNOWN (65%) |
| openrouter/owl-alpha | 0/50 | 0.0% [0.0%,7.1%] | 3.3s | CHACHA20 (54%) |


## TIER4A — Overall
**Records:** 32
**Accuracy:** 0.0% (Wilson 95% CI: [0.0%, 10.7%])

### Per-Backend
| Backend | k/N | Accuracy | 95% CI | Avg Latency | Default Guess |
|---------|-----|----------|--------|-------------|---------------|
| gemma4:31b-cloud | 0/32 | 0.0% [0.0%,10.7%] | 0.2s | UNKNOWN (100%) |


## Gap Analysis
| Comparison | Backend | Gap | 95% CI |
|------------|---------|-----|--------|
| tier1_vs_tier3 | gemma4:31b-cloud | 86.8% [82.6%,91.0%] |
| tier4a_vs_tier3 | gemma4:31b-cloud | -13.2% [-19.9%,-6.5%] |
| tier1_vs_tier3 | gpt-oss:120b-cloud | 58.6% [52.7%,64.5%] |
| tier1_vs_tier3 | nemotron-3-super:cloud | 85.9% [81.9%,90.0%] |
| tier1_vs_tier3 | openrouter/owl-alpha | 85.7% [79.6%,91.8%] |


## Confusion Matrices

### TIER1
| True \ Pred | 3DES     | AES-128  | AES-256  | CHACHA20 | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 80       | 0        | 0        | 0        | 0        | 0        | 0        | 20       |
| AES-256      | 0        | 0        | 80       | 0        | 0        | 0        | 0        | 0        | 11       |
| DES          | 0        | 0        | 0        | 0        | 0        | 80       | 0        | 0        | 0        |
| 3DES         | 80       | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 20       |
| ChaCha20     | 0        | 0        | 0        | 20       | 60       | 0        | 0        | 0        | 0        |
| RSA-2048     | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 80       | 0        |
| ML-KEM-768   | 0        | 0        | 0        | 0        | 0        | 0        | 80       | 0        | 0        |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER2
| True \ Pred | 3DES     | AES-128  | AES-256  | CHACHA20 | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 |
|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 80       | 0        | 0        | 0        | 0        | 0        | 0        |
| AES-256      | 0        | 0        | 80       | 0        | 0        | 0        | 0        | 0        |
| DES          | 0        | 0        | 0        | 0        | 0        | 80       | 0        | 0        |
| 3DES         | 80       | 0        | 0        | 0        | 0        | 0        | 0        | 0        |
| ChaCha20     | 0        | 0        | 0        | 20       | 60       | 0        | 0        | 0        |
| RSA-2048     | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 80       |
| ML-KEM-768   | 0        | 0        | 0        | 0        | 0        | 0        | 80       | 0        |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER3
| True \ Pred | 3DES     | AES-128  | AES-256  | CHACHA20 | ChaCha20 | DES      | ML-KEM-7 | RSA-2048 | UNKNOWN  |
|---|---|---|---|---|---|---|---|---|---|
| AES-128      | 0        | 25       | 70       | 24       | 40       | 0        | 0        | 0        | 1        |
| AES-256      | 0        | 20       | 51       | 0        | 39       | 0        | 1        | 0        | 37       |
| DES          | 10       | 1        | 5        | 0        | 61       | 0        | 0        | 3        | 40       |
| 3DES         | 25       | 3        | 23       | 27       | 68       | 13       | 0        | 1        | 0        |
| ChaCha20     | 0        | 4        | 31       | 0        | 41       | 0        | 0        | 4        | 45       |
| RSA-2048     | 0        | 0        | 3        | 0        | 39       | 0        | 0        | 38       | 42       |
| ML-KEM-768   | 0        | 1        | 23       | 0        | 39       | 0        | 17       | 0        | 58       |
| UNKNOWN      | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        | 0        |

### TIER4A
| True \ Pred | UNKNOWN  |
|---|---|
| AES-128      | 12       |
| AES-256      | 0        |
| DES          | 0        |
| 3DES         | 20       |
| ChaCha20     | 0        |
| RSA-2048     | 0        |
| ML-KEM-768   | 0        |
| UNKNOWN      | 0        |


*CI = Wilson score 95% confidence interval*