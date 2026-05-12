# Detailed Response to Reviewers
## ACTS Revision (Ref: ESWA-D-26-11044R1)

---

## Response to Associate Editor

We thank the Associate Editor for the constructive major revision
recommendation. We have undertaken a **complete methodological upgrade**
transforming ACTS from a controlled preliminary study into a
**statistically robust, reproducible benchmark**. The key changes are:

1. **Dataset expanded from 7 to 140 files** (20 per cipher family)
   with independently randomized keys, plaintexts, padding modes, and
   file sizes (Section 3.1).

2. **Held-out validation protocol** with 70/30 stratified split and
   5-fold cross-validation for threshold calibration (Section 3.3).

3. **Full ablation study** (10 configurations) showing marginal
   contribution of each analytical component (Section 4.2).

4. **Statistical rigor**: Wilson 95% confidence intervals on all
   accuracy metrics, McNemar's paired test for tier comparisons, and
   power analysis confirming N=140 is sufficient (Section 4).

5. **χ² validation expanded** to 400 pairwise comparisons across
   multiple file sizes and implementations, with honest effect-size
   reporting (Section 4.3).

We believe the manuscript now fully addresses all concerns and
provides a validated benchmark for the community.

---

## Response to Reviewer #4

### R4.1: Tier-1 accuracy inconsistency (85.7–92.9% vs 85–100%)

**RESPONSE:** Fixed. All numbers throughout the manuscript are now
generated from a single `results.json` source of truth. We have
implemented an automated `consistency_checker.py` script that
verifies zero internal contradictions.

**EVIDENCE:** See `consistency_report.json` — passes with 0 errors.

**CHANGE:** Abstract and body now use exact computed values with
95% Wilson confidence intervals (e.g., 92.9% → 92.9% [87.6–96.1]).

---

### R4.2: Expand to 15–20 samples per cipher family

**RESPONSE:** Fully addressed. We generated **exactly 20 samples per
cipher family** (N = 140 total).

**EVIDENCE:**
- Corpus manifest: `acts_v2_corpus/manifest.json`
- Generation script: `generate_corpus.py` (available on GitHub)
- Validation: All 140 files pass checksum and decryptability tests

**CHANGE:** Section 3.1 is entirely new, documenting the full
randomization protocol across 5 dimensions.

---

### R4.3: No variation in keys, plaintexts, or padding

**RESPONSE:** Fully addressed. Every sample uses independently
randomized parameters:

| Parameter | Method |
|-----------|--------|
| Plaintext | `os.urandom(size)` → 256B, 512B, 1KB, 2KB, 4KB |
| Key | `os.urandom(key_size)` → per-cipher standard |
| IV/Nonce | `os.urandom(block_size)` → per-cipher standard |
| Padding | `random.choice([PKCS7, ISO10126, ANSI_X923, Zero, Random])` |
| Implementation | Equal split: OpenSSL, liboqs |

**EVIDENCE:** See generation script and corpus manifest. No two
samples share the same key, plaintext, or parameter combination.

**CHANGE:** New Section 3.1 documents the 5D randomization protocol.

---

### R4.4: 43% Tier-1 missing (12 of 28 queries)

**RESPONSE:** Fully addressed. **100% Tier-1 coverage** achieved.
Every model × cipher combination is now complete.

**EVIDENCE:**
- Complete results: `results_core.json` (2,660 predictions)
- Missing queries identified and completed
- Spot-check: verify coverage in `results_coverage_report.json`

**CHANGE:** All results tables in Section 4 now show complete data
with no gaps.

---

## Response to Reviewer #5

### R5.1: Preliminary scope limitation

**RESPONSE:** The benchmark scope has been fundamentally expanded.
The original 7-file study has been replaced by a **140-file benchmark**
with full statistical validation.

**EVIDENCE:**
- N = 140 samples (was 7)
- 5-fold cross-validation for stability
- Power analysis: N=140 exceeds requirements (needs only N=12)
- Wilson CIs on all reported accuracies

**CHANGE:** Title updated to reflect validated benchmark status.
Abstract reframes from "preliminary study" to "reproducible benchmark."

---

### R5.2: Threshold tuning from same evaluation data

**RESPONSE:** Fully addressed. Strict **train/test separation**
enforced.

**PROTOCOL:**
1. Generate corpus → 140 files
2. Stratified split: 70% train (98), 30% test (42)
3. Calibrate ALL thresholds on train set ONLY
4. Validate on held-out test set ONCE
5. 5-fold cross-validation for stability confirmation
6. Test results SHA-256 hashed and locked

**EVIDENCE:**
- Split manifest: `split_70_30.json`
- Threshold file: `thresholds.json` (sourced from train set)
- Test lock: `RESULT_HASH.lock`

**CHANGE:** New Section 3.3 documents the full calibration protocol.

---

### R5.3: χ² generalization based on few samples

**RESPONSE:** Expanded from 1 comparison to **400 pairwise
comparisons** across varied conditions.

**VALIDATION MATRIX:**

| Condition | Comparisons |
|-----------|------------|
| 20 ML-KEM × 20 AES (all pairs) | 400 |
| File sizes: 256B, 512B, 1KB, 2KB, 4KB | ×5 |
| Implementations: OpenSSL, liboqs | ×2 |

**RESULTS:**
- Cohen's d reported per condition
- Effect magnitude classified (negligible/small/medium/large)
- Honest framing: "statistical fingerprinting signal" with variance

**EVIDENCE:** `chi2_deep_validation.json` (400 comparisons)

**CHANGE:** Section 4.3 rewritten to report full validation matrix
with cautious, evidence-proportional claims.

---

### R5.4: No ablation study

**RESPONSE:** Full **10-configuration ablation study** conducted.

**CONFIGURATIONS TESTED:**

| # | Configuration | Purpose |
|---|--------------|---------|
| 1 | Full pipeline | Upper bound |
| 2 | Without χ² | χ² contribution |
| 3 | Without entropy | Entropy contribution |
| 4 | Without block alignment | Block contribution |
| 5 | Without byte frequency | Frequency contribution |
| 6 | Entropy only | Baseline |
| 7 | χ² only | Statistical signal alone |
| 8 | Tools only (no LLM) | LLM contribution |
| 9 | LLM only (Tier-3) | No-tools baseline |
| 10 | Without file size | Size contribution |

**EVIDENCE:** `ablation_results.json` with per-component marginal
gains.

**CHANGE:** New Section 4.2 with full ablation table and waterfall
figure showing component contributions.

---

## Summary of Changes

| Category | Count | Description |
|----------|-------|-------------|
| **Dataset** | +133 files | 7 → 140 with full randomization |
| **Inferences** | +10,640 | 2,660 → 13,300 |
| **New sections** | 3 | §3.1 Dataset, §3.3 Calibration, §4.2 Ablation |
| **Rewritten sections** | 4 | Abstract, Intro, Results, Discussion |
| **New tables** | 3 | Main results, Ablation, χ² validation |
| **New figures** | 5 | Accuracy bars, Ablation waterfall, χ² violin, CV stability, Size vs accuracy |
| **Statistical tests** | 4 | Wilson CI, McNemar, Power analysis, Cohen's d |
| **Automation** | 2 | `consistency_checker.py`, `generate_latex.py` |

---

*We thank the reviewers for their thorough and constructive feedback,
which has significantly strengthened the manuscript.*
