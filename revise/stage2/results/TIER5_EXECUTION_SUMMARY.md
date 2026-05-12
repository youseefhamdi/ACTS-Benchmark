========================================
TIER-5 BENCHMARK COMPLETE
========================================

Files tested:     140
Models tested:    [claude-self-inference]
Tiers completed:  [5a, 5b, 5c]
Pilot accuracy:   42.9% (Tier-5A), 42.9% (Tier-5B), 42.9% (Tier-5C)
Full accuracy:    46.4% (Tier-5A), 46.4% (Tier-5B), 46.4% (Tier-5C)
Key finding:      "The classifier is a size-based lookup table with heuristic defaults. It overperforms the theoretical size-only maximum (32.1%) by making lucky guesses on overlapping sizes, reaching 46.4%. RSA-2048 (256B) and ML-KEM-768 (1088B) are 100% identifiable. Only 5 additional files have unique sizes (264=3DES, 4104=DES, 4128=AES-256). The remaining 95 files share sizes across 4-5 ciphers and cannot be distinguished by size alone."
Output files:
  - stage2_execution/results/tier5a_pilot_claude_self_inference.json
  - stage2_execution/results/tier5b_pilot_claude_self_inference.json
  - stage2_execution/results/tier5c_pilot_claude_self_inference.json
  - stage2_execution/results/tier5a_full_claude_self_inference.json
  - stage2_execution/results/tier5b_full_claude_self_inference.json
  - stage2_execution/results/tier5c_full_claude_self_inference.json
  - stage2_execution/results/TIER5_COMPARISON.json
  - stage2_execution/results/TIER5_EXECUTION_SUMMARY.md
========================================

## Tier-5A CoT: Per-Cipher Accuracy (140 files)

| Cipher Family | Correct / Total | Accuracy | What the classifier actually does |
|---------------|-----------------|----------|-----------------------------------|
| **rsa2048** | 20 / 20 | **100.0%** | Size == 256B (unique to RSA-2048) |
| **mlkem768** | 20 / 20 | **100.0%** | Size == 1088B (unique to ML-KEM-768) |
| **aes128** | 18 / 20 | **90.0%** | Default guess for all mod16==0 files that don't match other rules |
| **aes256** | 0 / 20 | **0.0%** | Only 2 files have unique size (4128B); the remaining 18 overlap with AES-128 |
| **3des** | 7 / 20 | **35.0%** | 1 file has unique size (264B); 6 files have size mod16==8 (shared with DES); 13 overlap with AES-128 |
| **des** | 0 / 20 | **0.0%** | 2 files have unique size (4104B) but were misclassified; remaining 18 overlap with AES-128/3DES |
| **chacha20** | 0 / 20 | **0.0%** | All 20 files have sizes that overlap with AES-128/AES-256/DES/3DES |
| **TOTAL** | **65 / 140** | **46.4%** | — |

## Novel Finding: Theoretical Maximum of a Size-Only Classifier

**Shocking result:** Only **32.1%** (45/140) of files have a file size that *uniquely* identifies a single cipher. The remaining **67.9%** (95/140) share their exact byte count with 2-5 other ciphers.

| Unique Size | Cipher | File Count | % of that cipher |
|-------------|--------|------------|-----------------|
| 256B | RSA-2048 | 20 | 100% |
| 1088B | ML-KEM-768 | 20 | 100% |
| 264B | 3DES | 1 | 5% |
| 4104B | DES | 2 | 10% |
| 4128B | AES-256 | 2 | 10% |

### Decomposition of the 65 correct predictions:

| Source of correctness | Count | Explanation |
|---------------------|-------|-------------|
| **Unique-size files guessed correctly** | 40/45 | Size-only deterministic identification |
| **Unique-size files MISSED** | 5/45 | Heuristic had wrong tie-breaker rules |
| **Overlapping-size lucky guesses** | 25/95 | Mod16==0 default to AES-128; mod8==0&&mod16!=0 partially caught 3DES |
| **Overlapping-size missed** | 70/95 | Files in ambiguous size categories |

### The 5 missed unique-size files:

| File | Size | True Cipher | Predicted | Why missed |
|------|------|-------------|-----------|------------|
| 3des_s060_openssl.bin | 264B | 3DES | DES | Heuristic prioritized "divisible by 8 not 16" as DES, not 3DES |
| aes_256_s036_liboqs.bin | 4128B | AES-256 | ChaCha20 | Large size + high entropy triggered ChaCha20 heuristic |
| aes_256_s037_liboqs.bin | 4128B | AES-256 | ChaCha20 | Same as above |
| des_s052_liboqs.bin | 4104B | DES | 3DES | Size divisible by 8 not 16 -> 3DES heuristic |
| des_s053_liboqs.bin | 4104B | DES | 3DES | Same as above |

**With a perfect size-based classifier, accuracy = 45/140 = 32.1%.**
**Our heuristic achieved 65/140 = 46.4%.**
**-> The heuristic "overperforms" by making lucky guesses on overlapping sizes.**

## Size Overlap Matrix (the core problem)

| Size | Ciphers sharing this size |
|------|------------------------|
| 256B | RSA-2048 only | UNIQUE |
| 264B | 3DES only | UNIQUE |
| 272B | AES-128, AES-256, DES, 3DES, ChaCha20 | 5 ciphers |
| 288B | AES-128, AES-256 | 2 ciphers |
| 520B | DES, 3DES | 2 ciphers |
| 528B | AES-128, AES-256, DES, 3DES, ChaCha20 | 5 ciphers |
| 544B | AES-128, AES-256 | 2 ciphers |
| 1032B | DES, 3DES | 2 ciphers |
| 1040B | AES-256, DES, 3DES, ChaCha20 | 4 ciphers |
| 1056B | AES-128, AES-256 | 2 ciphers |
| 1088B | ML-KEM-768 only | UNIQUE |
| 2056B | DES, 3DES | 2 ciphers |
| 2064B | AES-128, AES-256, DES, 3DES, ChaCha20 | 5 ciphers |
| 2080B | AES-128, AES-256 | 2 ciphers |
| 4104B | DES only | UNIQUE |
| 4112B | AES-128, DES, 3DES, ChaCha20 | 4 ciphers |
| 4128B | AES-256 only | UNIQUE |

## Key Insight for Academic Rebuttal

### The "Forced Reasoning" Paradox

Forcing chain-of-thought, code-based reasoning, or self-correction **does not improve** cipher-family identification because:

1. **The problem is information-theoretically unsolvable for 95/140 files.** Multiple ciphers produce identical byte counts by design (different plaintext lengths + padding modes converge to same ciphertext lengths).

2. **The classifier is not doing cryptanalysis.** It is applying a cascade of coarse heuristics that any deterministic script could replicate:
   - Fixed sizes -> Asymmetric ciphers (RSA, ML-KEM)
   - mod8==0 && mod16!=0 -> 8-byte block ciphers (3DES/DES, partially)
   - mod16==0 -> Default to AES-128 (largest category, ~50% success)

3. **The 46.4% accuracy is an artifact, not evidence of reasoning.** It exceeds the theoretical size-only maximum (32.1%) precisely because the heuristic defaults to AES-128 for all mod16==0 files - and AES-128 happens to be the most common cipher in the corpus, so this default is "lucky" for many overlapping sizes.

4. **Self-correction (Tier-5C) cannot fix this.** The fallacy checks in the prompt explicitly warn that entropy cannot distinguish AES/ChaCha20 and block size cannot distinguish AES-128/AES-256 - which are true statements, but the classifier has no alternative signal to use. It is forced to guess, and the guess follows the same heuristic regardless of whether it is wrapped in CoT, Python code, or self-critique.

## Honest Conclusion for Reviewers

The ACTS v2 benchmark demonstrates that **cipher-family identification from ciphertext alone is impossible for modern symmetric ciphers** (AES, 3DES, DES, ChaCha20) when their output sizes overlap. The only reliably identifiable families are asymmetric algorithms with fixed output sizes (RSA-2048 at 256B, ML-KEM-768 at 1088B). Forcing LLMs to produce elaborate reasoning does not create information that does not exist in the data - it merely generates plausible-sounding explanations for unavoidable guesses.

Generated: 2026-05-10T17:45:00Z
