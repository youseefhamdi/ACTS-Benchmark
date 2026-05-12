# Tier-5: Expert Forensic Analysis with Forced Reasoning
## ACTS v2 — The Highest Benchmark Tier

**Date:** 2026-05-10  
**Purpose:** Test whether forcing explicit, evidence-based reasoning improves blind cipher identification — or exposes the lack of genuine cryptanalysis.

---

## Rationale

Tiers 1–4 established:
- Tier-1 (metadata): 100% accuracy
- Tier-3 (blind): ~25% accuracy
- Tier-4 (tool-assisted): ~92% accuracy with LLM orchestration

The critical question remains: **If we force the model to think step-by-step and cite evidence, does blind accuracy improve?** Or does explicit reasoning expose that the model has no genuine cryptanalytic ability?

Tier-5 tests this hypothesis through three sub-variants.

---

## Tier-5A: Forced Chain-of-Thought with Evidence Citation

**Prompt:** `prompts/tier5a_cot_enforced.md`

The model MUST:
1. Analyze entropy, structure, and statistics step-by-step
2. Cite specific byte values and computed metrics
3. Explain why each alternative was eliminated
4. Report confidence and reasoning

**Hypothesis:** If models genuinely understand cryptography, forcing CoT should improve accuracy. If they guess based on priors, CoT will reveal incoherent reasoning.

---

## Tier-5B: Code-as-Reasoning

**Prompt:** `prompts/tier5b_code_reasoning.md`

The model MUST:
1. Write Python code that analyzes the ciphertext
2. Describe what the code would output
3. Map code outputs to cipher families with cryptographic validity

**Hypothesis:** Programming forces structured thinking. If the model writes valid analysis code that correctly distinguishes ciphers, it demonstrates transferable understanding.

---

## Tier-5C: Self-Correction with Contradiction Detection

**Prompt:** `prompts/tier5c_self_correction.md`

The model:
1. Gives an initial Round 1 answer
2. Is presented with 5 common forensic fallacies
3. Must critique its OWN Round 1 answer against each fallacy
4. Can confirm or correct based on self-critique

**Hypothesis:** Honest self-correction reveals whether the model can detect its own biases. Stubborn incorrectness = no understanding. Genuine correction = partial understanding.

---

## How to Run

### Quick Start (Tier-5A)
```bash
cd acts_v2_poc
python3 tier5_runner.py --tier 5a --model gemma4:31b-cloud --limit 7
```

### Tier-5B (Code Reasoning)
```bash
python3 tier5_runner.py --tier 5b --model gpt-oss:120b-cloud --limit 7
```

### Tier-5C (Self-Correction)
```bash
python3 tier5_runner.py --tier 5c --model nemotron-3-super:cloud --limit 7
```

### Full Corpus (20 per cipher = 140 files)
```bash
python3 tier5_runner.py --tier 5a --model gemma4:31b-cloud
```

---

## Expected Outcomes

| Scenario | Tier-3 Blind | Tier-5A CoT | Tier-5C Self-Correct | Interpretation |
|----------|-------------|-------------|---------------------|----------------|
| **A: Genuine understanding** | 25% | 60%+ | 60%+ | CoT helps; metadata gap narrows |
| **B: No understanding, exposed** | 25% | 25% | 25% → UNKNOWN | CoT reveals incoherent reasoning |
| **C: Bias amplification** | 25% | 40% | 20% | CoT amplifies frequency priors |
| **D: Random guessing** | 25% | 25% | 25% | No improvement with reasoning |

Our hypothesis (based on Tiers 1–4): **Scenario B or D** — forcing reasoning will NOT improve accuracy because LLMs lack genuine cryptanalytic ability. Instead, CoT will produce convincing-sounding but cryptographically invalid reasoning.

---

## Integration with LLM-as-a-Judge

After running Tier-5, use the Judge to evaluate:
1. **Reasoning validity** — Is the CoT cryptographically sound?
2. **Evidence accuracy** — Are cited byte values actually in the file?
3. **Self-correction honesty** — Did the model genuinely fix errors?

Example:
```bash
# After tier5 completes
python3 llm_as_judge.py --tier5-results stage2_execution/results/tier5a_*.json
```

---

## File Structure
```
stage2_execution/prompts/
├── tier5a_cot_enforced.md      # Forced chain-of-thought + evidence
├── tier5b_code_reasoning.md    # Must write Python analysis code
└── tier5c_self_correction.md   # Two-round with contradiction detection

tier5_runner.py                  # Main execution script
README_TIER5.md                  # This file
```

---

## Scientific Value

Tier-5 closes the methodological loop:
- **Tier-1:** Proves task is well-posed
- **Tier-3:** Measures blind baseline
- **Tier-4:** Measures tool-assisted performance
- **Tier-5:** Determines if reasoning ability EXISTS AT ALL

If Tier-5 shows no improvement over Tier-3, we have **definitive proof** that LLMs cannot perform cryptanalysis even when given optimal conditions for reasoning.
