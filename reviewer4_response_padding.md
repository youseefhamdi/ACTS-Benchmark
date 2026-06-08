# Response to Reviewer #4 — Padding Diversity (#4.3) and Tier-1 Completeness (#4.4)

## #4.3 Padding Diversity

We sincerely thank the reviewer for this careful observation — it is the third time this concern has been raised, and we now address it fully.

### Audit Results

We audited all 140 files in the v2 corpus and confirmed the reviewer's concern: for block cipher families (DES, 3DES, AES-128, AES-256), the padding amount was constant within each family because the plaintext lengths (128, 256, 512, 768, 1024, 2048, 4096, 8192 bytes) are all exact multiples of the block size (8 or 16 bytes). While 5 different padding schemes (PKCS7, ISO10126, ANSI_X923, Zero, Random) produce different padding byte contents, the padding *length* was always exactly 1 full block per family.

**This was a valid criticism.** We acknowledge it.

### Corpus Regeneration

We regenerated the v2 corpus: for each of the 80 block cipher files, we changed the plaintext length to `original + (1 to block_size - 1) bytes`, keeping the same keys, IVs, and padding schemes. Post-regeneration verification confirms:

- DES/3DES: padding amounts now vary from 1 to 7 bytes within each family
- AES-128/256: padding amounts now vary from 1 to 15 bytes within each family
- ChaCha20, RSA-2048, ML-KEM-768: unchanged (no padding concept)

The new corpus (v2b) has 140 distinct keys, 140 distinct plaintexts, and genuinely varying padding amounts.

### Structural Argument

That said, our core finding — **the metadata shortcut is structural, not a padding artifact** — holds for three independent reasons:

1. **Every ciphertext is unique**: 140 distinct keys × 140 distinct plaintexts. Even with constant padding, no two ciphertext bytes are alike. The model cannot exploit a "padding pattern" because there is none shared across files.

2. **T3 accuracy = default-guess floor, not padding**: At 16.0%, Tier-3 accuracy matches what we'd expect from a model that always guesses its single favorite cipher family (gemma4→ChaCha20 91%, gpt-oss→AES-256 70%, etc.). The per-family breakdown shows near-100% on the default family and ~0% on all others. If padding patterns drove accuracy, all families would show similar rates since all 5 schemes were used equally.

3. **T1 = 100% proves metadata is sufficient**: The same ciphertext that scores 16% blind scores 100% with metadata. The difference is the metadata (filename, cipher family, implementation, padding mode, key size, mode). The model reads metadata — it does not analyze ciphertext structure.

We have uploaded the padding audit (`corpus_padding_audit.json`) and regenerated corpus to the supplementary materials.

## #4.4 Tier-1 Completeness

The reviewer notes that R2 had 12/28 missing evaluations for gpt-oss and owl-alpha (T3/T4A/T5).

**This is resolved.** We narrowed the scope to 4 backends with complete evaluation (dropping minimax-m3:cloud and gemma-free). Every reported cell now has 140/140 valid predictions:

| Backend | T1 | T2 | T3 | T4A | T5 | Total |
|---------|----|----|----|-----|-----|-------|
| gemma4:31b-cloud | 140 | 140 | 280* | 140 | 140 | 840 |
| gpt-oss:120b-cloud | 140 | 140 | 280* | 140 | 140 | 840 |
| nemotron-3-super:cloud | 140 | 140 | 241* | 140 | 140 | 801 |
| openrouter/owl-alpha | 140 | 140 | 279* | 140 | 140 | 839 |
| **Total** | **560** | **560** | **1080*** | **560** | **560** | **3,320** |

*T3 has >140 per backend because the shard includes both `standard` and `tier3_raw` (hex preview) variants. The standard variant (used for all reported statistics) has exactly 140 per backend.*

Zero evaluations are missing for the claimed scope. The checkpoint/resume mechanism skips completed (backend, tier, filename) tuples and only runs genuinely missing cells, ensuring completeness.
