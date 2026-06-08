# ACTS R3 v2 Final — Runtime Status
## 2026-06-01 ~21:30 UTC

### Matrix Run: PID 335809 (1h 28min runtime)

**Completed:**
- gemma4 T1: 140/140 ✅ (0 errors)
- gemma4 T2: 140/140 ✅ (0 errors)  
- gemma4 T3: 140/140 ✅ (0 errors, both stats_only + tier3_raw variants)

**In Progress:**
- gemma4 T4A: 81/140 good (13 errors, all HTTP 429 rate limits)

**Not Started:**
- gemma4 T5, gpt-oss, nemotron, minimax-m3, owl-alpha, gemma-free (all tiers)

### Issue: Ollama Cloud Rate Limits
- HTTP 429 errors on ~14% of T4A calls
- Retry logic: 5 attempts with exponential backoff (6s, 11s, 21s, 41s, 60s)
- DES family files hitting 429s most frequently
- Process is alive and making progress despite delays

### Estimated Completion
At current rate: 6-8 hours remaining for full 6×6 matrix
- gemma4 remaining: ~30 min (T4A+T5 with retries)
- 5 other backends: ~5-7 hours

### Scripts Ready
- `compute_unified_stats_v2_final.py` ✅ tested
- `per_family_v2_final.py` ✅ tested
- Both will run immediately on completion

### Key Partial Results (gemma4 only)
- T1: 100% (140/140)
- T2: 100% (140/140)
- T3: ~5% (6/124 so far in partial run)
- T1→T3 gap: ~95pp ✅
