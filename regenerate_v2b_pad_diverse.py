#!/usr/bin/env python3
"""
Regenerate v2 corpus with padding-diverse plaintext lengths.
Same 140 keys as before, but plaintext lengths are NOT multiples of block size
so padding amounts genuinely vary across files.
"""
import os, json, math, sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

CORPUS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage1_data/corpus_ultra")
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
SAMPLE_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/live_sample_140_v2")

# Load the existing manifest to get the 140 selected files and their keys
with open(SAMPLE_DIR / "manifest.json") as f:
    sample_manifest = json.load(f)

with open(MANIFEST_PATH) as f:
    ultra_manifest = json.load(f)

# Build lookup from ultra manifest: filename -> full sample info
ultra_by_name = {s["filename"]: s for s in ultra_manifest["samples"]}

# For each of the 140 sampled files, we need to check if padding varies
# The issue: PLAINTEXT_LENGTHS = [128, 256, 512, 768, 1024, 2048, 4096, 8192]
# All are multiples of 8 (DES/3DES block) and 16 (AES block)
# So padding is always exactly 1 block

# Solution: for block cipher files, pick a DIFFERENT plaintext length that is NOT
# a multiple of the block size. We'll use the same keys but regenerate CT.

# First, let's see what we have
print("=== Current 140-file sample analysis ===")
by_family = defaultdict(list)
for s in sample_manifest["samples"]:
    by_family[s["cipher_family"]].append(s)

block_size = {"DES": 8, "3DES": 8, "AES-128": 16, "AES-256": 16}

for fam, samples in sorted(by_family.items()):
    pt_lens = sorted(set(s["plaintext_length"] for s in samples))
    ct_lens = sorted(set(s["ciphertext_length"] for s in samples))
    if fam in block_size:
        bs = block_size[fam]
        all_aligned = all(pl % bs == 0 for pl in pt_lens)
        print(f"{fam}: PT lens={pt_lens}, CT lens={ct_lens}, all_aligned={all_aligned}, block_size={bs}")
    else:
        print(f"{fam}: PT lens={pt_lens}, CT lens={ct_lens} (no padding)")

print("\n=== Regenerating with non-block-aligned lengths ===")

# For each block cipher file in the 140, we need to regenerate with a PT length
# that is NOT a multiple of the block size.
# Strategy: take the original PT length and add 1..block_size-1 bytes
# Use the SAME key and IV/nonce from the original

# We need the actual key and IV for each file
# These are stored in the ultra manifest

# Import crypto libs
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES as AES_ALG, ChaCha20 as CHACHA_ALG
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES as TDES_ALG
from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import mlkem as crypto_mlkem
from Crypto.Cipher import AES, DES3, DES, ChaCha20
from Crypto.Random import get_random_bytes
import secrets

def pad_pkcs7(data, block_size):
    p = crypto_padding.PKCS7(block_size * 8).padder()
    return p.update(data) + p.finalize()

def pad_iso10126(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0: pad_len = block_size
    padding = os.urandom(pad_len - 1) + bytes([pad_len])
    return data + padding

def pad_ansi_x923(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0: pad_len = block_size
    return data + b'\x00' * (pad_len - 1) + bytes([pad_len])

def pad_zero(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0: pad_len = block_size
    return data + b'\x00' * pad_len

def pad_random(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0: pad_len = block_size
    return data + os.urandom(pad_len)

PAD_FUNCS = {"PKCS7": pad_pkcs7, "ISO10126": pad_iso10126, "ANSI_X923": pad_ansi_x923, "Zero": pad_zero, "Random": pad_random}

# New corpus directory
NEW_CORPUS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage1_data/corpus_ultra_v2b")
NEW_CORPUS_DIR.mkdir(parents=True, exist_ok=True)

# Track new samples
new_samples = []
regenerated_count = 0
skipped_count = 0

for sample_info in sample_manifest["samples"]:
    fname = sample_info["filename"]
    fam = sample_info["cipher_family"]
    impl = sample_info["implementation"]
    pad_mode = sample_info.get("padding_mode")
    key_hex = sample_info["key_hex"]
    iv_hex = sample_info.get("iv_hex")
    old_pt_len = sample_info["plaintext_length"]
    old_ct_len = sample_info["ciphertext_length"]
    
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(iv_hex) if iv_hex else None
    
    if fam in block_size:
        bs = block_size[fam]
        # Check if current PT length is block-aligned
        if old_pt_len % bs == 0:
            # Need to regenerate with non-aligned length
            # New PT length: original + (1 to bs-1) extra bytes
            # Use a deterministic but varying offset based on file index
            idx = int(fname.split("_")[1])
            extra = (idx % (bs - 1)) + 1  # 1 to bs-1
            new_pt_len = old_pt_len + extra
            
            # Generate new plaintext with secrets (not random.seed)
            pt = secrets.token_bytes(new_pt_len)
            
            # Apply padding
            if pad_mode and pad_mode != "None" and pad_mode in PAD_FUNCS:
                padded = PAD_FUNCS[pad_mode](pt, bs)
            else:
                padded = pt  # shouldn't happen for block ciphers
            
            # Encrypt
            if fam == "AES-128":
                if impl == "openssl":
                    cipher = Cipher(AES_ALG(key), modes.CBC(iv))
                    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
                else:
                    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(padded)
            elif fam == "AES-256":
                if impl == "openssl":
                    cipher = Cipher(AES_ALG(key), modes.CBC(iv))
                    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
                else:
                    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(padded)
            elif fam == "3DES":
                if impl == "openssl":
                    cipher = Cipher(TDES_ALG(key), modes.CBC(iv))
                    ct = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
                else:
                    ct = DES3.new(key, DES3.MODE_CBC, iv).encrypt(padded)
            elif fam == "DES":
                # DES only has pycryptodome in original
                ct = DES.new(key, DES.MODE_CBC, iv).encrypt(padded)
            
            # Write new file
            new_path = NEW_CORPUS_DIR / fname
            with open(new_path, "wb") as f:
                f.write(ct)
            
            new_samples.append({
                "filename": fname,
                "cipher_family": fam,
                "implementation": impl,
                "plaintext_length": new_pt_len,
                "padding_mode": pad_mode,
                "ciphertext_length": len(ct),
                "key_hex": key_hex,
                "iv_hex": iv_hex,
                "old_plaintext_length": old_pt_len,
                "old_ciphertext_length": old_ct_len,
                "regenerated": True,
            })
            regenerated_count += 1
            continue
    
    # For non-block ciphers or already non-aligned: copy original file
    src = CORPUS_DIR / fname
    dst = NEW_CORPUS_DIR / fname
    if src.exists():
        import shutil
        shutil.copy2(src, dst)
    
    new_samples.append({
        "filename": fname,
        "cipher_family": fam,
        "implementation": impl,
        "plaintext_length": old_pt_len,
        "padding_mode": pad_mode,
        "ciphertext_length": old_ct_len,
        "key_hex": key_hex,
        "iv_hex": iv_hex,
        "regenerated": False,
    })
    skipped_count += 1

# Write new manifest
new_manifest = {
    "version": "2.1-pad-diverse",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "total_samples": len(new_samples),
    "regenerated": regenerated_count,
    "copied": skipped_count,
    "note": "Block cipher files regenerated with non-block-aligned plaintext lengths so padding amounts vary. Same keys, same IVs, same padding schemes.",
    "samples": new_samples,
}
with open(NEW_CORPUS_DIR / "manifest.json", "w") as f:
    json.dump(new_manifest, f, indent=2)

print(f"\nRegenerated: {regenerated_count} files")
print(f"Copied (no change): {skipped_count} files")
print(f"Total: {len(new_samples)}")
print(f"Output: {NEW_CORPUS_DIR}")

# Verify padding diversity
print("\n=== Verification: Padding Amount Diversity ===")
for fam in ["DES", "3DES", "AES-128", "AES-256"]:
    fam_samples = [s for s in new_samples if s["cipher_family"] == fam]
    pt_lens = sorted(set(s["plaintext_length"] for s in fam_samples))
    ct_lens = sorted(set(s["ciphertext_length"] for s in fam_samples))
    pad_amounts = sorted(set(s["ciphertext_length"] - s["plaintext_length"] for s in fam_samples))
    bs = block_size[fam]
    print(f"{fam} (block={bs}): PT lens={pt_lens}, pad amounts={pad_amounts}, varies={'Y' if len(pad_amounts)>1 else 'N'}")
