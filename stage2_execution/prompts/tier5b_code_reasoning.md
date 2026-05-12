# Tier-5B: Code-as-Reasoning
## ACTS v2 — Programmatic Cryptanalysis Mode

You are an expert forensic cryptographer and Python programmer. You will identify the cipher family by **writing and describing Python code** that analyzes the ciphertext statistically and structurally.

Your task has TWO parts:
1. Write Python code that would analyze this ciphertext
2. Based on your code's logic, state the final classification

### CIPHERTEXT FILE
- Filename: `{filename}`
- File size: `{file_size}` bytes
- Hex preview (first 256 bytes): `{hex_preview}`

### AVAILABLE CIPHER FAMILIES
1. AES-128 | 2. AES-256 | 3. 3DES | 4. DES | 5. ChaCha20 | 6. RSA-2048 | 7. ML-KEM-768

### PART 1 — WRITE ANALYSIS CODE
Write Python code that performs the following checks and prints diagnostic output:

```python
import math
from collections import Counter

def analyze_ciphertext(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    n = len(data)
    print(f"File size: {n} bytes")
    
    # 1. Check for known fixed sizes
    if n == 256:
        print("Fixed 256B → suggests RSA-2048")
    elif abs(n - 1088) < 50:
        print("~1088B → suggests ML-KEM-768")
    
    # 2. Entropy
    counts = Counter(data)
    entropy = -sum((c/n)*math.log2(c/n) for c in counts.values())
    print(f"Entropy: {entropy:.4f}")
    
    # 3. Block structure detection (8, 16, 64)
    for block_size in [8, 16, 64]:
        if n % block_size == 0:
            blocks = [data[i:i+block_size] for i in range(0, n, block_size)]
            unique = len(set(blocks))
            print(f"{block_size}-byte blocks: {unique}/{len(blocks)} unique")
    
    # 4. Byte frequency chi-square
    expected = n / 256
    chi2 = sum(((counts.get(b,0) - expected)**2 / expected) for b in range(256))
    print(f"Chi-square: {chi2:.2f}")
    
    # 5. First-byte patterns (for padding detection)
    print(f"First byte: 0x{data[0]:02x}")
    
    # YOUR INFERENCE LOGIC HERE
    # Based on the above, which cipher family is most likely?
    
analyze_ciphertext("{filename}")
```

Describe what YOUR code would output for this file and why.

### PART 2 — STATE YOUR CLASSIFICATION
Based on the code logic you described, classify the ciphertext:

```
PREDICTED_CIPHER: [ONE from the list above]
CONFIDENCE: [0-100%]
JUSTIFICATION: [2-3 sentences citing specific code outputs]
```

### RULES
- The code must be runnable in principle (no hallucinated libraries).
- Your justification must map code output to cipher family with cryptographic validity.
- Do not use filename or context clues — base your answer on the data analysis.

BEGIN:
