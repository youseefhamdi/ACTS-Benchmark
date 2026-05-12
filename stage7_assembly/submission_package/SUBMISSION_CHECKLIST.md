# Submission Checklist — ACTS v2 Revision
## Ref: ESWA-D-26-11044R1

---

## Required Files

### 1. Manuscript Source
- [x] `manuscript_v2.tex` — Main LaTeX document
- [x] `manuscript_v2.pdf` — Compiled output (zero errors/warnings)
- [x] `source_files.zip` — All .tex, .cls, .sty files + figures

### 2. Revision Documents
- [x] `response_to_reviewers.pdf` — Point-by-point rebuttal
- [x] `list_of_changes.pdf` — Tracked changes (diff)
- [x] `cover_letter.pdf` — Resubmission cover letter

### 3. Figures & Tables
- [x] `figure_accuracy_bars.pdf` — Main results with error bars
- [x] `figure_ablation_waterfall.pdf` — Component contribution
- [x] `figure_chi2_violin.pdf` — Distribution comparison
- [x] `figure_cv_stability.pdf` — 5-fold CV results
- [x] `table_main_results.tex` — Auto-generated (locked)
- [x] `table_ablation.tex` — Auto-generated (locked)
- [x] `table_chi2_validation.tex` — Auto-generated (locked)

### 4. Supplementary Material
- [x] `generate_corpus.py` — Data generation script
- [x] `split_protocol.py` — Validation split script
- [x] `ablation_runner.py` — Ablation study script
- [x] `chi2_validator.py` — χ² validation script
- [x] `statistical_analysis.py` — Statistics module
- [x] `consistency_checker.py` — Consistency verification
- [x] `Dockerfile.eval` — Reproducible environment
- [x] `corpus_manifest.json` — 140-file metadata

### 5. Open Science
- [x] GitHub repository updated: https://github.com/youseefhamdi/CoPaw-ACTS-Benchmark
- [x] Docker image built and tagged: `acts-v2-eval:latest`
- [x] LICENSE: MIT (code), CC-BY (data)
- [x] README with reproduction instructions

### 6. Administrative
- [x] ORCID verified for all authors
- [x] Author affiliations current
- [x] Conflict of interest statement
- [x] Funding statement (none)
- [x] Data availability statement
- [x] Code availability statement
- [x] Ethical compliance statement

---

## Pre-Submission Verification

### Build Test
```bash
pdflatex manuscript_v2.tex
bibtex manuscript_v2
pdflatex manuscript_v2.tex
pdflatex manuscript_v2.tex
# Must produce ZERO errors, ZERO warnings
```

### Consistency Check
```bash
python consistency_checker.py \
  --paper-file manuscript_v2.tex \
  --results-file results.json
# Must return: {"status": "PASS"}
```

### Reproducibility Test
```bash
docker build -f Dockerfile.eval -t acts-v2-eval .
docker run -v $(pwd)/acts_v2_corpus:/data acts-v2-eval \
  python generate_corpus.py --validate
# Must return: [OK] Corpus validation passed
```

---

## Upload Order (Editorial Manager)

1. **Manuscript** → `manuscript_v2.tex` + source `.zip`
2. **Cover Letter** → `cover_letter.pdf`
3. **Response to Reviewers** → `response_to_reviewers.pdf`
4. **Highlight Changes** → `list_of_changes.pdf`
5. **Supplementary Material** → `supplementary.zip`
6. **Figures** → Individual `.pdf` files

---

## Final Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Corresponding Author | Youssef Hamdi Zafaan | 2026-05-31 | ☐ |
| Co-Author | Mohammed Khalaf Salama | 2026-05-31 | ☐ |

---

*Submission deadline: May 31, 2026 (21 days from notification)*
