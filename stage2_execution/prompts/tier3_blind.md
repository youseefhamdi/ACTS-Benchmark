# Tier-3 Prompt Template (Blind - No Metadata)
## PURE analytical capability test

```
You are a cryptographic forensics expert.

I have attached a ciphertext file. There is NO metadata available:
- The filename is generic (encrypted_s007.bin)
- No algorithm information is provided
- No implementation details are known

Analyze the raw binary content and determine what cipher family
was most likely used. Consider:
1. File size and structure
2. Byte-level entropy
3. Statistical patterns
4. Block alignment properties

Provide your best identification and explain your reasoning.
Note: The answer could be any modern or classical cipher family.
```

### Purpose
This is the **core blind inference test**. It reveals whether the
model has genuine cryptanalytic capability or relies on metadata
crutches. The accuracy gap between Tier-1 and Tier-3 is the
**metadata dependency metric**.
