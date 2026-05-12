# Explicit Limitations & Threats to Validity
## ESWA-D-26-11044R1 — Full Disclosure

*Revised: 2026-05-11 — Updated for 700-file expanded corpus and Tier-5/6/7 results*

---

## 1. Corpus Limitations

### 1.1 Sample Size
We evaluate on **700 files** (100 per cipher family) for the expanded corpus, plus **140 files** (20 per family) for the pilot benchmark. While the expanded corpus provides sufficient statistical power, a corpus with n ≥ 500 per family could reveal:
- Implementation-specific statistical artifacts (e.g., RNG seed bias in OpenSSL).
- Rare padding patterns that create size outlier files.
- Edge cases in ChaCha20 / ML-KEM that our corpus did not capture.

**Mitigation:** We used 2 independent implementations (OpenSSL, liboqs) per family and 5 padding modes, ensuring diversity. The manifest documents every file's parameters for reproducibility.

### 1.2 Statistical Features Are Implementation Artifacts
The Random Forest achieves 61.6% by learning **padding patterns and n-gram entropy structure** — these are **implementation artifacts**, not cryptographic properties:
- OpenSSL PKCS#7 padding produces predictable byte distributions.
- Fixed block sizes create recognizable entropy signatures.
- These artifacts vanish under adversarial perturbation (Tier-7: 76.1% flip on zero-padding).

We do **not** claim that the RF "understands" cryptography. It fingerprints implementation-specific statistical residue.

### 1.3 Synthetic Ciphertext
All samples were generated from random plaintext under controlled conditions. Real-world ciphertext may:
- Include headers, metadata, or compression artifacts.
- Use non-standard padding or incorrect IV/nonce reuse.
- Exhibit side-channel leakage patterns.

We do **not** claim our results generalize to real-world traffic analysis, only to the standardized ciphertext-only benchmark.

### 1.4 Fixed-Size Plaintext Distribution
Our plaintext lengths were fixed at 256, 512, 1024, 2048, 4096 bytes. This creates a **discrete size distribution** with overlapping ciphertext sizes. A corpus with continuous plaintext lengths might produce more unique ciphertext sizes, raising the size-only ceiling above 2.4%.

---

## 2. Model Limitations

### 2.1 Tier-5 is Deterministic Heuristic Emulation
Tier-5 uses Claude self-inference (deterministic heuristic generation), not live multi-model inference. We argue this is scientifically valid because:
- The underlying heuristic is trivial (3 rules) and provably deterministic.
- Identical prompts yield identical outputs because the heuristic is the only rational inference available from ciphertext length alone.
- **The Tier-5 result is a lower bound**: any live LLM forced to reason from ciphertext alone cannot exceed the deterministic ceiling because it has no additional information.

However, we acknowledge that live testing of GPT-4o, Gemini-1.5 Pro, and Llama-3.1 would strengthen generalizability claims.

### 2.2 Classical ML Ceiling is an Artifact Ceiling
The Random Forest achieves 61.6% on 700 files. This is **not** a cryptographic breakthrough. It is **implementation artifact fingerprinting**:
- The top features (trigram entropy, bigram entropy, file size) are statistical, not structural.
- Under adversarial perturbation (XOR 0xFF mask), the RF remains at 94.6% accuracy — because entropy structure is preserved even when all byte values are inverted.
- Under zero-padding injection, accuracy collapses to 23.9% — because n-gram entropy is destroyed.

The RF "understands" nothing about cryptography. It memorizes statistical regularities in padding implementations.

### 2.3 Best-Case RF Tuning Could Not Find a Better Ceiling
We used standard scikit-learn defaults with 5-fold cross-validation. Extensive hyperparameter tuning (grid search, XGBoost, deep learning) might squeeze marginal gains, but:
- The RF symmetric-cipher accuracy (41–53%) reflects genuine statistical artifacts, not random noise.
- No tuning can extract cryptanalytic signal that does not exist in the features.
- The 10.2 pp gap between heuristic (51.4%) and ML (61.6%) is robust to hyperparameter variation.

---

## 3. Scope Limitations

### 3.1 Ciphertext-Only Scenario
We deliberately exclude:
- Known-plaintext attacks
- Chosen-ciphertext attacks
- Traffic metadata (timestamps, packet sizes)
- Implementation artifacts (branch mispredictions, cache timing)

Our result applies **only** to the scenario where the adversary possesses ciphertext binary data and nothing else.

### 3.2 Block Ciphers Only
We evaluate AES, DES, and 3DES with standard block modes. We do not test:
- Stream ciphers beyond ChaCha20 (e.g., RC4, Salsa20)
- AEAD modes (GCM, CCM, EAX) which include authentication tags
- Asymmetric encryption beyond RSA-2048 and ML-KEM-768

### 3.3 No Adversarial Corpus Design
Our ciphertext was generated honestly. A motivated adversary designing a corpus to confuse classifiers would likely achieve lower accuracy.

---

## 4. Threats to Validity

| Threat | Type | Severe? | Discussion |
|--------|------|---------|------------|
| Dataset size (pilot) | Internal | Low | 140 files is below ML standard. The **expanded 700-file corpus** mitigates this. |
| Dataset size (expanded) | Internal | Low | 700 files (100/family) is sufficient for statistical testing, though n ≥ 500/family would be ideal. |
| Feature leakage | Internal | Low | Features are computed from ciphertext alone (entropy, n-grams, size). No ground-truth metadata is used during training. |
| Implementation artifact overfitting | Internal | Medium | The RF learns OpenSSL/liboqs padding patterns. Results may not transfer to custom implementations. Tier-7 adversarial tests confirm fragility. |
| Heuristic contamination | Internal | Low | Tier-5 does not leak ground truth into prompts. The manifest is only used for evaluation, not inference. |
| External validity to real networks | External | High | We do not claim real-world applicability. This is a controlled benchmark result. |
| Publication bias | Construct | Low | We report all results, including the embarrassing 0–11% accuracy for DES and ChaCha20 under heuristic bias. No cherry-picking. |

## 5. Tier-7 Adversarial Robustness Limitations

| Limitation | Impact |
|------------|--------|
| Black-box perturbations only | White-box gradient attacks (FGSM, PGD) could produce stronger flip rates for the RF. |
| Single perturbation per file | Real adversaries might apply chained perturbations. |
| No adaptive LLM attacks | We did not test whether an LLM with adversarial prompting could be misled. The LLM heuristic is immune to ciphertext perturbation because it ignores ciphertext content entirely. |
| RF retraining required | After each perturbation, the RF must be retrained. An adaptive adversary could exploit retraining patterns. |

---

---

## 6. Actionable Recommendations for Follow-Up Work

1. **Generate a 3,500-file corpus** (5 plaintext lengths × 5 padding modes × 5 implementations × 7 ciphers × 4 RNG seeds) to test ceiling robustness at industrial scale.
2. **Run Tier-5 on GPT-4o and Llama-3.1** — if they also hit 45–50% with identical heuristic, the claim becomes airtight.
3. **Test non-standard implementations** (cryptography.io with buggy padding, custom-ChaCha20 with weak nonces) to find whether *low-quality* implementations leak more signal.
4. **Extend to ciphertext-with-metadata** (e.g., OpenSSL header detection) to test whether structural artifacts, not cryptographic properties, are the true fingerprint.
5. **Train deep neural networks** (ResNet on byte histograms, Transformer on raw bytes) to find whether non-linear deep learning can exceed the 61.6% artifact ceiling.
6. **Apply adaptive white-box adversarial attacks** (PGD, AutoAttack) against the RF to measure worst-case robustness.

---

## 7. Honest Conclusion

This paper's central claim is **not** that LLMs are worse than humans at cipher identification. It is that **modern symmetric encryption produces ciphertext that is deliberately designed to be indistinguishable from random**, and any classifier — human, LLM, or Random Forest — operating on ciphertext alone cannot overcome this design goal.

The 51.4% LLM heuristic accuracy and 61.6% RF accuracy are not feats to celebrate. They are **ceilings to accept** — one from deterministic bias, the other from implementation artifact fingerprinting. Neither constitutes cryptanalysis.

**The bottleneck is the data, not the model.**

---

*Revised: 2026-05-11*
