# ACTS v2 — 3-Backend Interim Results (Pure v2)

Generated: 2026-06-02T03:11:14.658048+00:00
Backends: gemma4:31b-cloud, gpt-oss:120b-cloud, nemotron-3-super:cloud
Total good records: 2481

## Overall Per-Tier Accuracy

| Tier | k/N | Accuracy | 95% Wilson CI |
|------|-----|----------|---------------|
| tier1 | 420/420 | 100.0% | [99.1%, 100.0%] |
| tier2 | 420/420 | 100.0% | [99.1%, 100.0%] |
| tier3 | 136/801 | 17.0% | [14.5%, 19.7%] |
| tier4a | 62/420 | 14.8% | [11.7%, 18.5%] |
| tier5 | 65/420 | 15.5% | [12.3%, 19.2%] |

## Per-Backend × Tier Accuracy

| Backend | tier1 | tier2 | tier3 | tier4a | tier5 |
|---------|--------|--------|--------|--------|--------|
| gemma4:31b-cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 14% [10%,18%] (38/280) | 15% [10%,22%] (21/140) | 19% [13%,26%] (26/140) |
| gpt-oss:120b-cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 20% [16%,25%] (57/280) | 15% [10%,22%] (21/140) | 14% [9%,21%] (20/140) |
| nemotron-3-super:cloud | 100% [97%,100%] (140/140) | 100% [97%,100%] (140/140) | 17% [13%,22%] (41/241) | 14% [9%,21%] (20/140) | 14% [9%,20%] (19/140) |

## Newcombe CI Gaps

| Backend | Gap | Estimate | 95% Newcombe CI | Significant? |
|---------|-----|----------|-----------------|--------------|
| gemma4:31b-cloud | T1_minus_T3 | 86.4% | [81.2%, 90.0%] | ✅ Yes |
| gemma4:31b-cloud | T4A_minus_T3 | 1.4% | [-5.3%, 9.1%] | ❌ No |
| gemma4:31b-cloud | T5_minus_T3 | 5.0% | [-2.2%, 13.1%] | ❌ No |
| gpt-oss:120b-cloud | T1_minus_T3 | 79.6% | [73.9%, 83.9%] | ✅ Yes |
| gpt-oss:120b-cloud | T4A_minus_T3 | -5.4% | [-12.5%, 2.7%] | ❌ No |
| gpt-oss:120b-cloud | T5_minus_T3 | -6.1% | [-13.1%, 1.9%] | ❌ No |
| nemotron-3-super:cloud | T1_minus_T3 | 83.0% | [77.1%, 87.2%] | ✅ Yes |
| nemotron-3-super:cloud | T4A_minus_T3 | -2.7% | [-9.9%, 5.2%] | ❌ No |
| nemotron-3-super:cloud | T5_minus_T3 | -3.4% | [-10.5%, 4.4%] | ❌ No |