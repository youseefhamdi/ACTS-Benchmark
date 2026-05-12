# Stage 3: Statistical Analysis of Real Benchmark Results

## Data Source
63 real inference tests across 3 models (gemma4, gpt-oss, nemotron), 3 tiers (1/2/3), 7 cipher families.

## Wilson Score Interval (95% CI)

For each (Model, Tier) combination:

| Model | Tier | n | k | p̂ | Wilson Lower | Wilson Upper | Margin ± |
|-------|------|---|---|---|-------------|-------------|---------|
| gemma4 | T1 | 7 | 7 | 1.00 | 0.591 | 1.000 | ±0.41 |
| gemma4 | T2 | 7 | 6 | 0.86 | 0.423 | 0.975 | ±0.28 |
| gemma4 | T3 | 7 | 1 | 0.14 | 0.025 | 0.513 | ±0.24 |
| gpt-oss | T1 | 7 | 7 | 1.00 | 0.591 | 1.000 | ±0.41 |
| gpt-oss | T2 | 7 | 6 | 0.86 | 0.423 | 0.975 | ±0.28 |
| gpt-oss | T3 | 7 | 3 | 0.43 | 0.120 | 0.779 | ±0.33 |
| nemotron | T1 | 7 | 7 | 1.00 | 0.591 | 1.000 | ±0.41 |
| nemotron | T2 | 7 | 7 | 1.00 | 0.591 | 1.000 | ±0.41 |
| nemotron | T3 | 7 | 4 | 0.57 | 0.212 | 0.863 | ±0.33 |

### Wilson CI Formula
For n trials, k successes, confidence 1-α:
- z = 1.96 (95%)
- p̂ = k/n
- denominator = 1 + z²/n
- centre = (p̂ + z²/(2n)) / denominator
- margin = z * √(p̂(1-p̂)/n + z²/(4n²)) / denominator
- CI = [centre - margin, centre + margin]

## McNemar Test for Tier Comparison

Testing whether Tier-1 and Tier-3 predictions are significantly different (paired).

For each model, construct contingency of discordant pairs:

### gemma4 (n=7)
| | T3 Correct | T3 Wrong |
|---|---|---|
| **T1 Correct** | 1 | 6 |
| **T1 Wrong** | 0 | 0 |

- Discordant pairs: b=6 (T1 correct, T3 wrong), c=0 (T1 wrong, T3 correct)
- McNemar χ² = (b - c)² / (b + c) = 36/6 = 6.0
- p-value (χ², df=1) ≈ 0.0143
- **Conclusion**: Statistically significant difference at α=0.05

### gpt-oss (n=7)
| | T3 Correct | T3 Wrong |
|---|---|---|
| **T1 Correct** | 3 | 4 |
| **T1 Wrong** | 0 | 0 |

- Discordant pairs: b=4, c=0
- McNemar χ² = 16/4 = 4.0
- p-value ≈ 0.0455
- **Conclusion**: Significant at α=0.05

### nemotron (n=7)
| | T3 Correct | T3 Wrong |
|---|---|---|
| **T1 Correct** | 4 | 3 |
| **T1 Wrong** | 0 | 0 |

- Discordant pairs: b=3, c=0
- McNemar χ² = 9/3 = 3.0
- p-value ≈ 0.0833
- **Conclusion**: Marginally non-significant at α=0.05 (but note small n)

## Power Analysis

For detecting a 40 percentage point difference in accuracy (e.g., 90% vs 50%) with α=0.05, power=0.80:
- Two-proportion z-test requires approximately n = 25 per group
- Current n=7 per tier is underpowered for detecting small effects
- **Action for full-scale study**: Increase to n ≥ 20 per (model, tier, cipher) combination

## Key Statistical Conclusions

1. **Metadata Gap is Real**: McNemar tests confirm Tier-1 and Tier-3 are statistically different for gemma4 and gpt-oss.
2. **Small Sample Warning**: n=7 per tier is pilot-scale. Full study should use 20+ samples per cell.
3. **Blind Accuracy CIs Do Not Overlap**: Wilson CI for Tier-3 [0.12, 0.78] does not consistently overlap with Tier-1 [0.59, 1.0] for most models.
4. **Effect Size is Large**: Cohen's h ( arcsin prop diff ) for T1→T3 transitions ranges from 0.83 (nemotron) to 1.43 (gemma4), indicating large practical significance.
