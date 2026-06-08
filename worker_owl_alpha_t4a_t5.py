#!/usr/bin/env python3
"""
Parallel Worker B: openrouter/owl-alpha — T4A + T5, all 140 files each.
OpenRouter free tier. Checkpoint/resume per-shard.
"""
import json, os, sys, re, time, math, argparse
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage2_execution/results/live_sample_140_v2"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
RESULTS_DIR = WORKSPACE / "stage2_execution/results"
SHARD_PATH = RESULTS_DIR / "owl_alpha_t4a_t5_v2_final.jsonl"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_openrouter_key():
    env_path = Path("/home/elaref/.hermes/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2 and parts[0] == "OPENROUTER_API_KEY":
                        key = parts[1]
                        if key: return key
    return os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_KEY = _load_openrouter_key()

MODEL = "openrouter/owl-alpha"
BACKEND_NAME = "openrouter/owl-alpha"
TIERS = ["tier4a", "tier5"]
DELAY = 3.0
TIMEOUT = 180

CIPHER_ALIASES = {
    "aes-128": "AES-128", "aes128": "AES-128",
    "aes-256": "AES-256", "aes256": "AES-256",
    "3des": "3DES", "tripledes": "3DES", "3-des": "3DES",
    "triple-des": "3DES", "triple des": "3DES",
    "des": "DES",
    "chacha20": "ChaCha20", "chacha": "ChaCha20",
    "rsa-2048": "RSA-2048", "rsa2048": "RSA-2048", "rsa": "RSA-2048",
    "ml-kem-768": "ML-KEM-768", "mlkem768": "ML-KEM-768",
    "ml-kem": "ML-KEM-768", "ml": "ML-KEM-768",
    "aes": "AES-128",
}

def normalize_prediction(raw):
    if not raw: return "UNKNOWN"
    text = raw.strip()
    answer_lines = []
    for line in text.split("\n"):
        line_s = line.strip()
        if any(marker in line_s.upper() for marker in [
            "FINAL_ANSWER", "FINAL DETERMINATION", "PREDICTED_CIPHER",
            "FINAL_PREDICTION", "CLASSIFICATION", "CIPHER FAMILY", "CIPHER:",
            "STEP 5", "CONCLUSIONS:", "ANSWER:"
        ]):
            if ":" in line_s:
                answer_lines.append(line_s.split(":", 1)[1].strip())
            else:
                answer_lines.append(line_s)
    search_targets = answer_lines + list(reversed(text.strip().split("\n")[-20:]))
    search_targets.append(text)
    for target in search_targets:
        t = target.lower().strip(" `*_-'")
        for alias, canonical in CIPHER_ALIASES.items():
            if alias in t:
                return canonical
    return "UNKNOWN"

def compute_entropy(d):
    if not d: return 0.0
    n = len(d); counts = Counter(d)
    return -sum((c/n)*math.log2(c/n) for c in counts.values())

def compute_chi2(d):
    if not d: return 0.0
    n = len(d); expected = n/256.0; counts = Counter(d)
    return sum(((counts.get(b,0)-expected)**2/expected) for b in range(256))

def hex_preview(d, n=32): return d[:n].hex()

def top_bytes(d, k=5):
    counts = Counter(d)
    return ", ".join(f"0x{b:02x}({c})" for b,c in counts.most_common(k))

def block_alignment(d):
    n = len(d)
    results = []
    for bs in [8, 16, 32, 64]:
        if n % bs == 0: results.append(f"divisible by {bs}")
        else: results.append(f"NOT divisible by {bs} (remainder {n%bs})")
    return "; ".join(results)

def build_tier4a_prompt(file_size, entropy, chi2_val, top_bytes_str, hex_str, block_info):
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2_val:.1f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 64 bytes): {hex_str}\n"
        f"- Block alignment: {block_info}\n\n"
        f"## POSSIBLE CIPHER FAMILIES\n"
        f"AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"## TASK\n"
        f"Based on the computed features above, determine which cipher family produced this ciphertext.\n"
        f"Use the features as your 'tools' — entropy, chi2, byte frequencies, block alignment.\n\n"
        f"Respond with ONLY the cipher family name."
    )

def build_tier5_prompt(file_size, entropy, chi2_val, top_bytes_str, hex_str, block_info):
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2_val:.1f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 64 bytes): {hex_str}\n"
        f"- Block alignment: {block_info}\n\n"
        f"## POSSIBLE CIPHER FAMILIES\n"
        f"AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"## OUTPUT FORMAT\n"
        f"You MUST respond in this exact structure:\n\n"
        f"STEP 1 — ENTROPY ANALYSIS:\n"
        f"[Your analysis of the entropy value]\n\n"
        f"STEP 2 — STRUCTURAL ANALYSIS:\n"
        f"[File size, block alignment, padding detection]\n\n"
        f"STEP 3 — STATISTICAL TESTING:\n"
        f"[Chi-square and byte frequency analysis]\n\n"
        f"STEP 4 — ELIMINATION:\n"
        f"[Which ciphers did you eliminate and WHY]\n\n"
        f"STEP 5 — FINAL DETERMINATION:\n"
        f"[ONE cipher family name from the list above]\n\n"
        f"CONFIDENCE: [0-100%]\n\n"
        f"BEGIN YOUR FORENSIC ANALYSIS:"
    )

def call_openrouter(model, prompt, timeout=180):
    payload = json.dumps({
        "model": model, "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2, "max_tokens": 2048,
    }).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://gidaai.local",
        "X-Title": "ACTS_v2_Benchmark",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            choices = result.get("choices", [])
            usage = result.get("usage", {})
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            return {
                "raw_response": content,
                "eval_count": usage.get("completion_tokens", 0) or 0,
                "prompt_eval_count": usage.get("prompt_tokens", 0) or 0,
                "eval_duration": 0,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason} | {body[:200]}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def load_completed_set(jsonl_path):
    done = set()
    if not jsonl_path.exists(): return done
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
                key = (rec.get("backend",""), rec.get("tier",""), rec.get("filename",""), rec.get("variant") or "standard")
                done.add(key)
            except: pass
    return done

def append_result(jsonl_path, record):
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

def run():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]

    completed = load_completed_set(SHARD_PATH)
    print(f"[owl-alpha T4A+T5] Checkpoint: {len(completed)} results in {SHARD_PATH.name}")

    total_calls = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for tier in TIERS:
        for sample in samples:
            filename = sample["filename"]
            file_key = (BACKEND_NAME, tier, filename, "standard")
            if file_key in completed:
                skipped += 1
                continue

            filepath = CORPUS_DIR / filename
            if not filepath.exists():
                print(f"  ⚠️  File not found: {filename}")
                errors += 1
                continue

            data = filepath.read_bytes()
            file_size = len(data)
            entropy = compute_entropy(data)
            chi2 = compute_chi2(data)

            if tier == "tier4a":
                prompt = build_tier4a_prompt(file_size, entropy, chi2, top_bytes(data),
                    hex_preview(data, 64), block_alignment(data))
            elif tier == "tier5":
                prompt = build_tier5_prompt(file_size, entropy, chi2, top_bytes(data),
                    hex_preview(data, 64), block_alignment(data))
            else:
                continue

            max_retries = 5
            result = {"error": "not called", "raw_response": ""}
            latency = 0.0
            for attempt in range(max_retries):
                t_call = time.time()
                result = call_openrouter(MODEL, prompt, timeout=TIMEOUT)
                latency = time.time() - t_call
                if "error" in result and result["error"]:
                    err_msg = result["error"]
                    if "429" in err_msg:
                        wait = min((2 ** attempt) * 10 + 1, 120)
                        print(f"    ⏳ 429, retry in {wait}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(wait)
                        continue
                    elif attempt < max_retries - 1:
                        print(f"    ⏳ Error: {err_msg[:80]}, retrying...")
                        time.sleep(5)
                        continue
                break

            raw_response = result.get("raw_response", "")
            predicted = normalize_prediction(raw_response)
            correct = (predicted == sample["cipher_family"])

            record = {
                "backend": BACKEND_NAME,
                "model_id": MODEL,
                "tier": tier,
                "variant": None,
                "filename": filename,
                "ground_truth": sample["cipher_family"],
                "implementation": sample["implementation"],
                "file_size": file_size,
                "parsed_prediction": predicted,
                "correct": correct,
                "latency_s": round(latency, 3),
                "prompt_tokens": result.get("prompt_eval_count", 0) or 0,
                "completion_tokens": result.get("eval_count", 0) or 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": result.get("error", ""),
            }
            append_result(SHARD_PATH, record)
            completed.add(file_key)
            total_calls += 1

            status = "✅" if correct else "❌"
            err_str = f" ERROR:{record['error'][:60]}" if record.get("error") else ""
            print(f"  {status} {tier} {filename}: GT={sample['cipher_family']} PRED={predicted} ({latency:.1f}s){err_str}")

            time.sleep(DELAY)

    elapsed = time.time() - t_start
    print(f"\n[owl-alpha T4A+T5] COMPLETE: {total_calls} calls in {elapsed:.0f}s | skipped={skipped} errors={errors}")
    print(f"   Shard: {SHARD_PATH}")

if __name__ == "__main__":
    run()
