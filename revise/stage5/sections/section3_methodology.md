# Section 3: Methodology (Upgraded for v2)

## 3.1 Dataset Generation

The ACTS v2 corpus contains **140 independently generated ciphertext files**
across 7 cipher families. Each file was generated with full randomization:

### Randomization Dimensions (5D)

| Dimension | Method | Rationale |
|-----------|--------|-----------|
| **Plaintext** | `os.urandom(size)` where size ∈ {256, 512, 1024, 2048, 4096} B | Eliminates corpus-specific plaintext artifacts |
| **Key** | `os.urandom(key_size)` per cipher standard | Eliminates key-dependent bias |
| **IV/Nonce** | `os.urandom(block_size)` | Eliminates IV-dependent patterns |
| **Padding** | Random choice from {PKCS7, ISO10126, ANSI_X923, Zero, Random} | Tests robustness to padding variation |
| **Implementation** | Equal split: OpenSSL, liboqs | Tests cross-implementation generalizability |

### Distribution

| Cipher Family | Samples | Key Size | Block/Nonce Size | Notes |
|--------------|---------|----------|-----------------|-------|
| AES-128 | 20 | 128 bits | 128 bits | CBC mode |
| AES-256 | 20 | 256 bits | 128 bits | CBC mode |
| DES | 20 | 56 bits (64 with parity) | 64 bits | CBC mode |
| 3DES | 20 | 168 bits (192 with parity) | 64 bits | CBC mode |
| ChaCha20 | 20 | 256 bits | 128 bits | Stream cipher (no padding) |
| RSA-2048 | 20 | 2048 bits | N/A | OAEP padding, 256-byte ciphertext |
| ML-KEM-768 | 20 | 768 bits (module-LWE) | N/A | KEM encapsulation, ~1088 bytes |

### Validation

All 140 files were validated for:
- Correct byte counts per cipher specification
- No duplicate SHA-256 hashes
- Decryptability with correct keys (spot-check: 14/14)
- Uniform entropy distribution (expected: > 7.5 bits/byte)

## 3.2 Evaluation Tiers

Five tiers measure performance under controlled information conditions:

| Tier | Metadata | Tools | Purpose | Hypothesis |
|------|----------|-------|---------|------------|
| **Tier-1** | Full (algorithm, mode, padding, impl) | None | Upper bound | Accuracy ≈ 95–100% |
| **Tier-2** | Filename only | None | Filename dependency | Accuracy < Tier-1 |
| **Tier-3** | None (generic filename) | None | Pure blind inference | Accuracy ≈ 10–25% |
| **Tier-4A** | None | file, ent, xxd | Tool-assisted blind | Accuracy > Tier-3 |
| **Tier-4B** | None | Full pipeline | Best automated | Accuracy ≈ 85–95% |

### Tier Definitions (Locked)

**Tier-1 Prompt:** Model receives plaintext description of the cipher
family, mode, padding, implementation, and key size. Task: confirm
the cipher family.

**Tier-2 Prompt:** Model receives only the original filename
(e.g., `aes-256-cbc_s007_openssl.bin`). Task: infer cipher family
from filename + content.

**Tier-3 Prompt:** Model receives generic filename
(`encrypted_s007.bin`) with no metadata. Task: analyze raw bytes
and identify cipher family.

**Tier-4A Prompt:** Model receives generic filename + access to
`file`, `ent`, and `xxd` tools. Task: use tool outputs to infer
cipher family.

**Tier-4B Prompt:** Model receives generic filename + full analytical
pipeline (entropy, χ², block alignment, byte frequency). Task:
orchestrate analysis and infer cipher family.

## 3.3 Threshold Calibration Protocol

To prevent corpus-specific tuning, Tier-4B thresholds are calibrated
using a strict **held-out validation protocol**:

### Step 1: Stratified Split
The 140-file corpus is stratified by cipher family into:
- **Training set**: 98 files (70%, 14 per cipher)
- **Test set**: 42 files (30%, 6 per cipher)

### Step 2: Train-Set Calibration
Grid search for optimal thresholds on training set only:
```
For each component (entropy, χ², block alignment):
  For each cipher family:
    Search threshold ∈ [grid]
    Maximize F1 on training set
```

### Step 3: Cross-Validation
5-fold stratified cross-validation confirms threshold stability:
- Fold mean accuracy ± standard deviation reported
- If std > 5%, re-evaluate threshold sensitivity

### Step 4: Single Test Evaluation
Test set is evaluated **exactly once** after calibration:
- Test results SHA-256 hashed and locked
- No re-evaluation without explicit justification

## 3.4 Models Evaluated

19 LLM systems spanning frontier APIs and open-weight models:

| Category | Models | Count |
|----------|--------|-------|
| Frontier APIs | GPT-5.4, Claude-4.6-Sonnet, Gemini-3.1-Pro, Perplexity-Pro | 4 |
| Large Open-Weight (>100B) | Mistral-Large-3, Llama-4-Scout, DeepSeek-V4, Command-R-Plus, Falcon-3-70B, Mixtral-8x22B | 6 |
| Medium Open-Weight (30–70B) | Qwen3.6-plus, Gemma4-31b, Yi-1.5-34B, Aya-4-35B, Granite-4-40B, Phi-4-Medium | 6 |
| Small Open-Weight (<10B) | Gemma4-4b, Qwen3.6-1.8b | 2 |
| Agentic Frameworks | CoPaw, CAI | 2 |

**Total inferences:** 19 models × 140 files × 5 tiers = **13,300 predictions**
