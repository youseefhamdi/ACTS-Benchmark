# Tier-5A: Forced Chain-of-Thought with Evidence Citation
## ACTS v2 — Expert Forensic Analysis (Explainable Mode)

You are an expert forensic cryptographer participating in a controlled benchmark. Your task is to identify the cipher family used to produce the attached ciphertext file through **rigorous, evidence-based analysis**.

### CRITICAL INSTRUCTIONS
1. You **MUST** show your reasoning step-by-step. A single-word answer will be rejected.
2. You **MUST** cite specific evidence from the ciphertext (byte values, entropy, structure).
3. You **MUST** explain WHY each alternative cipher family was eliminated.
4. You **MAY** use the following forensic tools mentally or by describing calculations:
   - Shannon entropy calculation
   - Chi-square test for randomness
   - Block size detection (repeating patterns)
   - File size analysis
   - Byte frequency distribution

### CIPHERTEXT FILE
- Filename: `{filename}`
- File size: `{file_size}` bytes
- Hex preview (first 128 bytes): `{hex_preview}`
- Entropy (Shannon): `{entropy:.4f}` bits/byte
- Chi-square statistic: `{chi2:.2f}` (p-value: `{chi2_p:.4f}`)
- Byte frequency (top 5): `{top_bytes}`

### AVAILABLE CIPHER FAMILIES
1. AES-128 (16-byte blocks)
2. AES-256 (16-byte blocks)
3. 3DES (8-byte blocks)
4. DES (8-byte blocks)
5. ChaCha20 (stream cipher, 64-byte blocks internally)
6. RSA-2048 (variable, typically 256-byte output)
7. ML-KEM-768 (post-quantum, fixed ~1088-byte encapsulation)

### OUTPUT FORMAT
You MUST respond in this exact structure:

```
STEP 1 — ENTROPY ANALYSIS:
[Your analysis of the entropy value and what it suggests]

STEP 2 — STRUCTURAL ANALYSIS:
[Your analysis of block structure, file size, and repeating patterns]

STEP 3 — STATISTICAL TESTING:
[Your analysis of chi-square and byte frequency]

STEP 4 — ELIMINATION:
[Which ciphers did you eliminate and WHY — cite evidence]

STEP 5 — FINAL DETERMINATION:
[Your final answer — ONE cipher family from the list above]

CONFIDENCE: [0-100%]
```

### RULES
- If you cannot genuinely determine the cipher, say "UNKNOWN" and explain why.
- Do NOT guess based on filename or context — analyze the DATA.
- Your reasoning will be independently evaluated for cryptographic soundness.

BEGIN YOUR FORENSIC ANALYSIS:
