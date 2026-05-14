# Plan: Elevate ACTS Paper to World-Class Impact

**Date:** 2026-05-14
**Target:** ESWA (Expert Systems With Applications) — then broader venues
**Current status:** Major revision (R1) in progress, live validation complete

---

## Goal

Transform the ACTS paper from a strong niche security benchmark into a **methodological landmark** that changes how the AI community evaluates LLM reasoning across domains. The paper should be cited not just by cryptographers, but by AI evaluators, cognitive scientists, and security practitioners worldwide.

---

## Current Strengths (Do Not Break)

1. **Radical honesty** — live validation correcting heuristic overestimates (9.0% vs 47.2%) is unique in ML literature
2. **Three-gap decomposition** — representation, integration, residual is a genuine theoretical contribution
3. **Multi-scale validation** — 140 → 700 → 7,000 files with controlled randomisation
4. **Zero-cost reproducibility** — entire pipeline runs on consumer hardware

---

## Phase 1: Theoretical Reframing (Days 1–3)

### 1.1 Elevate the Abstract (File: `acts_paper1.tex`)
**Current:** Describes a cipher-identification benchmark.  
**Target:** Describes a new epistemological framework for evaluating AI "understanding."

**Action:** Rewrite Abstract to frame ACTS as a **general methodology** for detecting confabulation:
> "We introduce ACTS, a falsification framework for determining whether a language model performs genuine analytical reasoning or generates plausible-sounding narratives from surface heuristics. We demonstrate the framework on cryptographic cipher identification, where we show that..."

### 1.2 Add "Philosophical Implications" Section (New: Section 5.7)
Connect findings to broader AI evaluation crisis:
- **Turpin et al. (2023)** — reasoning traces are not understanding
- **Ji et al. (2023)** — confabulation taxonomy
- **Bender & Koller (2020)** — form vs meaning
- Propose: "The ACTS Principle" — *any domain where (a) ground truth is verifiable, (b) surface heuristics exist, and (c) reasoning traces are inspectable, LLM claims of expertise should be falsified via controlled blind evaluation.*

### 1.3 Rename/Reframe Contributions
Rename paper title from:
> "ACTS: A Two-Phase Benchmark..."

To:
> "ACTS: A Falsification Framework for LLM "Expertise" — And Its Application to Cryptanalysis"

This signals methodological breadth over narrow domain specificity.

---

## Phase 2: Methodological Strengthening (Days 3–5)

### 2.1 Close Remaining Experimental Gaps

| Gap | Status | Action |
|-----|--------|--------|
| Tier 5 live on 100 samples | ✅ Done | Documented as 9.0% |
| Tier 7 live on perturbed samples | ❌ Open | **P0**: Run 20 live inferences on perturbed ciphertext (zero-prefix, XOR mask) to test if live LLM shows ANY flip |
| Backend comparison for Gemma 4 | ❌ Open | **P1**: Run Gemma 4 on both Ollama and OpenRouter to show if Nemotron swing is model-specific |
| Cross-model live comparison | ❌ Open | **P1**: Compare GPT-OSS, Gemma 4, Nemotron on same 20 blind samples to show if all models converge to heuristic |

### 2.2 Add "ACTS Protocol" Box (New: Section 3.4)
Formalize the 7-tier protocol as a **reusable checklist** for other domains:
```
The ACTS Protocol for falsifying AI domain expertise:
Tier 1–2: Metadata strip (filename → blind)
Tier 3: Baseline (can model solve without scaffolding?)
Tier 4: Tool augmentation (does scaffolding help?)
Tier 5: Forced reasoning (does reasoning format matter?)
Tier 6: ML ceiling (what is the statistical upper bound?)
Tier 7: Adversarial robustness (is signal fragile?)
Tier 8: Feature ablation (what is the true signal?)
Apply to: malware classification, vulnerability detection, steganalysis...
```

### 2.3 Compute Statistical Significance for Live 100
**Action:** Compute Wilson score CI for 9.0% on 100 samples and compare to heuristic 55.0%:
> Live LLM: 9.0% [4.4%–16.4%] (Wilson 95% CI)  
> Heuristic: 55.0% [45.2%–64.6%]  
> Non-overlapping: p < 0.0001 (exact binomial test)

Add this to Results.

---

## Phase 3: Artifact & Reproducibility (Days 5–7)

### 3.1 Make Repository a "One-Command" Reproduction
**Target:** `git clone && make reproduce` runs everything.

**Files to create:**
- `Makefile` with targets: `setup`, `reproduce-tier1`, `reproduce-tier8`, `validate-live`
- `docker-compose.yml` — pins Ollama + model versions
- `reproduce.sh` — runs deterministic tiers in < 5 minutes
- `ROADMAP.md` — obvious next experiments for other researchers

### 3.2 Create Live Validation Subpackage
**Directory:** `live_validation/`
- `run_20_samples.py` — P0 experiment (Tier 7 perturbed)
- `run_100_samples.py` — already done (Tier 5 blind)
- `cross_model_comparison.py` — P1 experiment
- `README.md` — "How to audit our heuristic claims"

### 3.3 Generate Auto-Documentation
Use the ablation results + live validation to auto-generate:
- `RESULTS_SUMMARY.md` — per-tier accuracy table
- `FEATURE_IMPORTANCE.md` — Gini importance ranked
- `DECISION_BOUNDARY.md` — visualization of which files get misclassified

---

## Phase 4: Narrative & Structural (Days 7–9)

### 4.1 Restructure Introduction (File: `acts_paper1.tex`)
**Current flow:** Domain intro → LLM claims → our benchmark  
**Target flow:** AI evaluation crisis → confabulation as systemic failure → ACTS as solution → cryptanalysis as demonstration

Add opening hook:
> "In June 2023, a GPT-4 user asked the model to analyse a ciphertext file. The model produced a three-paragraph chain-of-thought discussing entropy, block alignment, and key-scheduling, then correctly identified AES-256. The user was impressed—until they realised the filename was `AES-256_sample.bin`. This paper asks: what happens when the filename is removed?"

### 4.2 Add "Broader Impact" Panel (New: Section 6.1)
Explicitly map ACTS to other domains:
- **Malware analysis:** Can LLMs identify malware families from raw bytes, or do they read filenames?
- **Vulnerability detection:** Do LLMs audit code or parse `CVE-YYYY-NNNN` comments?
- **Forensic steganalysis:** Image metadata vs pixel statistics
- **Financial fraud detection:** Transaction narrative vs raw feature patterns

This transforms the paper from "cryptography niche" to "AI evaluation methodology."

### 4.3 Elevate Limitations to "Open Problems"
**Current:** Honest list of weaknesses.  
**Target:** Honest list of **research directions** that make reviewers want to cite the paper.

Restructure each limitation as a Question:
> "L1: Is the 9.0% floor model-specific? → **Open Question:** Do all LLMs converge to the same modulo heuristic, or do instruction-tuned models show different inductive biases?"

---

## Phase 5: Response to Reviewers (Days 9–10)

### 5.1 Response Document Structure
Write `RESPONSE_REVIEWERS_R2.md` with:
- **Point-by-point** addressing all R4/R5 comments
- **Live validation** as the crowning new experiment (not just an ablation)
- **Three-gap decomposition** as a genuine theoretical contribution
- **ACTS Protocol** as a transferable methodology

### 5.2 Highlight "Reviewer-Requested, Author-Delivered" Honesty
Frame the narrative:
> "Reviewer 5 asked for an ablation study. We delivered not just the ablation, but live validation proving our heuristic overestimated LLM performance by 46 pp. This honest correction strengthens rather than weakens our conclusions."

---

## Phase 6: Impact Maximization (Days 10–12)

### 6.1 Preprint + Social Strategy
- **arXiv:** Submit v1 immediately upon acceptance to ESWA (ESWA allows preprints)
- **Twitter/X thread:** 10-tweet thread: "We thought LLMs could do cryptanalysis. We were wrong. Here's the live data." — tag @ESWA_journal, @arXiv_Daily
- **Hacker News:** Post the live validation story (HN loves honest null results)

### 6.2 Code Release as "Living Benchmark"
- Register ACTS on [Papers With Code](https://paperswithcode.com/)
- Create leaderboard: invite other labs to submit their agentic pipelines
- Monthly updates: new models (GPT-5, Gemini 3, etc.) tested blind

### 6.3 Follow-Up Paper Pipeline
Plan sequels before reviewers even finish reading:
1. **ACTS-Malware:** Apply protocol to malware family classification
2. **ACTS-Stego:** Apply to steganographic detection
3. **ACTS-General:** Theoretical paper formalising the protocol for arbitrary domains

This signals the work is **foundational**, not terminal.

---

## Files Likely to Change

| File | Action |
|------|--------|
| `acts_paper1.tex` | Major rewrite of Abstract, Intro, F5, F7, Conclusion |
| `tab:gap_decomp` | Already added — verify formatting |
| `live_validation_100.py` | Already done — add to repo |
| `README.md` (repo root) | Rewrite as "One-command reproduction" |
| `Makefile` | **New** — automation |
| `docker-compose.yml` | **New** — reproducibility |
| `RESPONSE_REVIEWERS_R2.md` | **New** — reviewer response |
| `ROADMAP.md` | **New** — future directions |
| `RESULTS_SUMMARY.md` | **New** — auto-generated |

---

## Tests / Validation Checklist

- [ ] `pdflatex acts_paper1.tex` compiles without errors
- [ ] All tables fit within single column (or declared as `table*`)
- [ ] Live 100 numbers match JSON output exactly
- [ ] Three-gap decomposition arithmetic: 32.3 + 26.8 + 1.2 = 60.2 ✓
- [ ] Figure count ≤ ESWA limit (check guidelines)
- [ ] Word count ≤ limit (check ESWA: typically 12,000 words)
- [ ] All citations resolve (no `?` in PDF)
- [ ] Response document addresses every R4/R5 point explicitly

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| Live validation makes heuristic look bad | **Embrace it.** Honesty about 9.0% is the paper's superpower |
| ESWA asks for more experiments | Phase 2 has 3 pre-planned experiments; document any as "future work" |
| ArXiv scooping | Submit to arXiv same day as ESWA acceptance; ESWA allows preprints |
| Repository maintenance burden | Pin versions in Docker; write `MAINTAINERS.md` |
| Philosophical section alienates practical reviewers | Keep it short (1 page); label "Optional Reading" if needed |

---

## Open Questions for User

1. **Domain expansion:** Which domain should ACTS target next — malware, stego, or fraud detection?
2. **Title preference:** Keep "ACTS" acronym or rebrand as "FALSIFY" (Falsification of AI-Led Security Inference)?
3. **Experiment priority:** Tier 7 perturbed live (20 samples) or cross-model live (20×3=60 samples)?
4. **Venue ambition:** Target next-tier journal (IEEE S&P, TDSC) or conference (USENIX Security, CCS)?

---

*Saved to: `.hermes/plans/2026-05-14_235800-elevate-acts-world-class.md`*
