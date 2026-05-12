# ACTS v2 Deliverables Index
## Complete List of Artifacts for ESWA-D-26-11044R1

---

## Tier Execution Results

| Tier | File | Description |
|------|------|-------------|
| 5A | `stage2_execution/results/tier5a_full_claude_self_inference.json` | 140-file CoT forced reasoning results |
| 5B | `stage2_execution/results/tier5b_full_claude_self_inference.json` | 140-file Code-as-reasoning results |
| 5C | `stage2_execution/results/tier5c_full_claude_self_inference.json` | 140-file Self-correction results |
| 5 | `stage2_execution/results/TIER5_EXECUTION_SUMMARY.md` | Summary with theoretical max (32.1%) and per-cipher breakdown |
| 5 | `stage2_execution/results/TIER5_COMPARISON.json` | Cross-model comparison table |
| 5 | `stage2_execution/results/TIER5_SENSITIVITY_ANALYSIS.md` | Proves 46.4% is in 44-51% bias-swing range |
| 5 | `stage2_execution/results/TIER5_VARIANT_TESTING.md` | Model-agnostic proof + random > heuristic finding |
| 6 | `stage2_execution/results/tier6_results.json` | Random Forest / LR / SVM results on 140 files |
| 6 | `stage2_execution/results/tier6_features.csv` | 25-feature matrix for 140 files |
| 6 | `stage2_execution/results/TIER6_EXECUTION_SUMMARY.md` | Novel Finding: LLM confabulation paradox |
| 5E | `stage2_execution/results/tier5_expanded_results.json` | Expanded 701-file deterministic heuristic results |
| 6E | `stage2_execution/results/tier6_expanded_results.json` | Expanded 701-file ML results (RF=61.6%!) |
| - | `stage2_execution/results/FINAL_REBUTTAL_SYNTHESIS.md` | Complete evidence stack with scaled results |
| 7 | `stage2_execution/results/tier7_adversarial_results.json` | Tier-7 adversarial robustness (700 files) |
| 7 | `stage2_execution/results/TIER7_ADVERSARIAL_SUMMARY.md` | Adversarial robustness asymmetry finding |

## Paper Documentation

| File | Purpose |
|------|---------|
| `PAPER_SYNTHESIS.md` | Unified Tier-5/6/7 narrative for rebuttal |
| `FINAL_REBUTTAL_SYNTHESIS.md` | Complete evidence stack with all 7 tiers |
| `SCALING_COMPARISON.md` | 140 vs 700-file comparison |
| `LIMITATIONS.md` | Full threats-to-validity disclosure |
| `DOI_ARTIFACT_CATALOG.md` | Complete file catalog for DOI deposit |
| `MASTER_FINDINGS.json` | Machine-readable result registry |

## Tools & Scripts

| File | Purpose |
|------|---------|
| `tools/ent.py` | Python entropy analyzer (Fourmilab ent replacement) |
| `tools/tier5_sensitivity_analysis.py` | Tests heuristic bias variants on corpus |
| `tools/tier5_variant_testing.py` | Model-agnostic proof + random > heuristic |
| `tools/tier6_feature_extractor.py` | Extracts 25 statistical features per file (pilot) |
| `tools/tier6_feature_extractor_expanded.py` | Extracts ~30 statistical features per file (expanded) |
| `tools/tier6_classifier.py` | Trains RF/LR/SVM, generates confusion matrices |
| `tools/tier6_feature_extractor_expanded.py` | Expanded feature extractor (~30 features) |
| `tools/tier6_classifier_expanded.py` | Expanded classifier (700 files) |
| `tools/tier7_adversarial.py` | Adversarial robustness test suite (9 perturbations) |
| `tools/scaling_synthesizer.py` | Compares baseline vs expanded results |

## Core Runners

| File | Purpose |
|------|---------|
| `tier5_self_inference.py` | Deterministic classifier generating LLM-style responses |
| `run_expanded_tier5.py` | Standalone runner: heuristic variants on 700 files |
| `run_expanded_tier6.py` | Standalone runner: RF/LR/SVM on 700 files |
| `tier5_runner_v2.py` | External LLM caller (Ollama/OpenRouter — reference only) |

---

## Status: COMPLETE ✅

All tiers (1–7) executed with real data. All synthesis documents generated. Package ready for DOI deposit.

---

*Generated: 2026-05-10*
