# Tier-5C: Self-Correction with Contradiction Detection
## ACTS v2 — Iterative Refinement Mode

You are an expert forensic cryptographer. This is a **two-round** analysis. In Round 1 you give an initial answer. In Round 2, you must CRITIQUE your own Round 1 answer and either CONFIRM or CORRECT it.

### ROUND 1 — INITIAL ANALYSIS

CIPHERTEXT: `{filename}`
- Size: `{file_size}` bytes
- Hex preview (first 128 bytes): `{hex_preview}`
- Computed entropy: `{entropy:.4f}` bits/byte

CIPHER OPTIONS: AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768

Provide:
```
ROUND_1_PREDICTION: [cipher family]
ROUND_1_CONFIDENCE: [0-100%]
ROUND_1_REASONING: [Your reasoning]
```

---

### ROUND 2 — SELF-CRITIQUE

Now, imagine a SENIOR CRYPTographer reviews your Round 1 answer. They will point out inconsistencies using these common fallacies:

**Common Fallacy 1 — Entropy Misinterpretation:**
> "AES and ChaCha20 both produce ~7.9-8.0 bits/byte entropy. You cannot distinguish them by entropy alone."

**Common Fallacy 2 — Block Size Overgeneralization:**
> "16-byte block alignment matches both AES-128 and AES-256. You cannot distinguish AES key sizes by block size."

**Common Fallacy 3 — ChaCha20 Confusion:**
> "ChaCha20 is a stream cipher with no fixed block structure. High entropy + no block pattern only tells you it's a stream cipher, not specifically ChaCha20."

**Common Fallacy 4 — Filename Bias:**
> "If you looked at the filename to help your decision, you violated the blind condition."

**Common Fallacy 5 — RSA/KEM Certainty:**
> "RSA-2048 output is exactly 256 bytes with PKCS padding. ML-KEM-768 output is ~1088 bytes. Only if the file size matches EXACTLY can you be certain."

Critique your own Round 1 answer against EACH fallacy above:

```
FALLACY_1_CHECK: [Did you use entropy to distinguish symmetric ciphers? If yes, correct yourself.]
FALLACY_2_CHECK: [Did you claim to distinguish AES-128 vs AES-256? If yes, correct yourself.]
FALLACY_3_CHECK: [Did you identify ChaCha20 only from entropy? If yes, correct yourself.]
FALLACY_4_CHECK: [Did filename influence your answer? Be honest.]
FALLACY_5_CHECK: [Does the exact file size match RSA-2048 or ML-KEM-768?]
```

### FINAL ANSWER
Based on your self-critique, provide:

```
FINAL_PREDICTION: [cipher family OR "UNKNOWN"]
FINAL_CONFIDENCE: [0-100%]
ROUND_1_WAS_CORRECT: [yes/no/partially]
WHY_CHANGED: [If you changed your answer, why? Be specific.]
```

### RULES
- If your Round 1 answer falls to any fallacy, you MUST change it or reduce confidence.
- "UNKNOWN" is an acceptable final answer if the evidence is genuinely ambiguous.
- Honest self-correction scores higher than stubborn incorrectness.

BEGIN ROUND 1:
