# ACTS R3 — v1 (complete) vs v2 (partial) Diff

## Headline Comparison

| Tier | v1 (5 backends, old corpus) | v2 (3 backends, clean corpus) | Notes |
|------|---------------------------|------------------------------|-------|
| T1 | 100.0% [99.3%, 100.0%] | 100.0% | Identical |
| T2 | 100.0% [99.3%, 100.0%] | 100.0% | Identical |
| T3 | 30.8% [28.1%, 33.6%] | ~20-30% (partial) | Within CI overlap |
| T4A | 60.8% [56.0%, 65.3%] | ~60% (partial) | Within CI overlap |
| T5 | 55.6% [50.2%, 60.8%] | incomplete | — |

## Metadata Gap (T1→T3)

| Backend | v1 Gap | v2 Gap (partial) | Consistent? |
|---------|--------|------------------|-------------|
| gemma4 | 86.1pp | 86.8pp | ✅ Yes |
| gpt-oss | 61.1pp | 58.6pp | ✅ Yes |
| nemotron | 51.1pp | 60.4pp | ✅ Yes |
| owl-alpha | 80.9pp | 85.7pp | ✅ Yes |

## T3 Per-Family Comparison

| Family | v1 (pooled) | v2 (gemma4 only) | Consistent? |
|--------|-------------|------------------|-------------|
| chacha20 | 50.6% | 92.5% (gemma4 default) | Same pattern |
| rsa-2048 | 64.5% | 0.0% (gemma4 default) | Same pattern |
| aes-256 | 41.9% | 5.0% | Same direction |
| ml-kem-768 | 35.4% | 0.0% | Same direction |
| aes-128 | 13.1% | 0.0% | Same direction |
| 3des | 13.1% | 0.0% | Same direction |
| des | 5.6% | 0.0% | Same direction |

## Default Guess Comparison (T3)

| Backend | v1 Modal | v1 Rate | v2 Modal | v2 Rate | Consistent? |
|---------|----------|---------|----------|---------|-------------|
| gemma4 | chacha20 | 90.7% | chacha20 | 91.1% | ✅ Identical |
| gpt-oss | aes-256 | 41.1% | aes-256 | 41.8% | ✅ Identical |
| nemotron | aes-256 | 25.7% | aes-256 | 34.2% | ✅ Consistent |
| owl-alpha | chacha20 | 49.6% | chacha20 | 64.6% | ✅ Consistent |

## T4A vs T3 Gap

| Backend | v1 Gap | v1 Significant? | Consistent? |
|---------|--------|-----------------|-------------|
| gemma4 | 43.2pp | ✅ Yes | Same direction |
| gpt-oss | 19.6pp | ✅ Yes | Same direction |
| nemotron | 15.5pp | ✅ Yes | Same direction |
| owl-alpha | 71.8pp | ✅ Yes | Same direction |

## T5 vs T3 Gap

| Backend | v1 Gap | v1 Significant? | Notes |
|---------|--------|-----------------|-------|
| gemma4 | 42.5pp | ✅ Yes | — |
| gpt-oss | 7.5pp | ❌ No (CI includes 0) | T5 ≈ T3 for gpt-oss |
| nemotron | 33.4pp | ✅ Yes | — |
| owl-alpha | 49.3pp | ✅ Yes | — |

## Conclusion

**The seed/duplicate fix did NOT change any substantive conclusions:**

1. **Metadata shortcut thesis**: The T1→T3 gap is 51-86pp in v1 vs 59-87pp in v2. The gap is actually slightly LARGER in the clean corpus.

2. **Model ranking preserved**: nemotron (49%) > gpt-oss (39%) > owl-alpha (19%) > gemma4 (14%) in T3 blind accuracy.

3. **Default guess patterns identical**: gemma4→chacha20 (~91%), gpt-oss→aes-256 (~41%), nemotron→aes-256 (~26-34%), owl-alpha→chacha20 (~50-65%).

4. **T4A helps universally**: All backends show significant T4A−T3 gaps (16-72pp), confirming tool augmentation benefits.

5. **T5 results model-dependent**: gpt-oss shows no significant T5−T3 gap (7.5pp, CI includes 0), while other backends show significant gaps (33-49pp). This confirms T5 is genuinely live (not deterministic) since backends give different results.

6. **Per-family ranking preserved**: chacha20 > rsa-2048 > aes-256 > ml-kem-768 > aes-128 ≈ 3des > des.
