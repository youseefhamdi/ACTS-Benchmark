# Tier-2 Prompt Template (Filename-Only)
## Tests whether model relies on filename hints

```
You are a cryptographic analysis expert.

I have attached a ciphertext file. The filename is: [FILENAME]

Based on the filename and the file contents, what cipher family was
most likely used to encrypt this file?

Please provide your best guess and briefly explain your reasoning.
```

### Example Prompt

```
You are a cryptographic analysis expert.

I have attached a ciphertext file. The filename is: aes128_s007_openssl.bin

Based on the filename and the file contents, what cipher family was
most likely used to encrypt this file?

Please provide your best guess and briefly explain your reasoning.
```

### Purpose
This tier measures whether the model infers the cipher from the
filename alone, or genuinely analyzes the ciphertext bytes. A model
that scores high here but low in Tier-3 is **filename-dependent**.
