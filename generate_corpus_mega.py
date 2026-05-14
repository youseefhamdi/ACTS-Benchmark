#!/usr/bin/env python3
"""Generate ACTS v2 MEGA ciphertext corpus — 500 samples per cipher family."""

import os
import json
import random
from datetime import datetime, timezone
from itertools import product

from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.primitives.ciphers.algorithms import AES as AES_ALG, ChaCha20 as CHACHA_ALG
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES as TDES_ALG
from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import mlkem as crypto_mlkem

from Crypto.Cipher import AES, DES3, DES, ChaCha20
from Crypto.Random import get_random_bytes

random.seed(42)


def pad_pkcs7(data: bytes, block_size: int) -> bytes:
    p = crypto_padding.PKCS7(block_size * 8).padder()
    return p.update(data) + p.finalize()


def pad_iso10126(data: bytes, block_size: int) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    padding = os.urandom(pad_len - 1) + bytes([pad_len])
    return data + padding


def pad_ansi_x923(data: bytes, block_size: int) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + b'\x00' * (pad_len - 1) + bytes([pad_len])


def pad_zero(data: bytes, block_size: int) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    if pad_len == 0:
        pad_len = block_size
    return data + b'\x00' * pad_len


def pad_random(data: bytes, block_size: int) -> bytes:
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
    "3DES": {"key_size": 24, "iv_size": 8, "block_size": 8},
    "DES": {"key_size": 8, "iv_size": 8, "block_size": 8},
}

PLAINTEXT_LENGTHS = [128, 256, 512, 768, 1024, 2048, 4096, 8192]
RSA_PLAINTEXT_LENGTHS = [16, 32, 64, 128, 200]
PADDING_MODES = ["PKCS7", "ISO10126", "ANSI_X923", "Zero", "Random"]

N_PER_FAMILY = 500
OUTDIR = os.path.join(os.path.dirname(__file__), "stage1_data", "corpus_mega")


def write_bin(name, data):
    path = os.path.join(OUTDIR, name)
    with open(path, "wb") as f:
        f.write(data)
    return name


def aes_encrypt_openssl(pt, key, iv):
    cipher = Cipher(AES_ALG(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(pt) + encryptor.finalize()


def aes_encrypt_pycrypto(pt, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pt)


def des3_encrypt_openssl(pt, key, iv):
    cipher = Cipher(TDES_ALG(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(pt) + encryptor.finalize()


def des3_encrypt_pycrypto(pt, key, iv):
    return DES3.new(key, DES3.MODE_CBC, iv).encrypt(pt)


def des_encrypt_pycrypto(pt, key, iv):
    return DES.new(key, DES.MODE_CBC, iv).encrypt(pt)


def chacha_encrypt_openssl(pt, key, nonce):
    cipher = Cipher(CHACHA_ALG(key, nonce), mode=None)
    encryptor = cipher.encryptor()
    return encryptor.update(pt)


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


samples = []


def generate_block_family(name, cfg, impl_funcs, n_target):
    count = 0
    impls = ["openssl", "pycryptodome"]
    block_size = cfg["block_size"]
    key_size = cfg["key_size"]
    iv_size = cfg["iv_size"]

    base = list(product(PADDING_MODES, PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < n_target:
        candidates.extend(base)
    random.shuffle(candidates)
    selected = candidates[:n_target]

    for idx, (pad_mode, pt_len, impl) in enumerate(selected, 1):
        pt = os.urandom(pt_len)
        padded = PAD_FUNCS[pad_mode](pt, block_size)
        key = os.urandom(key_size)
        iv = os.urandom(iv_size)
        ct = impl_funcs[impl](padded, key, iv)

        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        samples.append({
            "filename": filename,
            "cipher_family": name,
            "implementation": impl,
            "plaintext_length": pt_len,
            "padding_mode": pad_mode,
            "ciphertext_length": len(ct),
            "key_hex": key.hex(),
            "iv_hex": iv.hex(),
        })
        count += 1
        if count % 100 == 0:
            print(f"  {name}: generated {count}/{n_target}")
    return count


def generate_chacha(n_target):
    name = "ChaCha20"
    key_size = 32
    nonce_size_openssl = 16
    nonce_size_pycrypto = 12
    impls = ["openssl", "pycryptodome"]
    base = list(product(PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < n_target:
        candidates.extend(base)
    random.shuffle(candidates)
    selected = candidates[:n_target]

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
        samples.append({
            "filename": filename,
            "cipher_family": name,
            "implementation": impl,
            "plaintext_length": pt_len,
            "padding_mode": None,
            "ciphertext_length": len(ct),
            "key_hex": key.hex(),
            "iv_hex": nonce.hex(),
        })
        if idx % 100 == 0:
            print(f"  {name}: generated {idx}/{n_target}")
    return n_target


def generate_rsa(n_target):
    name = "RSA-2048"
    impls = ["openssl", "pycryptodome"]
    base = list(product(RSA_PLAINTEXT_LENGTHS, impls))
    candidates = []
    while len(candidates) < n_target:
        candidates.extend(base)
    random.shuffle(candidates)
    selected = candidates[:n_target]

    n_keys = 50  # reuse keys to keep generation fast
    rsa_keys_openssl = []
    rsa_keys_pycrypto = []
    print(f"  {name}: generating {n_keys} RSA keypairs...")
    for _ in range(n_keys):
        priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rsa_keys_openssl.append((priv, priv.public_key()))
    from Crypto.PublicKey import RSA
    for _ in range(n_keys):
        k = RSA.generate(2048)
        rsa_keys_pycrypto.append(k)
    print(f"  {name}: RSA key generation done.")

    for idx, (pt_len, impl) in enumerate(selected, 1):
        pt = os.urandom(pt_len)
        keyi = (idx - 1) % n_keys
        if impl == "openssl":
            _, pubkey = rsa_keys_openssl[keyi]
            ct = rsa_encrypt_openssl(pt, pubkey)
            pubkey_bytes = pubkey.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            key_hex = pubkey_bytes.hex()
        else:
            key = rsa_keys_pycrypto[keyi]
            ct = rsa_encrypt_pycrypto(pt, key)
            key_hex = key.export_key().hex()
        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        samples.append({
            "filename": filename,
            "cipher_family": name,
            "implementation": impl,
            "plaintext_length": pt_len,
            "padding_mode": "PKCS1v15",
            "ciphertext_length": len(ct),
            "key_hex": key_hex,
            "iv_hex": None,
        })
        if idx % 100 == 0:
            print(f"  {name}: generated {idx}/{n_target}")
    return n_target


def generate_mlkem(n_target):
    name = "ML-KEM-768"
    impl = "openssl"

    n_keys = 50
    print(f"  {name}: generating {n_keys} ML-KEM keypairs...")
    mlkem_keys = []
    for _ in range(n_keys):
        mlkem_keys.append(crypto_mlkem.MLKEM768PrivateKey.generate())
    print(f"  {name}: ML-KEM key generation done.")

    for idx in range(1, n_target + 1):
        kem = mlkem_keys[idx % n_keys]
        ct, ss = mlkem_encapsulate_openssl(kem.public_key())
        filename = f"{name}_{idx:04d}_{impl}.bin"
        write_bin(filename, ct)
        samples.append({
            "filename": filename,
            "cipher_family": name,
            "implementation": impl,
            "plaintext_length": len(ss),
            "padding_mode": None,
            "ciphertext_length": len(ct),
            "key_hex": kem.public_key().public_bytes_raw().hex(),
            "iv_hex": None,
        })
        if idx % 100 == 0:
            print(f"  {name}: generated {idx}/{n_target}")
    return n_target


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    print(f"Generating MEGA corpus: {N_PER_FAMILY} per family = {N_PER_FAMILY * 7} total")
    print(f"Output directory: {OUTDIR}")
    print("=" * 60)

    total = 0
    total += generate_block_family(
        "AES-128", CIPHERS["AES-128"],
        {"openssl": aes_encrypt_openssl, "pycryptodome": aes_encrypt_pycrypto}, N_PER_FAMILY)
    total += generate_block_family(
        "AES-256", CIPHERS["AES-256"],
        {"openssl": aes_encrypt_openssl, "pycryptodome": aes_encrypt_pycrypto}, N_PER_FAMILY)
    total += generate_block_family(
        "3DES", CIPHERS["3DES"],
        {"openssl": des3_encrypt_openssl, "pycryptodome": des3_encrypt_pycrypto}, N_PER_FAMILY)
    total += generate_block_family(
        "DES", CIPHERS["DES"],
        {"openssl": des_encrypt_pycrypto, "pycryptodome": des_encrypt_pycrypto}, N_PER_FAMILY)
    total += generate_chacha(N_PER_FAMILY)
    total += generate_rsa(N_PER_FAMILY)
    total += generate_mlkem(N_PER_FAMILY)

    manifest = {
        "version": "3.0-mega",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_samples": total,
        "n_per_family": N_PER_FAMILY,
        "samples": samples,
    }
    manifest_path = os.path.join(OUTDIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 60)
    print(f"DONE. Generated {total} samples in {OUTDIR}")
    print(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
