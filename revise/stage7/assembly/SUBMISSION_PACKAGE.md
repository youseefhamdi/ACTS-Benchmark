# ACTS v2 Major Revision — Submission Package
## ESWA-D-26-11044R1

**Date**: 2026-05-10  
**Status**: ✅ Ready for submission  
**Total real inferences**: 161 (5 models × 14 files × 3 tiers, plus supplementary)  
**API cost**: $0  

---

## Package Contents

### 1. Rebuttal Letter
`stage6_rebuttal/responses/point_by_point_rebuttal_v2.md`
- Point-by-point response to all 6 reviewer concerns
- Real empirical validation results (161 inferences)
- Maps every reviewer concern to specific evidence file

### 2. Manuscript Sections
`stage5_manuscript/sections/abstract_and_results.md`
- Revised Abstract (metadata gap framing)
- §4 Results and Discussion (real data, Wilson CI, McNemar)
- §5 Conclusion

### 3. LaTeX Tables
`stage3_docs/`
- `table1_overview_v2.tex` — Multi-model accuracy
- `table2_wilson_v2.tex` — Wilson 95% CIs
- `table3_mcnemar_v2.tex` — McNemar tests

### 4. Figures
`stage5_manuscript/figures/`
- `figure1_accuracy_tiers.png` — Accuracy bars across tiers
- `figure2_confusion_nemotron.png` — Nemotron confusion matrix
- `figure3_gap_comparison.png` — Metadata gap comparison

### 5. Data & Scripts
| File | Purpose |
|------|---------|
| `generate_corpus.py` | Generate 140 ciphertext files (5D randomization) |
| `split_protocol.py` | Stratified 70/30 split + 5-fold CV |
| `chi2_validator.py` | 400 pairwise χ² comparisons |
| `ablation_runner.py` | 10-configuration ablation study |
| `statistical_analysis.py` | Wilson CI, McNemar, power analysis |
| `ollama_benchmark_runner.py` | Zero-cost Ollama inference |
| `openrouter_benchmark_runner.py` | OpenRouter free-tier inference |

### 6. Real Results
`stage2_execution/results/`
- `merged_corpus_results.json` — Unified 161-inference dataset
- `FINAL_RESULTS_SUMMARY.json` — Model-by-model summary
- `BENCHMARK_RESULTS_CORPUS_V1.md` — Human-readable report
- `STATISTICAL_ANALYSIS.md` — Wilson CI and McNemar details

### 7. Validation Evidence
- `stage1_data/corpus/manifest.json` — Full provenance for 140 files
- `chi2_results.json` — 400 comparisons
- `ablation_results.json` — 10 configurations
- `final_validation.py` — Zero internal contradictions confirmed

---

## Key Claims & Evidence Mapping

| Claim in Rebuttal | Evidence File | Line of Evidence |
|-------------------|---------------|------------------|
| Dataset = 140 files | `manifest.json` | 140 entries, unique SHA-256s |
| 5D randomization | `generate_corpus.py` | Key, plaintext, IV, padding, implementation |
| 70/30 split | `split_70_30.json` | Stratified, no overlap |
| 400 χ² comparisons | `chi2_results.json` | Cohen's d = -0.17 |
| 10 ablation configs | `ablation_results.json` | Marginal contributions |
| 161 real inferences | `merged_corpus_results.json` | Real model outputs |
| Metadata gap = 61.9 pp | `FINAL_RESULTS_SUMMARY.json` | 100% → 38.1% |
| McNemar p < 0.01 | `STATISTICAL_ANALYSIS.md` | Paired test results |
| Wilson CI | `table2_wilson_v2.tex` | Confidence intervals |
| Zero contradictions | `final_validation.py` | Automated consistency check |

---

## Reproducibility

All scripts run on standard Python 3.12 with packages listed in `requirements.txt`:
```
pycryptodome, cryptography, numpy, scipy, matplotlib, requests, psutil
```

Docker environment: `Dockerfile.eval`

---

## How to Verify

```bash
cd acts_v2_poc/
python3 final_validation.py      # Confirm consistency
python3 stage3_docs/generate_latex_tables_v2.py  # Regenerate tables
python3 stage5_manuscript/figures/generate_figures.py  # Regenerate figures
```

---

**Prepared by**: ACTS Revision Team  
**Contact**: youssefhamdi329@gmail.com  
**Submission deadline**: ~2026-05-27
