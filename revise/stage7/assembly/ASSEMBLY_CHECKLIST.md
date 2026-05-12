# ACTS v2 Assembly Checklist

## Stage 7: Final Assembly & Pre-Submission Validation

**Date:** 2026-05-10  
**Manuscript ID:** ESWA-D-26-11044R1  
**Status:** Ready for Submission

---

## Deliverables Inventory

### Core Documents
- [x] `REBUTTAL_LETTER_FINAL.md` — Point-by-point response to both reviewers (+ AE cover)
- [x] `ABSTRACT_FINAL.md` — Updated abstract with real empirical findings
- [x] `RESULTS_AND_DISCUSSION_FINAL.md` — Full results section with 161 real inferences
- [x] `TABLES_FINAL.tex` — All 5 LaTeX tables (multimodel, Wilson CI, McNemar, biases, ablation)

### Data & Results
- [x] 140 ciphertext files (`stage1_data/corpus/*.bin`)
- [x] Corpus manifest with full provenance (`manifest.json`)
- [x] 14 test-sample mapping (`corpus_14_sample_mapping.json`)
- [x] Ollama results: `gemma4_corpus14.json` (42 tests)
- [x] Ollama results: `gptoss_corpus14.json` (42 tests)
- [x] Ollama results: `nemotron_all_tiers.json` (21 tests) + `nemotron_corpus14_tier3only.json` (14 tests)
- [x] OpenRouter results: `openrouter_tier3_batch1.json` (42 tests)
- [x] Final merged summary: `FINAL_RESULTS_SUMMARY.json`

### Validation Studies
- [x] χ² validation: 400 comparisons (`chi2_results.json`)
- [x] Ablation study: 10 configurations (`ablation_results.json`)
- [x] Statistical analysis: Wilson CI, McNemar, power analysis
- [x] Consistency check: `consistency_checker.py` (0 errors)

### Automation Scripts
- [x] `generate_corpus.py` — 140-file corpus generation
- [x] `split_protocol.py` — Stratified split + 5-fold CV
- [x] `chi2_validator.py` — 400 pairwise χ² comparisons
- [x] `ablation_runner.py` — 10-configuration ablation
- [x] `statistical_analysis.py` — Wilson CI, McNemar, power
- [x] `consistency_checker.py` — Cross-file number validation
- [x] `ollama_benchmark_runner.py` — Zero-cost local inference
- [x] `openrouter_benchmark_runner.py` — Free cloud inference
- [x] `generate_latex_tables.py` — LaTeX table generation
- [x] `generate_figures.py` — Publication figures ( matplotlib)

### Figures
- [x] `figure1_accuracy_tiers.png` — Multi-model accuracy bars
- [x] `figure2_confusion_nemotron.png` — Confusion matrix
- [x] `figure3_gap_comparison.png` — Metadata gap comparison

### Reproducibility
- [x] `Dockerfile.eval` — Containerized evaluation environment
- [x] All scripts have `requirements.txt` or explicit dependencies
- [x] All random seeds documented

---

## Cross-Reference Validation

| Manuscript Claim | Source File | Status |
|-----------------|-------------|--------|
| "140 files with 5D randomization" | `manifest.json` | ✅ Verified |
| "161 real inferences" | `FINAL_RESULTS_SUMMARY.json` | ✅ Verified |
| "Tier-1: 100%" | All result files | ✅ Verified |
| "Tier-3 mean: 25.0%" | `FINAL_RESULTS_SUMMARY.json` | ✅ Verified |
| "Metadata gap: 75.0 pp" | Computed from results | ✅ Verified |
| "Wilson CI [0.040, 0.388] for Gemma 4" | `statistical_analysis.py` | ✅ Verified |
| "McNemar p < 0.01" | All 5 models | ✅ Verified |
| "Cohen's d = −0.17" | `chi2_results.json` | ✅ Verified |
| "10 ablation configs" | `ablation_results.json` | ✅ Verified |

---

## Statistics Summary

| Metric | Value |
|--------|-------|
| Total files generated | 160+ |
| Total lines of code | ~2,800 |
| Real LLM inferences | 161 |
| Models tested | 5 |
| API cost | $0 |
| Time invested | ~6 hours |
| Reviewer concerns addressed | 8/8 (100%) |

---

## Submission Package Structure

```
ACTS_v2_Revision_Package/
├── 0_Rebuttal_Letter/
│   └── REBUTTAL_LETTER_FINAL.md
├── 1_Manuscript/
│   ├── ABSTRACT_FINAL.md
│   ├── section3_methodology.md
│   └── RESULTS_AND_DISCUSSION_FINAL.md
├── 2_Tables_and_Figures/
│   ├── TABLES_FINAL.tex
│   ├── figure1_accuracy_tiers.png
│   ├── figure2_confusion_nemotron.png
│   └── figure3_gap_comparison.png
├── 3_Data/
│   ├── corpus_manifest.json
│   ├── corpus_14_sample_mapping.json
│   └── (140 .bin files, if allowed by journal size limits)
├── 4_Results/
│   ├── FINAL_RESULTS_SUMMARY.json
│   ├── gemma4_corpus14.json
│   ├── gptoss_corpus14.json
│   ├── nemotron_all_tiers.json
│   └── openrouter_tier3_batch1.json
├── 5_Code/
│   ├── generate_corpus.py
│   ├── ollama_benchmark_runner.py
│   ├── openrouter_benchmark_runner.py
│   ├── statistical_analysis.py
│   └── (all 7 scripts)
├── 6_Validation/
│   ├── chi2_results.json
│   ├── ablation_results.json
│   └── consistency_report.json
└── 7_Reproducibility/
    └── Dockerfile.eval
```

---

## Pre-Submission Checklist

- [x] All reviewer concerns have explicit responses
- [x] All manuscript numbers match result files
- [x] Statistical tests are properly reported
- [x] Limitations are honestly disclosed
- [x] Code is documented and runnable
- [x] Data is available and checksum-verified
- [ ] **NEED:** Merge all manuscript sections into single LaTeX file ( Stage 8)
- [ ] **NEED:** Final proofread by co-authors
- [ ] **NEED:** Convert figures to journal-required format (EPS/TIFF)
- [ ] **NEED:** Generate PDF from LaTeX and verify layout

---

## Next Steps (Stage 8)

1. Insert LaTeX tables into manuscript `.tex` file
2. Insert figure references into manuscript
3. Final co-author review
4. Generate submission PDF
5. Upload to ESWA editorial system

**Status: Stage 7 Complete. Ready for Stage 8 (Submission).**
