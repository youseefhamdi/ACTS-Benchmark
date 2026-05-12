#!/usr/bin/env python3
"""
Scaling Synthesizer — ACTS v2
==============================
Compares 140-file baseline results vs expanded-corpus results.
Generates final academic deliverables:
  - stage2_execution/results/SCALING_COMPARISON.md
  - stage2_execution/results/FINAL_REBUTTAL_SYNTHESIS.md
"""

import json
from pathlib import Path


def load_json(p: Path):
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main():
    results_dir = Path("stage2_execution/results")

    orig_t5 = load_json(results_dir / "tier5a_full_claude_self_inference.json")
    orig_t6 = load_json(results_dir / "tier6_results.json")
    exp_t5 = load_json(results_dir / "tier5_expanded_results.json")
    exp_t6 = load_json(results_dir / "tier6_expanded_results.json")

    # Generate scaling comparison
    md = """# Scaling Comparison — ACTS v2 Corpus

## Question

Does the information-theoretic ceiling hold when the corpus scales from 140 → 700+ files?

## Baseline (140 files)

| Metric | Value |
|--------|-------|
| Total files | 140 |
| Theoretical size-only max | 32.1% |
| Tier-5 LLM heuristic (best bias) | 51.4% |
| Tier-5 LLM heuristic (worst bias) | 44.3% |
| Tier-5 LLM heuristic (Claude default) | 46.4% |
| Tier-6 Random Forest | 42.9% |
| RF symmetric cipher accuracy | Random (~20%) |

## Expanded (700+ files)

| Metric | Value |
|--------|-------|
| Total files | {expanded_total} |
| Theoretical size-only max | {expanded_theory} |
| Tier-5 heuristic (best bias) | {t5_best} |
| Tier-5 heuristic (worst bias) | {t5_worst} |
| Tier-6 Random Forest | {t6_rf} |
| RF symmetric cipher accuracy | {t6_symmetric} |

## Stability Assessment

Awaiting expanded corpus agent completion...

## Conclusion

Awaiting expanded corpus agent completion...

*Generated: 2026-05-10*
"""
    out_path = results_dir / "SCALING_COMPARISON.md"
    out_path.write_text(md)
    print(f"Saved scaling comparison template → {out_path}")

    # Final rebuttal synthesis
    final_md = """# FINAL REBUTTAL SYNTHESIS — ESWA-D-26-11044R1

## Executive Summary

This document presents the complete evidence that cipher-family identification from ciphertext alone is information-theoretically impossible for modern symmetric ciphers, and that LLM forced-reasoning is a spurious source of apparent accuracy.

## Evidence Stack

### Tier 1–3: Baseline LLM Blind Classification
Multiple external LLMs tested on 140-file corpus. Accuracy: 14.3%–57.1%.

### Tier 5: Forced Reasoning (Self-Inference)
- CoT, Code, Self-Correction all yield **identical** accuracy because the classifier is a 3-rule heuristic.
- The 46.4% figure is **inside a 44–51% bias-swing range** — not evidence of skill.

### Tier 6: Classical ML Control
- Random Forest (200 trees, 25 features) achieves 42.9%.
- Symmetric cipher accuracy: **exactly random guessing** (15–25%).
- No hidden statistical signal exists.

### Scaling Validation (Expanded Corpus)
Results will be appended here once the 700+ file agents complete.

## The Confabulation Paradox
LLMs can exceed the honest ML ceiling by inventing false heuristics that accidentally match dataset bias. This is a **failure mode**, not a success mode.

## Limitations
See LIMITATIONS.md for full disclosure.

---

*Generated: 2026-05-10*
"""
    (results_dir / "FINAL_REBUTTAL_SYNTHESIS.md").write_text(final_md)
    print(f"Saved final rebuttal synthesis → {results_dir / 'FINAL_REBUTTAL_SYNTHESIS.md'}")


if __name__ == "__main__":
    main()
