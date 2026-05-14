#!/usr/bin/env python3
"""
Live Inference Validation Experiment
=====================================
Purpose: Validate Tier-5 deterministic heuristic against live LLM API calls.
Run 100 random samples from corpus_ultra via GPT-OSS 120B (Ollama) 
and compare accuracy to deterministic heuristic.

Output: JSON with per-file predictions and summary diff.
"""
import json, os, random, time, requests, re
from pathlib import Path
from collections import Counter
import math

CORPUS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage1_data/corpus_ultra")
OUTPUT_FILE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/live_validation_100.json")
MODEL = "gpt-oss:120b-cloud"
OLLAMA_URL = "http://localhost:11434/api/generate"
SAMPLE_SIZE = 100

CIPHER_MAP = {
    "AES-128": "AES-128", "AES-256": "AES-256", "3DES": "3DES",
    "DES": "DES", "ChaCha20": "ChaCha20",
    "RSA-2048": "RSA-2048", "ML-KEM-768": "ML-KEM-768",
}

def parse_ground_truth(filename: str) -> str:
    """Extract cipher family from filename like AES-256_0301_pycryptodome.bin"""
    base = filename.split("_")[0]
    if base == "AES":
        # AES-128 or AES-256
        parts = filename.split("_")
        base = f"AES-{parts[1].split('-')[1]}" if len(parts) > 1 and "-" in parts[1] else "AES-128"
    return CIPHER_MAP.get(base, base)

def compute_entropy(data: bytes) -> float:
    if not data: return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def compute_chi2(data: bytes):
    if not data: return 0.0, 1.0
    n = len(data)
    expected = n / 256.0
    counts = Counter(data)
    chi2 = sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))
    return chi2, 0.5 if chi2 < 255 else 0.01

def build_prompt(filepath: Path) -> str:
    data = filepath.read_bytes()
    chi2, chi2_p = compute_chi2(data)
    counts = Counter(data)
    top = counts.most_common(5)
    top_str = ", ".join(f"0x{b:02x}({c})" for b, c in top)

    prompt = f"""# Tier-5A: Forced Chain-of-Thought with Evidence Citation

You are an expert forensic cryptographer. Identify the cipher family used to produce the attached ciphertext through rigorous, evidence-based analysis.

## CRITICAL INSTRUCTIONS
1. You MUST show your reasoning step-by-step.
2. You MUST cite specific evidence from the ciphertext.
3. You MUST explain WHY each alternative was eliminated.

## CIPHERTEXT FILE
- Filename: {filepath.name}
- File size: {len(data)} bytes
- Hex preview (first 64 bytes): {data[:64].hex()}
- Entropy (Shannon): {compute_entropy(data):.4f} bits/byte
- Chi-square: {chi2:.2f} (p≈{chi2_p:.2f})
- Top bytes: {top_str}

## AVAILABLE CIPHER FAMILIES
1. AES-128 (16-byte blocks)   2. AES-256 (16-byte blocks)
3. 3DES (8-byte blocks)       4. DES (8-byte blocks)
5. ChaCha20 (stream cipher)   6. RSA-2048 (256-byte output)
7. ML-KEM-768 (1088-byte fixed)

## OUTPUT FORMAT
Provide your step-by-step reasoning, then end with exactly:
FINAL_ANSWER: [cipher family name]
"""
    return prompt

def extract_answer(response_text: str) -> str:
    """Extract FINAL_ANSWER from LLM response."""
    lines = response_text.splitlines()
    for line in reversed(lines):
        if "FINAL_ANSWER:" in line:
            ans = line.split("FINAL_ANSWER:")[-1].strip().strip("`*")
            return ans
    # Fallback: search whole text for cipher names
    text_lower = response_text.lower()
    for cipher in ["aes-256", "aes-128", "aes", "3des", "tripledes", "des", "chacha20", "chacha", "rsa-2048", "rsa2048", "rsa", "ml-kem-768", "mlkem768", "ml-kem"]:
        if cipher in text_lower:
            if "aes-256" in text_lower: return "AES-256"
            if "aes-128" in text_lower: return "AES-128"
            if cipher in ("aes",): return "AES-128"
            if cipher in ("3des", "tripledes"): return "3DES"
            if cipher == "des": return "DES"
            if cipher in ("chacha20", "chacha"): return "ChaCha20"
            if cipher in ("rsa-2048", "rsa2048", "rsa"): return "RSA-2048"
            if cipher in ("ml-kem-768", "mlkem768", "ml-kem"): return "ML-KEM-768"
    return "UNKNOWN"

def normalize_answer(ans: str) -> str:
    ans = ans.strip().upper()
    if "AES" in ans and "256" in ans: return "AES-256"
    if "AES" in ans: return "AES-128"
    if "3DES" in ans or "TRIPLE" in ans: return "3DES"
    if "DES" in ans: return "DES"
    if "CHACHA" in ans: return "ChaCha20"
    if "RSA" in ans: return "RSA-2048"
    if "ML" in ans or "KEM" in ans: return "ML-KEM-768"
    return ans

def deterministic_heuristic(filepath: Path) -> str:
    """The deterministic size heuristic used in the paper."""
    size = filepath.stat().st_size
    if size == 1088: return "ML-KEM-768"
    if size == 256: return "RSA-2048"
    if size % 16 == 0:
        # Ambiguous: AES or DES could both be 16-aligned
        # Tie-break: bias toward AES (heuristic default)
        return "AES-128"
    if size % 8 == 0:
        return "DES"
    return "ChaCha20"

def call_ollama(prompt: str, model: str = MODEL, timeout: int = 120) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 800}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "response": ""}

def main():
    # Sample 100 random files
    all_files = sorted([f for f in CORPUS_DIR.iterdir() if f.suffix == ".bin"])
    random.seed(42)
    sample = random.sample(all_files, SAMPLE_SIZE)

    results = []
    correct_live = 0
    correct_heuristic = 0

    print(f"Running live validation on {SAMPLE_SIZE} samples via {MODEL}...")
    for i, filepath in enumerate(sample, 1):
        gt = parse_ground_truth(filepath.name)
        prompt = build_prompt(filepath)

        t0 = time.time()
        resp = call_ollama(prompt)
        latency = time.time() - t0

        if "error" in resp:
            print(f"  [{i}/{SAMPLE_SIZE}] ERROR: {resp['error']}")
            continue

        response_text = resp.get("response", "")
        live_ans = normalize_answer(extract_answer(response_text))
        heuristic_ans = deterministic_heuristic(filepath)

        live_correct = (live_ans == gt)
        heuristic_correct = (heuristic_ans == gt)
        if live_correct: correct_live += 1
        if heuristic_correct: correct_heuristic += 1

        results.append({
            "file": filepath.name,
            "ground_truth": gt,
            "live_answer": live_ans,
            "heuristic_answer": heuristic_ans,
            "live_correct": live_correct,
            "heuristic_correct": heuristic_correct,
            "latency_sec": round(latency, 2),
            "tokens_evaluated": resp.get("eval_count", 0),
        })

        print(f"  [{i}/{SAMPLE_SIZE}] {filepath.name}: GT={gt} LIVE={live_ans} HEUR={heuristic_ans} ({latency:.1f}s)")

    live_acc = correct_live / len(results) * 100 if results else 0
    heuristic_acc = correct_heuristic / len(results) * 100 if results else 0
    diff = live_acc - heuristic_acc

    summary = {
        "model": MODEL,
        "sample_size": len(results),
        "live_accuracy": round(live_acc, 2),
        "heuristic_accuracy": round(heuristic_acc, 2),
        "diff_pp": round(diff, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }

    OUTPUT_FILE.write_text(json.dumps(summary, indent=2))
    print(f"\n{'='*60}")
    print(f"LIVE accuracy:     {live_acc:.1f}% ({correct_live}/{len(results)})")
    print(f"HEURISTIC accuracy: {heuristic_acc:.1f}% ({correct_heuristic}/{len(results)})")
    print(f"DIFFERENCE:        {diff:+.2f} pp")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
