#!/usr/bin/env python3
"""
Tier-5 Live Validation — 50 random samples from ultra corpus
Run via GPT-OSS 120B (Ollama) WITHOUT filename metadata.
Compare to deterministic heuristic.
"""
import json, os, random, time, requests
from pathlib import Path
from collections import Counter
import math

CORPUS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage1_data/corpus_ultra")
OUTPUT_FILE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/live_validation_50.json")
MODEL = "gpt-oss:120b-cloud"
OLLAMA_URL = "http://localhost:11434/api/generate"
SAMPLE_SIZE = 50

CIPHER_MAP = {
    "AES-128": "AES-128", "AES-256": "AES-256", "3DES": "3DES",
    "DES": "DES", "ChaCha20": "ChaCha20",
    "RSA-2048": "RSA-2048", "ML-KEM-768": "ML-KEM-768",
}

def parse_ground_truth(filename: str) -> str:
    base = filename.split("_")[0]
    if base == "AES":
        parts = filename.split("_")
        base = f"AES-{parts[1].split('-')[1]}" if len(parts) > 1 and "-" in parts[1] else "AES-128"
    return CIPHER_MAP.get(base, base)

def compute_entropy(data: bytes) -> float:
    if not data: return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

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

def deterministic_heuristic(size: int) -> str:
    if size == 1088: return "ML-KEM-768"
    if size == 256: return "RSA-2048"
    if size % 16 == 0: return "AES-128"
    if size % 8 == 0: return "DES"
    return "ChaCha20"

def call_ollama(prompt: str, model: str = MODEL, timeout: int = 90) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 300}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "response": ""}

def build_prompt(data: bytes) -> str:
    ent = compute_entropy(data)
    hex_preview = data[:64].hex()
    prompt = f"""You are a forensic cryptographer analyzing raw ciphertext.

## CIPHERTEXT PROPERTIES
- File size: {len(data)} bytes
- Hex preview (first 64 bytes): {hex_preview}
- Entropy (Shannon): {ent:.4f} bits/byte

## AVAILABLE CIPHER FAMILIES
1. AES-128 (16-byte blocks)   2. AES-256 (16-byte blocks)
3. 3DES (8-byte blocks)       4. DES (8-byte blocks)
5. ChaCha20 (stream cipher)   6. RSA-2048 (256-byte output)
7. ML-KEM-768 (1088-byte fixed)

## INSTRUCTIONS
Think step by step. Consider file size, entropy, and block structure.
Then write EXACTLY one line:
FINAL_ANSWER: [cipher family name]
"""
    return prompt

def main():
    all_files = sorted([f for f in CORPUS_DIR.iterdir() if f.suffix == ".bin"])
    random.seed(42)
    sample = random.sample(all_files, SAMPLE_SIZE)

    results = []
    correct_live = 0
    correct_heuristic = 0

    print(f"[START] Running {SAMPLE_SIZE} live inferences via {MODEL}")
    for i, filepath in enumerate(sample, 1):
        gt = parse_ground_truth(filepath.name)
        data = filepath.read_bytes()
        size = len(data)

        prompt = build_prompt(data)
        t0 = time.time()
        resp = call_ollama(prompt)
        latency = time.time() - t0

        if "error" in resp:
            print(f"  [{i}/{SAMPLE_SIZE}] ERROR: {resp['error']}")
            continue

        response_text = resp.get("response", "")
        # Extract last line after FINAL_ANSWER:
        live_ans = "UNKNOWN"
        for line in reversed(response_text.splitlines()):
            if "FINAL_ANSWER:" in line:
                live_ans = line.split("FINAL_ANSWER:")[-1].strip().strip("`*")
                break

        live_ans = normalize_answer(live_ans)
        heuristic_ans = deterministic_heuristic(size)

        live_correct = (live_ans == gt)
        heuristic_correct = (heuristic_ans == gt)
        if live_correct: correct_live += 1
        if heuristic_correct: correct_heuristic += 1

        results.append({
            "file": filepath.name,
            "ground_truth": gt,
            "size": size,
            "live_answer": live_ans,
            "heuristic_answer": heuristic_ans,
            "live_correct": live_correct,
            "heuristic_correct": heuristic_correct,
            "latency_sec": round(latency, 1),
        })

        print(f"  [{i}/{SAMPLE_SIZE}] GT={gt} LIVE={live_ans} HEUR={heuristic_ans} ({latency:.1f}s)")

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
    print(f"LIVE accuracy:      {live_acc:.1f}% ({correct_live}/{len(results)})")
    print(f"HEURISTIC accuracy: {heuristic_acc:.1f}% ({correct_heuristic}/{len(results)})")
    print(f"DIFFERENCE:         {diff:+.2f} pp")
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
