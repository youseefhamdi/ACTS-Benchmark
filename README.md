# ACTS v2 — LLM Cipher Identification Benchmark
## Reproducibility Package for ESWA-D-26-11044R1

**This package contains all data, code, and results for the revised ESWA submission.**

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt       # Install dependencies
python run_expanded_tier5.py          # Replicate Tier-5 heuristic (1 min)
python run_expanded_tier6.py          # Replicate Tier-6 ML (2 min)
python final_validation.py            # Validate consistency (30 sec)
```

No API keys required. No GPU required.

---

## 📁 Package Contents

| Component | Count | Description |
|-----------|-------|-------------|
| **Datasets** | 840 `.bin` files | 140 pilot + 700 expanded ciphertext samples |
| **Scripts** | 21 `.py` files | Generators, runners, classifiers, validators |
| **Results** | 64 files | JSON + CSV + Markdown reports |
| **Docs** | 40 `.md` files | Synthesis, rebuttal, analysis |

**Total size:** 8.8 MB

---

## 🎯 Core Results

| Experiment | Corpus | Key Result |
|------------|--------|------------|
| Tier-3 (blind LLM) | 140 files | 25.0% avg accuracy; 75 pp metadata gap |
| Tier-5 (forced reasoning) | 140 + 700 | 46–51% — identical across CoT/Code/Self-Correct |
| Tier-6 (Random Forest) | 700 files | **61.6%** — non-linear artifact signal |
| Tier-6 (Logistic Regression) | 700 files | **43.4%** — linear bound |
| **LLM vs ML gap** | 700 files | **10.2 pp** — confabulation tax |

---

## 📚 Key Documents

| File | Purpose |
|------|---------|
| `DOI_ARTIFACT_CATALOG.md` | **Complete file catalog** for DOI deposit |
| `PAPER_SYNTHESIS.md` | Unified narrative (Introduction/Discussion) |
| `FINAL_REBUTTAL_SYNTHESIS.md` | Point-by-point evidence stack |
| `SCALING_COMPARISON.md` | Pilot (140) vs Expanded (700) |
| `MASTER_FINDINGS.json` | Machine-readable result registry |

---

## 🔬 Reproducing the Experiments

### Tier-5: Deterministic Heuristic on Expanded Corpus
```bash
python run_expanded_tier5.py
# Output: stage2_execution/results/tier5_expanded_results.json
# Expected: 5 bias variants, 44.4–51.4% accuracy
```

### Tier-6: Classical ML on Expanded Corpus
```bash
python run_expanded_tier6.py
# Output: stage2_execution/results/tier6_expanded_results.json
# Expected: RF=61.6%, LR=43.4%, SVM=43.6%
```

### Validation
```bash
python final_validation.py
# Validates consistency across all JSON/Markdown/LaTeX
```

---

## 📊 Dataset Generation Parameters

All ciphertext was generated with **5-dimensional randomization:**
1. Random plaintext (`os.urandom`, lengths: 256–4096 B)
2. Random key (unique per file)
3. Random IV/nonce (unique per file)
4. Random padding mode (PKCS7, ISO10126, ANSI_X923, Zero, Random)
5. Random implementation library (OpenSSL, liboqs)

Every file passes: SHA-256 uniqueness, entropy > 7.5 bits/byte, decryptability.

---

## ⚖️ License

- **Software:** Apache-2.0
- **Data (ciphertext):** CC0 (synthetic, random plaintext)
- **Results:** CC0

---

## 📖 Citation

```bibtex
@misc{acts_v2_2026,
  title={{ACTS v2: LLM Cipher Identification Benchmark}},
  year={2026},
  note={ESWA-D-26-11044R1 Supplementary Materials}
}
```

---

*Generated: 2026-05-10*
