# Task 3: Backend-Scope Decision Note (Reviewer #4.4)

**Date:** 2026-06-01
**Status:** Report only — do NOT run more backends until human confirms.

## Current Evaluation Scope

### Backends Evaluated (5 total)

| # | Backend | Type | Tiers Complete | Notes |
|---|---------|------|----------------|-------|
| 1 | gemma4:31b-cloud | Ollama (local) | T1/T2/T3/T4A/T5 | All tiers complete (v1), re-running on v2 corpus |
| 2 | gpt-oss:120b-cloud | Ollama (local) | T1/T2/T3/T4A/T5 | All tiers complete (v1), re-running on v2 corpus |
| 3 | nemotron-3-super:cloud | Ollama (local) | T1/T2/T3/T4A/T5 | All tiers complete (v1), re-running on v2 corpus |
| 4 | openrouter/owl-alpha | OpenRouter (free) | T1/T2/T3/T4A/T5 | All tiers complete (v1), re-running on v2 corpus |
| 5 | google/gemma-4-31b-it:free | OpenRouter (free) | T1/T2/T3/T4A/T5 | All tiers complete (v1), re-running on v2 corpus |

**Tier completeness per backend (v1 data):**
- Tier-1: 5/5 backends × 140 files = 700 records ✓
- Tier-2: 5/5 backends × 140 files = 700 records ✓
- Tier-3: 5/5 backends × 140 files × 2 variants = 1400 records ✓
- Tier-4A: 4/5 backends × ~107 files = 435 records (owl-alpha partial: 11 records)
- Tier-5: 5/5 backends × 140 files = 700 records ✓

### Systems NOT Evaluated (of the 21 claimed)

The paper claims evaluation across 21 systems. The following 16 systems were NOT run:

**Ollama local (free):**
- llama3.1:8b, llama3.1:70b, llama3.3:70b
- qwen2.5:7b, qwen2.5:32b, qwen3:8b
- mistral:7b, mixtral:8x7b
- phi3:14b, phi4:14b
- codellama:70b

**OpenRouter free tier:**
- meta-llama/llama-4-maverick:free
- meta-llama/llama-4-scout:free
- deepseek/deepseek-r1:free
- deepseek/deepseek-chat-v3:free
- anthropic/claude-sonnet-4:free (if available)

**Other:**
- gemini-2.0-flash:free (OpenRouter)
- command-r-plus:free (OpenRouter)

## Two Options for Reviewer #4.4

### Option A: Narrow Scope to 5 Backends (RECOMMENDED)
- **Claim:** "We evaluate 5 diverse LLM backends spanning 3 model families (Gemma, GPT-OSS, Nemotron) across 6 evaluation tiers."
- **Advantages:** Tier-1 is 100% complete for all 5 backends. Results are internally consistent. No additional compute cost.
- **Disadvantage:** Reviewer may still want more diversity.
- **Paper text change:** Replace "21 systems" with "5 backends" throughout.

### Option B: Run Additional Backends
- **Scope:** Add 4-6 more free backends from OpenRouter (e.g., deepseek-r1:free, llama-4-maverick:free, gemini-2.0-flash:free, qwen3:8b)
- **Advantages:** Broader coverage, addresses reviewer concern directly.
- **Disadvantages:** 
  - Additional time (~2-3 hours per backend for all 6 tiers)
  - Some backends may have rate limits or DNS issues (as seen with gemma-4-31b-it:free)
  - Tier-4A and Tier-5 would need to be re-run for new backends
- **Cost:** $0 (all free tier)

## Recommendation

**Option A** is recommended for the following reasons:
1. The 5 evaluated backends already span 3 distinct model families with diverse architectures
2. The key findings (metadata gap, tool augmentation benefit, CoT non-determinism) are consistent across backends
3. The paper's contribution is the evaluation methodology and tier framework, not the number of backends
4. Running 16 additional backends would take ~20+ hours and may not change headline findings

**If Reviewer #4.4 insists on more backends**, suggest adding 3-4 high-quality free backends (deepseek-r1:free, llama-4-maverick:free, gemini-2.0-flash:free) as a compromise, focusing on Tier-1 and Tier-3 only.

---
*This note is for human decision. Do not run additional backends until explicitly confirmed.*
