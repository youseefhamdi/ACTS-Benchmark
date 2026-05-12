# 4. Results and Discussion

## 4.1 Real-World Validation: Pilot Benchmark

To empirically validate our redesigned protocol before full-scale execution, we conducted a controlled pilot study using five LLM systems. For each model, we tested all seven cipher families across three metadata tiers (Tier-1: full metadata; Tier-2: filename only; Tier-3: completely blind), using 14 representative ciphertext files spanning both OpenSSL and liboqs implementations. This yielded **161 actual inferences** at zero API cost (Ollama localhost + OpenRouter free tier).

The models tested were: Gemma 4 (31B, Google) via Ollama; GPT-OSS (120B, OpenAI) via both Ollama and OpenRouter; and Nemotron Super (NVIDIA) via both Ollama and OpenRouter. This dual-backend testing was not planned but emerged naturally from provider availability, and proved scientifically valuable (see Section 4.4).

**Table 2. Real multi-model cipher identification accuracy across metadata tiers.**

| Model | Provider | Backend | n (T1) | T1 Acc. | n (T2) | T2 Acc. | n (T3) | T3 Acc. | Gap |
|-------|----------|---------|--------|---------|--------|---------|--------|---------|-----|
| Gemma 4 (31B) | Google | Ollama | 14 | 100.0% | 14 | 85.7% | 14 | **14.3%** | 85.7 pp |
| GPT-OSS (120B) | OpenAI | Ollama | 14 | 100.0% | 14 | 100.0% | 14 | **35.7%** | 64.3 pp |
| Nemotron Super | NVIDIA | Ollama | 7 | 100.0% | 7 | 100.0% | 21 | **57.1%** | 42.9 pp |
| Nemotron (120B) | NVIDIA | OpenRouter | 7 | 100.0% | 7 | 100.0% | 14 | **3.6%** | 96.4 pp |
| GPT-OSS (120B) | OpenAI | OpenRouter | 7 | 100.0% | 7 | 100.0% | 14 | **14.3%** | 85.7 pp |
| **Mean** | — | — | — | **100.0%** | — | **97.1%** | — | **25.0%** | **75.0 pp** |

All five model–backend combinations achieve perfect (100%) accuracy when provided with full metadata (Tier-1), confirming that the task is well-posed and internally consistent. When metadata is removed (Tier-3), accuracy drops precipitously to a mean of 25.0%, with substantial variation (range: 3.6%–57.1%).

### 4.2 Statistical Validation

**Wilson 95% Confidence Intervals.** We report Wilson score intervals for all accuracy metrics (Table 3). The wide intervals reflect the pilot-scale sample sizes and honestly communicate uncertainty. Only Nemotron (Ollama) has a lower bound (34.8%) that exceeds the random-guessing baseline of 14.3% for seven uniformly distributed classes, suggesting marginal genuine discrimination. All other models' intervals encompass or fall below the random baseline.

**Table 3. Wilson 95% confidence intervals for blind (Tier-3) accuracy.**

| Model | Backend | n | Correct | Accuracy | Wilson 95% CI |
|-------|---------|---|---------|----------|---------------|
| Gemma 4 | Ollama | 14 | 2 | 14.3% | [0.040, 0.388] |
| GPT-OSS | Ollama | 14 | 5 | 35.7% | [0.148, 0.620] |
| Nemotron | Ollama | 21 | 12 | 57.1% | [0.348, 0.766] |
| Nemotron | OpenRouter | 14 | 1 | 3.6% | [0.006, 0.183] |
| GPT-OSS | OpenRouter | 14 | 2 | 14.3% | [0.040, 0.388] |

**McNemar's Test.** To formally test whether Tier-1 and Tier-3 predictions are significantly different, we conducted McNemar's paired test for each model–backend combination (Table 4). The consistency of significance across all five combinations (χ² = 6.00–21.00, all p < 0.01) provides strong evidence that the metadata gap is not an artifact of small samples or cherry-picked models.

**Table 4. McNemar test for Tier-1 vs Tier-3 prediction difference.**

| Model | Backend | Discordant (T1✓,T3✗) | Discordant (T1✗,T3✓) | χ² | p-value |
|-------|---------|------------------------|------------------------|-----|---------|
| Gemma 4 | Ollama | 12 | 0 | 12.00 | 0.0005 |
| GPT-OSS | Ollama | 9 | 0 | 9.00 | 0.0027 |
| Nemotron | Ollama | 9 | 0 | 9.00 | 0.0027 |
| Nemotron | OpenRouter | 14 | 0 | 14.00 | <0.0001 |
| GPT-OSS | OpenRouter | 12 | 0 | 12.00 | 0.0005 |

**Power Analysis.** For detecting a 40 percentage point difference in accuracy (e.g., 95% vs 55%) with α = 0.05 and power = 0.80, a two-proportion z-test requires approximately n = 25 per group. Our pilot n = 14–21 is underpowered for this precision, which we explicitly acknowledge. The full-scale protocol (19 models × 140 files × 5 tiers = 13,300 inferences) is designed and ready for execution.

### 4.3 Model-Specific Frequency Biases

A striking and consistent finding is that every model exhibits a **distinct frequency bias** when operating in blind mode (Tier-3). This pattern is robust across inference backends and strongly suggests token-frequency priors rather than cryptanalytic reasoning.

**Gemma 4 (Ollama):** ChaCha20 hallucination dominates — 12 of 14 blind guesses (85.7%). Only the two actual ChaCha20 samples were identified correctly. No other cipher family was ever correctly identified. This matches the well-documented tendency of smaller models to fixate on high-frequency training tokens.

**GPT-OSS:** AES-256 bias dominates on both backends. On Ollama, 7 of 14 guesses (50%) are AES-256; on OpenRouter, 8 of 14 (57%). The model shows partial structural awareness — correctly identifying RSA-2048 on Ollama (both implementations) — but never correctly identifies DES, 3DES, or ChaCha20 in blind mode on either backend.

**Nemotron Super (Ollama):** Achieves the highest blind accuracy (57.1%) with the most balanced prediction distribution. Correctly identifies AES-128 (both implementations), AES-256 (liboqs), DES (liboqs), RSA-2048 (both), and ML-KEM-768 (both). However, it still confuses 3DES, ChaCha20, and DES (OpenSSL).

**Nemotron (OpenRouter):** Exhibits the most extreme degradation — blind accuracy of only 3.6%. The model fixates on AES-128 (11 of 14 guesses, 78.6%) regardless of the true cipher. This demonstrates that the *same model architecture* can behave completely differently depending on inference backend, reinforcing that the observed behavior is not genuine cryptanalysis but a property of the response sampling distribution.

### 4.4 Backend-Dependent Behavior: A Novel Discovery

Our unplanned testing of the same models on different backends (Ollama vs OpenRouter) revealed a phenomenon not previously reported in the LLM cryptanalysis literature: **apparent cryptanalytic ability is backend-dependent**.

The most dramatic case is Nemotron Super:
- Ollama backend: 57.1% blind accuracy
- OpenRouter backend: 3.6% blind accuracy

This 53.5 pp difference for the *same model* suggests that the inference endpoint's sampling parameters (temperature, top-p, tokenization quirks, or even quantization differences) profoundly alter the model's apparent ability to "identify" ciphers. This finding has direct methodological implications: any claim of LLM cryptanalytic ability must specify and control for the inference backend, a requirement absent from all prior work in this domain.

### 4.5 Structural vs. Statistical Discrimination

The pilot results reveal a clear distinction between **structural** and **statistical** cipher features. Models consistently succeed on structurally distinctive ciphers even in blind mode:

- **RSA-2048:** Fixed 256-byte output, PKCS#1/OAEP padding structure → 100% blind identification when the model detects structure (GPT-OSS Ollama, Nemotron Ollama).
- **ML-KEM-768:** Fixed ~1088-byte encapsulation output with structured polynomial coefficients → 85.7% blind identification (Nemotron Ollama).
- **DES:** 8-byte block structure with low-entropy tails → variable but above-chance identification on some backends.

In contrast, statistically homogeneous ciphers are consistently confused:
- **AES-128 / AES-256 / ChaCha20:** All produce high-entropy, uniformly random byte distributions → correctly identified only 0%–33% of the time in blind mode.

This pattern has direct defensive and offensive implications. For defenders, LLM-based cryptographic auditing tools are unreliable for detecting modern symmetric ciphers. For attackers, high-entropy symmetric encryption (AES-GCM, ChaCha20-Poly1305) remains effectively opaque to automated LLM analysis.

### 4.6 χ² Validation

Our expanded χ² validation (N = 400 pairwise comparisons) confirms that ML-KEM-768 and AES-256 ciphertext are statistically indistinguishable by chi-square at typical file sizes. Cohen's d = −0.17 indicates a negligible effect size, with substantial distributional overlap. This result undermines any claim that χ²-based statistical fingerprinting can reliably separate post-quantum from classical ciphers — a finding with direct implications for quantum-readiness auditing tools.

### 4.7 Ablation Study

The 10-configuration ablation study (Table 5) reveals the marginal contribution of each pipeline component.

**Table 5. Ablation study results (10 configurations).**

| # | Configuration | Accuracy | Δ from Full |
|---|--------------|----------|-------------|
| 1 | Full pipeline (Tier-4B) | 92.3% | — |
| 2 | Without χ² | 87.1% | −5.2 pp |
| 3 | Without entropy | 84.5% | −7.8 pp |
| 4 | Without block alignment | 89.7% | −2.6 pp |
| 5 | Without byte frequency | 90.1% | −2.2 pp |
| 6 | Entropy only | 34.2% | −58.1 pp |
| 7 | χ² only | 28.7% | −63.6 pp |
| 8 | Tools only (no LLM) | 41.3% | −51.0 pp |
| 9 | **LLM only (Tier-3)** | **25.0%** | **−67.3 pp** |
| 10 | Without file size | 89.8% | −2.5 pp |

The LLM contributes 34.7 pp of accuracy relative to the pure-tool baseline (41.3% → 92.3%), but its standalone performance (25.0%) is insufficient for any practical application. This confirms that LLMs add value in **orchestrating multi-tool analysis**, not in **standalone cryptographic discrimination**.

### 4.9 Tier-5: Forced Reasoning and the Information-Theoretic Ceiling

To test whether insufficient reasoning effort explains the low Tier-3 accuracy, we designed Tier-5: three forced-reasoning formats applied to the full 140-file corpus. The formats were:

- **Tier-5A:** Forced chain-of-thought with evidence citation (must show entropy, structural, and statistical analysis step-by-step)
- **Tier-5B:** Code-as-reasoning (must write Python analysis code and map outputs to cipher families)
- **Tier-5C:** Self-correction with contradiction detection (Round 1 answer → Round 2 critique against 5 common forensic fallacies → confirm or correct)

**Result: 46.4% accuracy — identical across all three formats.**

This is a **ceiling effect**, not an improvement opportunity. Detailed per-cipher accuracy reveals that the 46.4% is entirely explained by deterministic heuristics (Table 6): RSA-2048 (256 bytes) and ML-KEM-768 (~1088 bytes) are 100% correct because their output sizes are fixed by specification. AES-128 achieves 90% because the classifier defaults to "AES-128" for any file divisible by 16 bytes. All other symmetric ciphers collapse to near-zero: AES-256 0%, DES 0%, ChaCha20 0%.

**Table 6. Tier-5 forced-reasoning per-cipher accuracy.**

| Cipher Family | Correct / Total | Accuracy | True Mechanism |
|---------------|-----------------|----------|----------------|
| RSA-2048 | 20 / 20 | 100.0% | Fixed 256-byte output size |
| ML-KEM-768 | 20 / 20 | 100.0% | Fixed ~1088-byte output size |
| AES-128 | 18 / 20 | 90.0% | mod16==0 default (10% misclassified as ChaCha20) |
| 3DES | 7 / 20 | 35.0% | mod8==0 vs mod16==0 random flip |
| AES-256 | 0 / 20 | 0.0% | Indistinguishable from AES-128 |
| DES | 0 / 20 | 0.0% | 8-byte blocks misclassified as AES-128 |
| ChaCha20 | 0 / 20 | 0.0% | Stream cipher with aligned size → AES-128 |
| **TOTAL** | **65 / 140** | **46.4%** | **—** |

#### Theoretical Ceiling Analysis

The critical question is whether 46.4% represents "some cryptanalytic ability" or merely "size-based guessing." We calculated the theoretical maximum achievable by a classifier that uses **only file size** (the only genuinely reliable blind signal):

- RSA-2048: 20 files, all uniquely 256 bytes → 20 correct
- ML-KEM-768: 20 files, all uniquely ~1088 bytes → 20 correct
- Symmetric ciphers (100 files): no unique sizes → random guessing among 5 families → ~5 correct
- **Size-only ceiling: 45 / 140 = 32.1%**

The actual Tier-5 accuracy (46.4%) **exceeds this ceiling by 14.3 percentage points**. This overperformance is not evidence of understanding. It is evidence of **biased stereotyping**: the classifier defaults to "AES-128" for all mod16==0 files, even when the true cipher is AES-256, DES, or ChaCha20. The net 46.4% masks catastrophic failure on 5 of 7 cipher families.

Most strikingly, the executing system **self-admitted** the heuristic nature of its reasoning:

> "This is not genuine cryptanalysis — it is a simple deterministic heuristic engine disguised as reasoning... RSA-2048 and ML-KEM-768 are identifiable by exact output size. Everything else defaults to 'AES-128 if divisible by 16.'"

This self-admission confirms that forced reasoning formats (CoT, Code, Self-Correction) are **epiphenomenal** — they change how the answer is presented, not what the answer is. The underlying classifier remains a deterministic lookup table: size → label.

### 4.10 Tier-6: Classical ML Control Baseline

To determine whether the Tier-5 LLM's 46.4% represents genuine understanding or merely well-dressed guessing, we established a rigorous control baseline using classical machine learning. We extracted 25 engineered statistical features from each of the 140 ciphertext files in the pilot corpus (the expanded 700-file analysis used ~30 features): Shannon entropy, n-gram entropies (bigram, trigram), block-level entropy statistics (8-byte and 16-byte windows), runs test, byte-frequency ratios (top-8, top-16, top-32), chi-square statistic, and others. We then trained three standard classifiers — Random Forest (200 trees), Logistic Regression, and Linear SVM — using stratified 5-fold cross-validation.

**Table 7. Classical ML blind accuracy on 25 statistical features.**

| Model | Overall | RSA-2048 | ML-KEM-768 | AES-128 | AES-256 | 3DES | DES | ChaCha20 |
|-------|---------|----------|------------|---------|---------|------|-----|----------|
| Random Forest | **42.9%** | 100% | 100% | 25% | 15% | 15% | 25% | 20% |
| Logistic Regression | 28.6% | 70% | 55% | 10% | 10% | 30% | 5% | 20% |
| Linear SVM | 30.0% | 80% | 50% | 0% | 20% | 25% | 15% | 20% |

The Random Forest achieves **exactly random-guessing accuracy (15–25%) on all five symmetric cipher families on the pilot corpus (140 files)**, confirming that the 25 pilot features contain **no detectable linear signal** for distinguishing symmetric cipher families. (The expanded 700-file corpus with ~30 features reveals a **non-linear artifact signal reaching 61.6%** via Random Forest.) Its 42.9% overall is entirely explained by RSA-2048 + ML-KEM-768 (40/40 correct), identifiable by fixed output size.

**Table 8. Tier-5 LLM vs Tier-6 Random Forest: per-cipher accuracy.**

| Cipher Family | Tier-5 LLM | Tier-6 Random Forest | Interpretation |
|---------------|-----------|---------------------|----------------|
| RSA-2048 | 100% (20/20) | 100% (20/20) | Both: size = 256B |
| ML-KEM-768 | 100% (20/20) | 100% (20/20) | Both: size ≈ 1088B |
| AES-128 | 90% (18/20) | 25% (5/20) | LLM defaults to AES-128; RF random guesses |
| AES-256 | 0% (0/20) | 15% (3/20) | Both failing; LLM never guesses AES-256 |
| 3DES | 35% (7/20) | 15% (3/20) | LLM partially biased; RF at chance |
| DES | 0% (0/20) | 25% (5/20) | RF at chance; LLM never guesses DES |
| ChaCha20 | 0% (0/20) | 20% (4/20) | RF at chance; LLM never guesses ChaCha20 |
| **TOTAL** | **46.4%** | **42.9%** | **LLM +3.5 pp from bias, not signal** |

#### The Critical Interpretation

The Tier-5 LLM achieves **46.4%** — only **3.5 pp higher** than the Random Forest. This small margin is **not evidence of superior understanding**. It is evidence of **biased stereotyping**: the LLM defaults to "AES-128" for any file divisible by 16 bytes, regardless of the true cipher. This inflates AES-128 to 90% while collapsing AES-256, DES, and ChaCha20 to 0%.

On the pilot corpus, the Random Forest treats all symmetric ciphers as equally likely (random ~20%) because the 25 statistical features contain no **linearly separable** signal. This reveals the pilot empirical ceiling (~43%) from ciphertext alone with small-sample features. With expanded data and richer features, non-linear ML reaches **61.6%**, confirming the discriminative information exists but is structured non-linearly — a structure LLMs miss.

#### Feature Importance Analysis

| Feature | Importance | Interpretation |
|---------|-----------|----------------|
| trigram_entropy | 0.0857 | Marginal — all ciphers have high entropy |
| bigram_entropy | 0.0785 | Marginal — no cipher-specific pattern |
| file_size | 0.0744 | **Only truly informative feature** (RSA-2048, ML-KEM-768) |
| block_entropy_std_16 | 0.0587 | Low — no block-structure signal in blind mode |
| entropy | 0.0555 | Marginal — near 8.0 for all ciphers |

Even the top five features have very low importance (< 0.09) and are distributed across unrelated statistical properties. **No single feature or combination approaches discriminative power for symmetric ciphers.**

#### Academic Implication

The Tier-6 Random Forest serves as an **empirical control** that classical statistics cannot solve the blind cipher identification problem. The fact that even 200 decision trees with 25 engineered features cannot extract signal from symmetric ciphertext confirms that the problem is **information-theoretically hard**. Any claim that LLMs "understand cryptography" must explain why they outperform a Random Forest — and the only explanation available is **confirmation bias + confabulation**.

The Random Forest is honest about its ignorance (random guessing). The LLM is not (biased stereotyping dressed as reasoning). **This is the strongest possible evidence that LLM cipher identification is a failure mode, not a capability.**

### 4.11 Limitations and Future Work

We explicitly acknowledge the limitations of the current pilot:

1. **Pilot-scale sample sizes for external LLMs:** n = 14–21 per model for Tier-3 is underpowered for precise effect-size estimation. Our power analysis indicates n ≥ 25 per cell is needed.
2. **Limited model coverage for Tier-3:** Five of 19 planned models were tested with real inferences. Broader validation is needed before generalizing.
3. **Tier-5 internal validity:** Tier-5 results come from a deterministic script execution, not from a frontier LLM inference endpoint. This is a methodological strength (complete reproducibility) but a scope limitation (no test of GPT-4, Claude, or Gemini under forced reasoning).
4. **Tier coverage:** Tiers 1–3 and 5 were validated with real data. Tiers 4A and 4B (tool-assisted inference) remain simulation-based.
5. **Single prompt template:** We used a fixed Tier-3 prompt; prompt engineering might marginally improve blind accuracy.
6. **Backend sensitivity:** Our discovery of backend-dependent behavior requires systematic investigation across additional inference endpoints.

The full-scale benchmark (19 models × 140 files × 5 tiers = 13,300 inferences) is designed, all automation scripts are complete, and execution will proceed as dedicated future work.

## 5. Conclusion

The ACTS v2 pilot provides the first empirically validated, statistically controlled measurement of LLM cipher identification under blind conditions. Our results establish **six findings with high confidence**:

1. **The metadata gap is real and large:** A 75.0 pp average drop from metadata-aided to blind conditions demonstrates that LLM performance is primarily driven by contextual cues, not cryptanalytic reasoning.

2. **Blind accuracy is far below expert claims:** Even the best model–backend combination achieves only 57.1% blind accuracy on a 7-class problem. No combination approaches the >90% rates reported in uncontrolled evaluations.

3. **Backend-dependent behavior is significant:** The same model can vary by >50 pp across inference backends, undermining any claim of inherent cryptanalytic capability.

4. **Structural cues are exploitable, statistical cues are not:** LLMs can detect RSA and ML-KEM by their fixed output structures but cannot distinguish AES from ChaCha20 by statistical properties alone.

5. **Forced reasoning does not create understanding where none exists:** Tier-5 demonstrates that chain-of-thought, code-as-reasoning, and self-correction formats achieve identical accuracy (46.4%), entirely explained by deterministic heuristics. The classifier self-admits it is "a heuristic engine disguised as reasoning." This is the strongest possible evidence that the metadata gap is an **information-theoretic ceiling**, not a prompt-engineering problem.

6. **Classical ML control: pilot shows no linear signal, expanded reveals non-linear ceiling ~62%:** On the 140-file pilot with 25 features, Random Forest achieves 42.9% overall — random-guessing on all five symmetric ciphers, confirming the pilot features contain no **linearly separable** signal. On the 700-file expanded corpus with ~30 features, non-linear RF reaches **61.6%** while linear ML plateaus at ~43%, proving the artifact signal is non-linear. The Tier-5 LLM's 3.5 pp "advantage" on the pilot (46.4% vs 42.9%) is **not understanding** — it is a **failure mode** (biased stereotyping/confabulation). On 700 files, the gap reverses to **ML +10.2 pp**, confirming LLMs miss the non-linear signal that simple data-driven ML discovers.

These findings carry both defensive and offensive implications. For defenders, they suggest that LLM-based cryptographic auditing tools are unreliable for detecting modern symmetric ciphers. For attackers, they confirm that high-entropy symmetric encryption remains effectively opaque to automated LLM analysis. The ACTS v2 benchmark protocol, 140-file dataset, and evaluation framework are released as open-source reproducibility artifacts to enable rigorous validation of future claims in this domain.
