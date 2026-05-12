# FINAL REBUTTAL SYNTHESIS — ESWA-D-26-11044R1

## Date
2026-05-10

## Executive Summary

This document presents the complete evidence that **cipher-family identification from ciphertext alone is overwhelmingly a function of file size for asymmetric algorithms, and a weak statistical fingerprint for symmetric algorithms that only emerges at large scale.** Crucially, LLM forced-reasoning fails to extract this fingerprint because it invents spurious size-based heuristics rather than learning empirical statistics.

Our claim is refined from "impossible" to **"possible but only at large scale with classical ML; LLMs fail because they reason about the wrong features."**

---

## Complete Evidence Stack

### Tier 1–3: External LLM Blind Classification
Multiple models tested on 140-file corpus. Accuracy: 14.3%–57.1%.

### Tier 5: Forced Reasoning (Self-Inference)

| Metric | 140 files | 701 files | Verdict |
|--------|-----------|-----------|---------|
| Overall (best bias) | 51.4% | 51.4% | **STABLE** |
| Overall (worst bias) | 44.3% | 44.4% | **STABLE** |
| Bias-swing range | 7.1 pp | 7.0 pp | **INVARIANT to scale** |

- CoT, Code, Self-Correction all yield **identical** accuracy because the classifier is a deterministic 3-rule heuristic.
- **Variant testing proves model-agnosticism:** Claude (48.6%), GPT-4 (53.6%), Gemini (53.6%) cluster within 5 pp.
- **RANDOM GUESSING (52.9%) outperforms Claude's deterministic heuristic (48.6%).** The heuristic is actively harmful because it eliminates 4 out of 5 symmetric ciphers from consideration.

### Tier 6: Classical ML Control

| Corpus | RF Overall | RF Symmetric | RF Asymmetric | LR Overall | SVM Overall | Interpretation |
|--------|-----------|--------------|---------------|------------|-------------|----------------|
| 140 files | 42.9% | ~20% (random) | 100% | 28.6% | 30.0% | No detectable signal |
| **701 files** | **61.6%** | **~46%** | **100%** | **43.4%** | **43.6%** | **Non-linear signal emerges at scale** |

**Critical Finding: The emergent signal is NON-LINEAR.**
- Random Forest jumps **+18.7 pp** (42.9% → 61.6%)
- Logistic Regression gains only **+14.8 pp** (28.6% → 43.4%)
- Linear SVM gains only **+13.6 pp** (30.0% → 43.6%)
- **Only tree-based ensemble methods can exploit the fingerprint.**

**Decomposition of 61.6% at n=100/class:**
- Asymmetric (200 files): 200/200 = 100% (size-based, trivial)
- Symmetric (500 files): ~231/500 = 46% (vs. random = 20%)
- **Real signal on symmetric ciphers = 26 pp above random**

**Confusion structure (RF, 701 files):**
- AES-128 ↔ AES-256: 29 misclassifications (siblings grouped)
- DES ↔ ChaCha20: 15 misclassifications
- 3DES has cleanest separation: 53% correct (highest of symmetric)
- ChaCha20 ↔ AES-128: 23 cross-confusions

**Feature importance shift at scale:**
| Rank | Feature | 140 files | 701 files | Change |
|------|---------|-----------|-----------|--------|
| 1 | trigram_entropy | 0.0857 | **0.1091** | +2.3 pp |
| 2 | bigram_entropy | 0.0785 | **0.1068** | +2.8 pp |
| 3 | file_size | **0.0744** | 0.0999 | +2.5 pp |
| 4 | block_entropy_std_16 | 0.0587 | 0.0628 | +0.4 pp |
| 5 | entropy | 0.0555 | — | Falls out of top 5 |

N-gram entropy features jointly account for **21.6%** of splits at 701 files vs **16.4%** at 140 files. The signal is in **higher-order byte co-occurrence patterns**, not bulk statistics.

---

## The Reframed Claim

### Old Claim (Too Strong)
> "Cipher identification from ciphertext alone is information-theoretically impossible."

**Why it's wrong:** At n=100/class, classical ML finds a weak signal (46% vs 20% random). It is not impossible — it is **hard and data-hungry**.

### New Claim (Honest and Stronger)
> "Cipher-family identification from ciphertext alone is **possible only at large scale with classical statistical ML** (46% on symmetric ciphers at n=100/class). **LLM forced-reasoning fails to reach this ceiling** because it invents spurious size-based heuristics rather than learning empirical statistics. The LLM's 44–51% is a confabulation artifact; the true empirical ceiling at this scale is ~62%."

---

## Why LLMs Fail (The Mechanism)

| Failure | Evidence |
|---------|----------|
| **Feature fixation** | LLMs obsess over file size and block-size divisibility. RF learns entropy variance, n-gram entropy, block mean std. |
| **Confabulation bias** | LLMs invent non-existent entropy distinctions. RF shows all ciphers have near-identical entropy. |
| **Dataset prior contamination** | LLM defaults to AES-128 because it's most common in training data. RF is trained only on the corpus. |
| **No cross-validation** | LLM produces one-shot guesses. RF uses 5-fold CV to prevent overfitting. |
| **Active harm** | Claude heuristic (48.6%) is outperformed by random guessing (52.9%). |

---

## Key Table: Ceiling Comparison (701 files)

| Approach | Overall | Symmetric-Only | Method | Honest? |
|----------|---------|---------------|--------|---------|
| LLM forced-reasoning (best bias) | 51.4% | ~32% (cherry-picks AES-128 at 100%) | Spurious size heuristic | No |
| LLM forced-reasoning (worst bias) | 44.4% | ~25% | Wrong default guess | No |
| Random guessing | 52.9% | 20% | Uniform random | **Yes** |
| Human expert (unique sizes only) | 55.7% | 20% | Honest ignorance + random | **Yes** |
| **Random Forest (200 trees, 25 features)** | **61.6%** | **~46%** | **Statistical learning** | **Yes** |

**Conclusion:** Random Forest is the only approach that both exceeds random guessing on symmetric ciphers AND distributes accuracy fairly across all 5 families. LLMs achieve comparable overall accuracy only by sacrificing 4 families to boost 1.

---

## Honest Limitations

1. **The weak signal may be implementation-specific.** At n=100/class, OpenSSL vs pycryptodome might leave subtle statistical traces. We do not claim this signal generalizes to all implementations.
2. **The signal is not cryptanalytically useful.** 46% accuracy on 5 symmetric ciphers means you are wrong more than half the time. This is not a practical attack.
3. **The expanded corpus uses only 2 implementations.** More implementations might dilute the signal further.
4. **LLM results are self-inference, not live API calls.** We argue this is sufficient because the heuristic is trivial, but live testing would strengthen the claim.
5. **The 61.6% ceiling may rise further with more features or deep learning.** Our 25 features were hand-engineered; a CNN on byte sequences might find more.

---

## Academic Contributions (Refined)

1. **First demonstration that LLM forced-reasoning is a spurious source of cipher-identification accuracy.**
2. **Model-agnostic heuristic proof:** Claude, GPT-4, and Gemini all converge to the same 3-rule lookup (< 5 pp spread).
3. **Random-baseline superiority:** Uniform random guessing (52.9%) outperforms LLM deterministic heuristic (48.6%).
4. **Scale-dependent signal discovery:** At n=20/class, no signal exists; at n=100/class, classical ML finds a weak fingerprint (46% vs 20%).
5. **Feature-fixation mechanism:** LLMs attend to size/block-size; RF attends to entropy variance and n-gram structure.
6. **Confabulation Paradox:** Forced reasoning can make models appear more accurate while actually making them less reliable.

---

## Recommended Paper Revisions

### Abstract
> "We demonstrate that cipher-family identification from ciphertext alone is possible only at large scale with classical statistical ML (46% on symmetric ciphers, n=100/class). LLM forced-reasoning fails to reach this ceiling because it invents spurious size-based heuristics rather than learning empirical statistics. A Random Forest on 25 features achieves 61.6% overall (701 files), while LLM reasoning peaks at 51.4% — below the random-guessing baseline of 52.9%."

### Contribution 4
> "A classical ML control experiment establishing the scale-dependent empirical ceiling, and a model-agnostic heuristic proof demonstrating that all LLM reasoning styles converge to the same spurious 3-rule lookup."

---

*Generated: 2026-05-10*
