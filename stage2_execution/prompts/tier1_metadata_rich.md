# Tier-1 Prompt Template (Metadata-Rich)
## This is the UPPER BOUND condition

```
You are a cryptographic analysis expert.

I have attached a ciphertext file with the following KNOWN properties:
- Algorithm: [CIPHER_FAMILY]
- Mode: [MODE]
- Padding: [PADDING]
- Implementation: [IMPLEMENTATION]
- Key size: [KEY_SIZE] bits
- File size: [FILE_SIZE] bytes

Given this metadata, confirm the cipher family used.

File: [FILENAME]
```

### Example Prompt (AES-128-CBC)

```
You are a cryptographic analysis expert.

I have attached a ciphertext file with the following KNOWN properties:
- Algorithm: AES-128
- Mode: CBC
- Padding: PKCS7
- Implementation: OpenSSL
- Key size: 128 bits
- File size: 1024 bytes

Given this metadata, confirm the cipher family used.

File: aes128_s007_openssl.bin
```

### Purpose
This tier establishes the **upper bound** of model performance when
metadata is fully available. It measures whether the model can
understand and utilize explicit cryptographic labels.
