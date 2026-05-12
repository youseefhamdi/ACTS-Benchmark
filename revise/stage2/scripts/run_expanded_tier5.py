#!/usr/bin/env python3
"""Tier-5 + Tier-6 Expanded Corpus Analysis"""
import json, math
from pathlib import Path
from collections import Counter

manifest = json.load(open('stage1_data/corpus_expanded/manifest.json'))
corpus_dir = Path('stage1_data/corpus_expanded')

def classify_expanded(data: bytes, variant: str) -> str:
    size = len(data)
    if size == 256:
        return "rsa2048"
    if size == 1088:
        return "mlkem768"
    if size == 264:
        return "3des" if variant != "des_bias" else "des"
    if size == 4104:
        return "des" if variant != "3des_bias" else "3des"
    if size == 4128:
        return "aes256"
    mod8 = (size % 8 == 0)
    mod16 = (size % 16 == 0)
    if mod8 and not mod16:
        if variant == "3des_bias": return "3des"
        elif variant == "des_bias": return "des"
        else: return "3des"
    if mod16:
        if variant == "aes256_bias": return "aes256"
        elif variant == "chacha20_bias": return "chacha20"
        elif variant == "des_bias": return "des"
        else: return "aes128"
    if variant == "chacha20_bias": return "chacha20"
    return "aes128"

family_map = {"AES-128": "aes128", "AES-256": "aes256", "3DES": "3des", "DES": "des", "ChaCha20": "chacha20", "RSA-2048": "rsa2048", "ML-KEM-768": "mlkem768"}

variants = {
    "default (AES-128 bias)": "default",
    "AES-256 bias": "aes256_bias",
    "ChaCha20 bias": "chacha20_bias",
    "3DES bias": "3des_bias",
    "DES bias": "des_bias",
}

print("=" * 60)
print("TIER-5 SENSITIVITY — EXPANDED CORPUS (700 files)")
print("=" * 60)

results = {}
for vname, vcode in variants.items():
    correct = 0
    total = 0
    per_class = {}
    for s in manifest:
        filepath = corpus_dir / s["filename"] / "ciphertext.bin"
        if not filepath.exists():
            filepath = corpus_dir / s["filename"]
        data = filepath.read_bytes()
        pred = classify_expanded(data, vcode)
        true = family_map[s["cipher_family"]]
        ok = pred == true
        correct += ok
        total += 1
        per_class.setdefault(true, {"correct": 0, "total": 0})
        per_class[true]["total"] += 1
        if ok: per_class[true]["correct"] += 1
    
    acc = correct / total
    results[vname] = {"overall": acc, "per_class": per_class}
    print(f"\n{vname}: {acc:.1%} ({correct}/{total})")
    for fam in ["rsa2048", "mlkem768", "aes128", "aes256", "3des", "des", "chacha20"]:
        if fam in per_class:
            c = per_class[fam]["correct"]
            t = per_class[fam]["total"]
            print(f"  {fam}: {c}/{t} = {c/t:.0%}")

unique_sizes = set()
for s in manifest:
    filepath = corpus_dir / s["filename"] / "ciphertext.bin"
    if not filepath.exists():
        filepath = corpus_dir / s["filename"]
    unique_sizes.add(len(filepath.read_bytes()))

print(f"\n{'='*60}")
print(f"Unique sizes: {len(unique_sizes)} || Theoretical size-only max: {len(unique_sizes)/700:.1%}")
print(f"{'='*60}")

# Save results
json.dump(results, open('stage2_execution/results/tier5_expanded_results.json', 'w'), indent=2)
print("\nSaved: stage2_execution/results/tier5_expanded_results.json")
