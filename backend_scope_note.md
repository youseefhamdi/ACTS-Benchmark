# Backend Scope Note — ACTS v2 Final Evaluation

## Included Backends (4)

| # | Backend | Provider | Type | Context |
|---|---------|----------|------|---------|
| 1 | `gemma4:31b-cloud` | Ollama (cloud proxy) | Local proxy | 31B |
| 2 | `gpt-oss:120b-cloud` | Ollama (cloud proxy) | Local proxy | 120B |
| 3 | `nemotron-3-super:cloud` | Ollama (cloud proxy) | Local proxy | Super |
| 4 | `openrouter/owl-alpha` | OpenRouter (free tier) | Free tier | Alpha |

**Total good records**: 3,320 (4 backends × 140 files × 5 tiers, minus errors/UNKNOWNs excluded)

## Excluded Backends

### `minimax-m3:cloud` (Ollama cloud proxy, thinking model)

**Rationale**: Ollama cloud 429/401 rate limits caused extreme slowdown. After 1h+ of runtime, T3 had only 39/140 good records (many UNKNOWN abstentions). T4A and T5 were not started. The per-file thinking time (~2min) makes a full 700-call matrix infeasible (>10h estimated). **Excluded entirely from all reported numbers.** Raw shard archived at `minimax_m3_all_v2_final_ARCHIVED.jsonl` for reference but never appears in any statistic.

### `google/gemma-4-31b-it:free` (OpenRouter free tier)

**Rationale**: >50% error rate (429 rate limits) across all tiers in initial attempts. Free-tier models have strict rate limits that make 700 calls per backend infeasible. Excluded from all runs.

## Corpus

**v2 corpus** (`live_sample_140_v2`): 140 distinct files, `secrets.SystemRandom` key generation, 140 distinct plaintexts, 140 distinct keys. Block cipher files (DES, 3DES, AES-128, AES-256) were regenerated with non-block-aligned plaintext lengths so padding amounts genuinely vary across files. This addresses Reviewer #4's concern about padding diversity.

**Corpus versioning**: v2.1-pad-diverse (80 of 140 files regenerated; ChaCha20, RSA, ML-KEM unchanged; block cipher family files regenerated with varying-length plaintexts).

## Error Handling

All reported k/N statistics **exclude**:
- HTTP 429 (rate limit) responses
- Timeout errors
- Parse failures (no extractable prediction)
- UNKNOWN predictions (model abstained)

These are never scored as incorrect (never in k or N). Only records with a valid parsed prediction contribute to accuracy calculations.
