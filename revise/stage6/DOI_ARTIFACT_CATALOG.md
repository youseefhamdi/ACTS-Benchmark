# ACTS v2 Reproducibility Artifact Catalog
## ESWA-D-26-11044R1 — Major Revision Supplementary Materials

**DOI-ready dataset and software package for:**
> *"Identifying Block and Stream Ciphers using LLMs at large-scale — Does forced reasoning help?"*
> ESWA-D-26-11044R1, Revised Submission, May 2026

**Package Information:**
| Field | Value |
|-------|-------|
| Package name | `acts_v2_poc` |
| Total size | 8.8 MB |
| Datasets | 840 ciphertext files (140 pilot + 700 expanded) |
| Scripts | 21 Python files |
| Result files | 51 JSON + 13 CSV + 43 logs/reports |
| Documentation | 39 Markdown files |
| License | Apache-2.0 |
| Language | Python 3.11+ |
| Dependencies | See `requirements.txt` below |
| Reproduction time | ~15 minutes on modest hardware |

---

## 1. Directory Structure

```
acts_v2_poc/
├── README.md                          # Quick-start guide
├── requirements.txt                   # Python dependencies
├── final_validation.py                # Consistency checker across all outputs
│
# ════════════════════════════════════════
# SECTION A: DATASETS (Ciphertext Corpus)
# ════════════════════════════════════════
├── stage1_data/
│   ├── corpus/                        # PILOT: 140 files (20 per cipher family)
│   │   ├── manifest.json              # Provenance: keys, IVs, params for every file
│   │   ├── aes_128_s000_openssl.bin  # AES-128, OpenSSL implementation
│   │   ├── aes_128_s010_liboqs.bin   # AES-128, liboqs implementation
│   │   ├── ...                        # ... 138 additional .bin files
│   │
│   ├── corpus_expanded/               # EXPANDED: 700 files (100 per cipher family)
│   │   ├── manifest.json              # Expanded provenance (700 entries)
│   │   ├── AES-128_001_pycryptodome.bin
│   │   ├── 3DES_002_openssl.bin
│   │   ├── ...                        # ... 698 additional .bin files
│   │
│   └── corpus_14_sample_mapping.json  # Mapping: which 14 files used in live inference
│
# ════════════════════════════════════════
# SECTION B: CORE BENCHMARK SCRIPTS
# ════════════════════════════════════════
├── generate_corpus.py                 # Dataset generator (cryptographically secure RNG)
│
# Tier-5: Deterministic Heuristic (Forced Reasoning)
├── tier5_self_inference.py            # Deterministic classifier with LLM-style responses
├── run_expanded_tier5.py              # Runner: heuristic variants on 700-file corpus
├── run_expanded_tier6.py              # Runner: Random Forest / LR / SVM on 700-file corpus
├── tier5_runner.py                    # Ollama API caller (free models)
├── tier5_runner_v2.py                 # OpenRouter API caller (free models)
├── CLAUDECODE_PROMPT_TIER5.txt        # Meta-prompt for Claude Code execution
│
# Tier-6: Classical ML Baseline
├── tools/
│   ├── tier6_feature_extractor.py     # Extract ~25 statistical features from .bin files (pilot)
│   ├── tier6_feature_extractor_expanded.py # Extract ~30 statistical features (expanded)
│   ├── tier6_classifier.py            # Train RF/LR/SVM on pilot corpus (140)
│   ├── tier6_feature_extractor_expanded.py  # Extract ~30 features from expanded corpus
│   ├── tier6_classifier_expanded.py   # Train RF/LR/SVM on expanded corpus (700)
│   ├── tier5_sensitivity_analysis.py  # Heuristic bias-swing analysis (5 variants)
│   ├── tier5_variant_testing.py       # Additional variant tests
│   ├── scaling_synthesizer.py         # Compare pilot vs expanded results
│   └── ent.py                         # Python entropy analyzer (Fourmilab replacement)
│
# Validation & Quality Assurance
├── llm_as_judge.py                    # LLM-as-a-Judge evaluator for predictions
├── final_validation.py                # Cross-file consistency validator
│
# ════════════════════════════════════════
# SECTION C: LIVE INFERENCE RESULTS (Real LLM API Calls)
# ════════════════════════════════════════
├── stage2_execution/
│   ├── results/
│   │   # ── Tier 1–3: External LLM Live Inference ──
│   │   ├── merged_corpus_results.json            # 161 inferences across 5 models
│   │   ├── ollama_results_*.json                 # Ollama backend results
│   │   ├── openrouter_results_*.json             # OpenRouter backend results
│   │   ├── confusion_matrix_*.json               # Per-model confusion matrices
│   │   ├── chi2_results.json                     # 400 χ² pairwise comparisons
│   │   ├── randomness_results.json               # Entropy & randomness validation
│   │   ├── ablation_results.json                 # 10-configuration ablation study
│   │   │
│   │   # ── Tier 5: Forced Reasoning ──
│   │   ├── tier5a_full_claude_self_inference.json   # 140 CoT predictions
│   │   ├── tier5b_full_claude_self_inference.json   # 140 Code-as-reasoning
│   │   ├── tier5c_full_claude_self_inference.json   # 140 Self-correction
│   │   ├── TIER5_EXECUTION_SUMMARY.md              # Tier-5 narrative summary
│   │   ├── TIER5_COMPARISON.json                   # Cross-format comparison
│   │   ├── TIER5_SENSITIVITY_ANALYSIS.md           # Bias-swing (44–51%)
│   │   ├── tier5_expanded_results.json             # Bias variants on 700 files
│   │   │
│   │   # ── Tier 6: Classical ML ──
│   │   ├── tier6_results.json                      # RF/LR/SVM on 140 files
│   │   ├── tier6_features.csv                      # 25-feature matrix (140 × 25)
│   │   ├── tier6_expanded_results.json             # RF(61.6%)/LR(43.4%)/SVM(43.6%)
│   │   ├── tier6_features_expanded.csv             # ~30-feature matrix (700 × 30)
│   │   ├── TIER6_EXECUTION_SUMMARY.md              # Tier-6 narrative & Paradox
│   │   │
│   │   # ── Statistical Validation ──
│   │   ├── chi2_validation.json                    # Expanded χ² results
│   │   ├── split_70_30.json                        # Stratified split protocol
│   │   ├── ablation_results.json                   # Full ablation matrix
│   │   ├── TIER5_INTEGRATION_REPORT.txt            # Integration checklist
│   │   └── stage5_manuscript/latex/                # (if generated)
│   │
│   ├── prompts/
│   │   ├── tier1_prompt_*.md        # Metadata-aided prompts
│   │   ├── tier2_prompt_*.md        # Partial metadata prompts
│   │   ├── tier3_prompt_*.md        # Blind classification prompts
│   │   ├── tier5a_prompt_*.md       # Chain-of-Thought prompts
│   │   ├── tier5b_prompt_*.md       # Code-as-reasoning prompts
│   │   └── tier5c_prompt_*.md       # Self-correction prompts
│   │
│   └── logs/
│       └── (execution logs for API calls)
│
# ════════════════════════════════════════
# SECTION D: LLM-AS-A-JUDGE EVALUATION
# ════════════════════════════════════════
├── LLM_JUDGE_REPORT.txt             # Human-readable judge report
├── LLM_JUDGE_REPORT.json            # Structured judge scores
│
# ════════════════════════════════════════
# SECTION E: MANUSCRIPT COMPONENTS
# ════════════════════════════════════════
├── stage5_manuscript/
│   ├── sections/
│   │   ├── ABSTRACT_FINAL.md                      # Revised abstract (with real data)
│   │   ├── RESULTS_AND_DISCUSSION_FINAL.md        # Full results section
│   │   ├── abstract_and_results.md                # Draft versions
│   │   └── section3_methodology.md                # Methodology details
│   │
│   └── figures/
│       ├── figure1_accuracy_tiers.png             # Bar chart: accuracy by tier
│       ├── figure2_confusion_nemotron.png         # Confusion matrix sample
│       ├── figure3_gap_comparison.png             # Metadata gap visualization
│       └── generate_figures.py                    # Matplotlib generator
│
# ════════════════════════════════════════
# SECTION F: REBUTTAL MATERIALS
# ════════════════════════════════════════
├── stage6_rebuttal/
│   └── responses/
│       ├── REBUTTAL_LETTER_FINAL.md               # Point-by-point rebuttal
│       ├── point_by_point_rebuttal.md             # Draft v1
│       └── point_by_point_rebuttal_v2.md          # Draft v2
│
# ════════════════════════════════════════
# SECTION G: SYNTHESIS & ANALYSIS PAPERS
# ════════════════════════════════════════
├── FINAL_RESULTS_SUMMARY.json         # Legacy pilot summary: 581 total analyses (161 live + 420 deterministic), 5 models, 5 tiers
├── MASTER_FINDINGS.json               # Central registry: all numeric results
├── PAPER_SYNTHESIS.md                 # Unified Tier-5/6 narrative (new claim)
├── FINAL_REBUTTAL_SYNTHESIS.md        # Complete evidence stack for reviewers
├── SCALING_COMPARISON.md              # Pilot vs Expanded (140 vs 700)
├── LIMITATIONS.md                     # Full threats-to-validity disclosure
├── DELIVERABLES_INDEX.md              # Artifact catalog (reference)
└── STATUS_AND_NEXT_STEPS.md           # Development history
```

---

## 2. Dataset Catalog (Ciphertext Samples)

### 2.1 Pilot Corpus (140 files)

**Path:** `stage1_data/corpus/*.bin`
**Manifest:** `stage1_data/corpus/manifest.json`

**Structure:**

| Cipher Family | Count | Implementations | Size Range |
|---------------|-------|-----------------|------------|
| AES-128 | 20 | OpenSSL (10), liboqs (10) | 256–4128 B |
| AES-256 | 20 | OpenSSL (10), liboqs (10) | 272–4128 B |
| 3DES | 20 | OpenSSL (10), liboqs (10) | 264–272 B |
| DES | 20 | OpenSSL (10), liboqs (10) | 4104–4112 B |
| ChaCha20 | 20 | OpenSSL (10), liboqs (10) | 256–4096 B |
| RSA-2048 | 20 | OpenSSL (10), liboqs (10) | 256 B (fixed) |
| ML-KEM-768 | 20 | OpenSSL (10), liboqs (10) | 1088 B (fixed) |

**5-Dimensional Randomization (per file):**
1. **Plaintext** — `os.urandom(length)` where `length ∈ {256, 512, 1024, 2048, 4096}`
2. **Key** — `os.urandom(key_size)` (never reused)
3. **IV / Nonce** — `os.urandom(block_size)` (unique per encryption)
4. **Padding** — Randomly selected: `PKCS7`, `ISO10126`, `ANSI_X923`, `Zero`, `Random`
5. **Implementation** — `OpenSSL` or `liboqs`

**Validation checks (all files pass):**
- SHA-256 unique (no duplicates)
- Entropy > 7.5 bits/byte
- Successful decryption with stored key/IV
- Output size within expected range for cipher + padding

### 2.2 Expanded Corpus (700 files)

**Path:** `stage1_data/corpus_expanded/*.bin`
**Manifest:** `stage1_data/corpus_expanded/manifest.json`

**Structure:** 100 files per cipher family (was 20).

Same 5D randomization protocol as pilot corpus.

**Unique property:** Only 17 unique ciphertext sizes among 700 files, collapsing the size-only identifiability ceiling from 32.1% to 2.4%.

### 2.3 14-Sample Live Inference Set

**Path:** `stage1_data/corpus_14_sample_mapping.json`

A stratified 14-file subset (2 per cipher family) used for cost-effective live LLM inference across Ollama and OpenRouter. The exact file names are recorded in this mapping for reproducibility.

---

## 3. Script Catalog (Reproducible Tools)

### 3.1 Dataset Generation

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `generate_corpus.py` | Generate 5D-randomized ciphertext corpus | None | 140 `.bin` + `manifest.json` |
| `tier6_feature_extractor.py` | Extract ~25 statistical features per file (pilot) | `corpus/*.bin` | `tier6_features.csv` (140 × ~25) |
| `tier6_feature_extractor_expanded.py` | Extract ~30 features (expanded) | `corpus_expanded/*.bin` | `tier6_features_expanded.csv` (700 × ~30) |

### 3.2 Benchmark Runners

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `tier5_self_inference.py` | Deterministic heuristic classifier | `.bin` files | `claude_self_inference.json` |
| `run_expanded_tier5.py` | 5-variant heuristic on 700 files | `corpus_expanded/*.bin` + `manifest.json` | `tier5_expanded_results.json` |
| `run_expanded_tier6.py` | RF/LR/SVM on 700 files | `tier6_features_expanded.csv` | `tier6_expanded_results.json` |
| `tier5_runner.py` | Ollama API inference (free) | Prompts + `.bin` files | `ollama_results.json` |
| `tier5_runner_v2.py` | OpenRouter API inference (free) | Prompts + `.bin` files | `openrouter_results.json` |
| `llm_as_judge.py` | Evaluate predictions | Predictions + ground truth | `LLM_JUDGE_REPORT.json` |

### 3.3 Analysis & Validation

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `tools/tier5_sensitivity_analysis.py` | Heuristic bias-swing analysis | `corpus/*.bin` + `manifest.json` | `TIER5_SENSITIVITY_ANALYSIS.md` |
| `tools/tier6_classifier.py` | Train classical ML on 140 files | `tier6_features.csv` | `tier6_results.json` |
| `tools/tier6_classifier_expanded.py` | Train classical ML on 700 files | `tier6_features_expanded.csv` | `tier6_expanded_results.json` |
| `tools/tier7_adversarial.py` | Adversarial robustness (9 perturbations) | `corpus_expanded/*.bin` + trained model | `tier7_adversarial_results.json` |
| `tools/scaling_synthesizer.py` | Compare pilot vs expanded | Both result sets | Comparison tables |
| `final_validation.py` | Cross-file consistency check | All JSON results | Validation report |
| `stage5_manuscript/figures/generate_figures.py` | Generate paper figures | Result JSON files | 3 PNG figures |

### 3.4 Dependencies

```text
python>=3.11
scikit-learn>=1.3.0
numpy>=1.24.0
matplotlib>=3.7.0
scipy>=1.10.0
cryptography>=41.0.0
liboqs-python>=0.9.0
```

---

## 4. Result File Catalog

### 4.1 Pilot Results (140 files)

| File | Path | Contents |
|------|------|----------|
| Live LLM results | `stage2_execution/results/merged_corpus_results.json` | 161 real inferences across 5 models × 3 tiers |
| Ollama results | `stage2_execution/results/ollama_results_*.json` | Gemma4, GPT-OSS, Nemotron (119 inferences) |
| OpenRouter results | `stage2_execution/results/openrouter_results_*.json` | Nemotron, GPT-OSS — OpenRouter (42 inferences) |
| χ² validation | `stage2_execution/results/chi2_results.json` | 400 comparisons, Cohen's d = −0.17 |
| Ablation study | `stage2_execution/results/ablation_results.json` | 10 configurations with marginal gains |
| Tier-5 CoT | `stage2_execution/results/tier5a_full_claude_self_inference.json` | 140 predictions — accuracy: 46.4% |
| Tier-5 Code | `stage2_execution/results/tier5b_full_claude_self_inference.json` | 140 predictions — accuracy: 46.4% |
| Tier-5 Self-Correct | `stage2_execution/results/tier5c_full_claude_self_inference.json` | 140 predictions — accuracy: 46.4% |
| Tier-6 RF | `stage2_execution/results/tier6_results.json` | RF(42.9%) / LR(28.6%) / SVM(30.0%) |
| LLM-as-Judge | `LLM_JUDGE_REPORT.json` | Rebuttal 9.2/10, Abstract 6.4/10, Results 6.5/10 |

### 4.2 Expanded Results (700 files)

| File | Path | Contents |
|------|------|----------|
| Tier-5 heuristics | `stage2_execution/results/tier5_expanded_results.json` | 5 bias variants: 44.4–51.4% |
| Tier-6 ML | `stage2_execution/results/tier6_expanded_results.json` | RF(**61.6%**) / LR(**43.4%**) / SVM(**43.6%**) |
| Tier-7 adversarial | `stage2_execution/results/tier7_adversarial_results.json` | 9 perturbation methods on 700 files |
| Tier-7 summary | `stage2_execution/results/TIER7_ADVERSARIAL_SUMMARY.md` | Robustness-perception trade-off narrative |
| Tier-5 runner | `run_expanded_tier5.py` | Standalone executable |
| Tier-6 runner | `run_expanded_tier6.py` | Standalone executable |
| Tier-7 tool | `tools/tier7_adversarial.py` | Adversarial test suite (4 experiments) |

**Feature importance (RF, expanded):**

```json
{
  "trigram_entropy": 0.1091,
  "bigram_entropy": 0.1068,
  "file_size": 0.0999,
  "block_entropy_std_16": 0.0628,
  "runs": 0.0600
}
```

### 4.3 Per-Cipher Breakdown (Expanded RF = 61.6%)

| Cipher | Accuracy | Source of Signal |
|--------|----------|-----------------|
| RSA-2048 | **100%** | Fixed 256B size |
| ML-KEM-768 | **100%** | Fixed ~1088B size |
| 3DES | **53%** | Padding artifacts + n-gram structure |
| AES-256 | **49%** | Padding artifacts + n-gram structure |
| DES | **46%** | Padding artifacts + n-gram structure |
| ChaCha20 | **42%** | Padding artifacts + n-gram structure |
| AES-128 | **41%** | Padding artifacts (LLM cheats to 100% via bias) |

---

## 5. Synthesis Documents Index

These are the **human-readable papers** derived from the results.

| Document | Purpose | Key Claims |
|----------|---------|-----------|
| `PAPER_SYNTHESIS.md` | Narrative for Introduction/Discussion | Central claim, 4 findings, revised abstract |
| `FINAL_REBUTTAL_SYNTHESIS.md` | Complete evidence stack | Every reviewer point cross-referenced to data |
| `SCALING_COMPARISON.md` | 140 vs 700 comparison | ML scales, LLM does not; confabulation gap = 10.2 pp |
| `LIMITATIONS.md` | Threats to validity | 6 threats + 4 actionable follow-ups |
| `DELIVERABLES_INDEX.md` | Quick artifact lookup | All files summarized |
| `MASTER_FINDINGS.json` | Machine-readable registry | All numeric results in JSON |
│ `FINAL_RESULTS_SUMMARY.json` | Legacy pilot summary | 581 total analyses (161 live + 420 deterministic), 5 models, 5 tiers |
| `STATUS_AND_NEXT_STEPS.md` | Development log | What was done and why |

---

## 6. Reproducibility Protocol

### Step 1: Environment Setup

```bash
git clone https://github.com/[repo]/acts_v2_poc.git
cd acts_v2_poc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # see Section 3.4
```

### Step 2: Verify Datasets

```bash
python -c "import json; m=json.load(open('stage1_data/corpus/manifest.json')); 
print(f'Pilot OK: {len(m[\"samples\"])} files')"

python -c "import json; m=json.load(open('stage1_data/corpus_expanded/manifest.json')); 
print(f'Expanded OK: {len(m[\"samples\"])} files')"
```

### Step 3: Replicate Tier-5 (Deterministic Heuristic)

```bash
python run_expanded_tier5.py
# Output: tier5_expanded_results.json
# Expected: 5 variants with swing range 44.4–51.4%
```

### Step 4: Replicate Tier-6 (Classical ML)

```bash
pip install scikit-learn numpy
python run_expanded_tier6.py
# Output: tier6_expanded_results.json
# Expected: RF ≈ 61.6%, LR ≈ 43.4%, SVM ≈ 43.6%
```

### Step 5: Validate Cross-File Consistency

```bash
python final_validation.py
# Expected: 0 errors, ≤2 warnings (known-bening)
```

### Step 6: Generate Figures

```bash
python stage5_manuscript/figures/generate_figures.py
# Output: 3 PNG figures in stage5_manuscript/figures/
```

**Total runtime:** ~15 minutes on a 4-core CPU with 8 GB RAM. No GPU required. No paid API calls required. All results are deterministic (fixed random seeds where applicable).

---

## 7. Citation

If you use this dataset, software, or results, please cite:

```bibtex
@misc{acts_v2_2026,
  title={{ACTS v2 Reproducibility Package: Identifying Block and Stream Ciphers with LLMs and Classical ML}},
  author={[Redacted for Review]},
  year={2026},
  howpublished={{DOI-to-be-assigned}},
  note={Supplementary materials for ESWA-D-26-11044R1}
}
```

---

## 8. License & Terms

**Software** (`.py` files): Apache License 2.0
**Data** (`.bin` files): CC0 — synthetic ciphertext generated from random plaintext
**Results** (`.json`, `.csv`, `.md`): CC0 — open research outputs

---

## 9. File Integrity & Sizes

| Category | Count | Total Size |
|----------|-------|------------|
| Pilot corpus (`.bin`) | 140 | 708 KB |
| Expanded corpus (`.bin`) | 700 | 4.1 MB |
| Result files (`.json`, `.csv`) | 64 | ~2.5 MB |
| Scripts (`.py`) | 21 | ~300 KB |
| Documentation (`.md`) | 39 | ~800 KB |
| Figures (`.png`, `.py`) | 4 | ~200 KB |
| **Total package** | **968** | **8.8 MB** |

---

*End of DOI Artifact Catalog*
*Generated for ESWA-D-26-11044R1 — May 10, 2026*
