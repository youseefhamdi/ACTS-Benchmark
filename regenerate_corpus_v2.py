#!/usr/bin/env python3
"""
Regenerate 140-file evaluation corpus with:
- NO fixed random seed for selection
- Unique CSPRNG key per file (including RSA/ML-KEM)
- Distinct random plaintext per file
- Random IV/nonce per file (where applicable)
- secrets.SystemRandom for all random choices
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES as AES_ALG, ChaCha20 as CHACHA_ALG
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES as TDES_ALG
from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import mlkem as crypto_mlkem

from Crypto.Cipher import AES, DES3, DES, ChaCha20
from Crypto.Random import get_random_bytes

# Use secrets for all random choices (CSPRNG)
rng = secrets.SystemRandom()

# --- Padding functions (same as before) ---

def pad_pkcs7(data, block_size):
    p = crypto_padding.PKCS7(block_size * 8).padder()
    return p.update(data) + p.finalize()

def pad_iso10126(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    padding = os.urandom(pad_len - 1) + bytes([pad_len])
    return data + padding

def pad_ansi_x923(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + b'\x00' * (pad_len - 1) + bytes([pad_len])

def pad_zero(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + b'\x00' * pad_len

def pad_random(data, block_size):
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + os.urandom(pad_len)

PAD_FUNCS = {
    "PKCS7": pad_pkcs7,
    "ISO10126": pad_iso10126,
    "ANSI_X923": pad_ansi_x923,
    "Zero": pad_zero,
    "Random": pad_random,
}

CIPHERS = {
    "AES-128": {"key_size": 16, "iv_size": 16, "block_size": 16},
    "AES-256": {"key_size": 32, "iv_size": 16, "block_size": 16},
    "3DES":    {"key_size": 24, "iv_size": 8,  "block_size": 8},
    "DES":     {"key_size": 8,  "iv_size": 8,  "block_size": 8},
}

PLAINTEXT_LENGTHS = [128, 256, 512, 768, 1024, 2048, 4096, 8192]
RSA_PLAINTEXT_LENGTHS = [16, 32, 64, 128, 200]
PADDING_MODES = ["PKCS7", "ISO10126", "ANSI_X923", "Zero", "Random"]

N_PER_FAMILY = 20
FAMILIES = ["3DES", "AES-128", "AES-256", "ChaCha20", "DES", "ML-KEM-768", "RSA-2048"]
OUTDIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results/live_sample_140_v2")
MANIFEST_PATH = OUTDIR / "manifest.json"


def write_bin(name, data):
    path = OUTDIR / name
    with open(path, "wb") as f:
        f.write(data)
    return name


def aes_encrypt_openssl(pt, key, iv):
    cipher = Cipher(AES_ALG(key), modes.CBC(iv))
    return cipher.encryptor().update(pt) + cipher.encryptor().finalize()

def aes_encrypt_pycrypto(pt, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pt)

def des3_encrypt_openssl(pt, key, iv):
    cipher = Cipher(TDES_ALG(key), modes.CBC(iv))
    return cipher.encryptor().update(pt) + cipher.encryptor().finalize()

def des3_encrypt_pycrypto(pt, key, iv):
    return DES3.new(key, DES3.MODE_CBC, iv).encrypt(pt)

def des_encrypt_pycrypto(pt, key, iv):
    return DES.new(key, DES.MODE_CBC, iv).encrypt(pt)

def chacha_encrypt_openssl(pt, key, nonce):
    cipher = Cipher(CHACHA_ALG(key, nonce), mode=None)
    return cipher.encryptor().update(pt)

def chacha_encrypt_pycrypto(pt, key, nonce):
    return ChaCha20.new(key=key, nonce=nonce).encrypt(pt)

def rsa_encrypt_openssl(pt, pubkey):
    return pubkey.encrypt(pt, rsa_padding.PKCS1v15())

def rsa_encrypt_pycrypto(pt, key):
    from Crypto.Cipher import PKCS1_v1_5
    return PKCS1_v1_5.new(key).encrypt(pt)

def mlkem_encapsulate_openssl(pubkey):
    ss, ct = pubkey.encapsulate()
    return ct, ss


def generate_block_family(name, cfg):
    count = 0
    impls = ["openssl", "pycryptodome"]
    block_size = cfg["block_size"]
    key_size = cfg["key_size"]
    iv_size = cfg["iv_size"]

    # Build candidate pool
    base = list(product(PADDING_MODES, PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < N_PER_FAMILY:
        candidates.extend(base)
    rng.shuffle(candidates)
    selected = candidates[:N_PER_FAMILY]

    impl_funcs = {
        "openssl": {
            "AES-128": aes_encrypt_openssl,
            "AES-256": aes_encrypt_openssl,
            "3DES": des3_encrypt_openssl,
            "DES": des_encrypt_pycrypto,
        }[name],
        "pycryptodome": {
            "AES-128": aes_encrypt_pycrypto,
            "AES-256": aes_encrypt_pycrypto,
            "3DES": des3_encrypt_pycrypto,
            "DES": des_encrypt_pycrypto,
        }[name],
    }

    for idx, (pad_mode, pt_len, impl) in enumerate(selected, 1):
        pt = os.urandom(pt_len)
        padded = PAD_FUNCS[pad_mode](pt, block_size)
        key = os.urandom(key_size)
        iv = os.urandom(iv_size)
        ct = impl_funcs[impl](padded, key, iv)

        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        count += 1

        sha256 = hashlib.sha256(ct).hexdigest()
        yield {
            "filename": filename,
            "cipher_family": name,
            "ground_truth": name,
            "implementation": impl,
            "mode": "CBC",
            "padding_mode": pad_mode,
            "key_size_bits": key_size * 8,
            "key_hex": key.hex(),
            "iv_hex": iv.hex(),
            "plaintext_length": pt_len,
            "ciphertext_length": len(ct),
            "file_size_bytes": len(ct),
            "sha256": sha256,
        }


def generate_chacha():
    name = "ChaCha20"
    key_size = 32
    nonce_size_openssl = 16
    nonce_size_pycrypto = 12
    impls = ["openssl", "pycryptodome"]

    base = list(product(PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < N_PER_FAMILY:
        candidates.extend(base)
    rng.shuffle(candidates)
    selected = candidates[:N_PER_FAMILY]

    for idx, (pt_len, impl) in enumerate(selected, 1):
        pt = os.urandom(pt_len)
        key = os.urandom(key_size)
        if impl == "openssl":
            nonce = os.urandom(nonce_size_openssl)
            ct = chacha_encrypt_openssl(pt, key, nonce)
        else:
            nonce = os.urandom(nonce_size_pycrypto)
            ct = chacha_encrypt_pycrypto(pt, key, nonce)

        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        sha256 = hashlib.sha256(ct).hexdigest()
        yield {
            "filename": filename,
            "cipher_family": name,
            "ground_truth": name,
            "implementation": impl,
            "mode": "stream cipher",
            "padding_mode": None,
            "key_size_bits": 256,
            "key_hex": key.hex(),
            "iv_hex": nonce.hex(),
            "plaintext_length": pt_len,
            "ciphertext_length": len(ct),
            "file_size_bytes": len(ct),
            "sha256": sha256,
        }


def generate_rsa():
    name = "RSA-2048"
    impls = ["openssl", "pycryptodome"]

    base = list(product(RSA_PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < N_PER_FAMILY:
        candidates.extend(base)
    rng.shuffle(candidates)
    selected = candidates[:N_PER_FAMILY]

    # Generate unique keypair per file
    for idx, (pt_len, impl) in enumerate(selected, 1):
        pt = os.urandom(pt_len)

        if impl == "openssl":
            priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            pubkey = priv.public_key()
            ct = rsa_encrypt_openssl(pt, pubkey)
            pubkey_bytes = pubkey.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            key_hex = pubkey_bytes.hex()
        else:
            from Crypto.PublicKey import RSA
            k = RSA.generate(2048)
            ct = rsa_encrypt_pycrypto(pt, k)
            key_hex = k.export_key().hex()

        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        sha256 = hashlib.sha256(ct).hexdigest()
        yield {
            "filename": filename,
            "cipher_family": name,
            "ground_truth": name,
            "implementation": impl,
            "mode": "PKCS1v15",
            "padding_mode": "PKCS1v15",
            "key_size_bits": 2048,
            "key_hex": key_hex,
            "iv_hex": None,
            "plaintext_length": pt_len,
            "ciphertext_length": len(ct),
            "file_size_bytes": len(ct),
            "sha256": sha256,
        }


def generate_mlkem():
    name = "ML-KEM-768"
    impl = "openssl"

    for idx in range(1, N_PER_FAMILY + 1):
        # Unique keypair per file
        kem = crypto_mlkem.MLKEM768PrivateKey.generate()
        ct, ss = mlkem_encapsulate_openssl(kem.public_key())

        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        sha256 = hashlib.sha256(ct).hexdigest()
        yield {
            "filename": filename,
            "cipher_family": name,
            "ground_truth": name,
            "implementation": impl,
            "mode": "key encapsulation",
            "padding_mode": None,
            "key_size_bits": 768,
            "key_hex": kem.public_key().public_bytes_raw().hex(),
            "iv_hex": None,
            "plaintext_length": len(ss),
            "ciphertext_length": len(ct),
            "file_size_bytes": len(ct),
            "sha256": sha256,
        }


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating v2 corpus: {N_PER_FAMILY} per family = {N_PER_FAMILY * 7} total")
    print(f"Output: {OUTDIR}")
    print("NO FIXED SEED — using secrets.SystemRandom (CSPRNG)")
    print("=" * 60)

    samples = []
    total = 0

    for fam in FAMILIES:
        print(f"  Generating {fam}...")
        if fam in CIPHERS:
            for s in generate_block_family(fam, CIPHERS[fam]):
                samples.append(s)
                total += 1
        elif fam == "ChaCha20":
            for s in generate_chacha():
                samples.append(s)
                total += 1
        elif fam == "RSA-2048":
            for s in generate_rsa():
                samples.append(s)
                total += 1
        elif fam == "ML-KEM-768":
            for s in generate_mlkem():
                samples.append(s)
                total += 1
        print(f"    done: {N_PER_FAMILY}")

    manifest = {
        "version": "live_eval_140_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": None,
        "random_source": "secrets.SystemRandom (os.urandom)",
        "total_files": total,
        "files_per_family": N_PER_FAMILY,
        "families": FAMILIES,
        "samples": samples,
    }

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 60)
    print(f"DONE. Generated {total} samples in {OUTDIR}")
    print(f"Manifest: {MANIFEST_PATH}")

    # Verify
    keys = set(s["key_hex"] for s in samples)
    sha256s = set(s["sha256"] for s in samples)
    print(f"Verification: {len(keys)}/{total} distinct keys, {len(sha256s)}/{total} distinct ciphertexts")

    # Per-family
    for fam in FAMILIES:
        fs = [s for s in samples if s["cipher_family"] == fam]
        dk = len(set(s["key_hex"] for s in fs))
        ds = len(set(s["sha256"] for s in fs))
        print(f"  {fam}: {len(fs)} files, {dk} distinct keys, {ds} distinct ct")


if __name__ == "__main__":
    main()
