#!/usr/bin/env python3
"""
Tier-4A and Tier-5 Live Evaluation Runner
==========================================
Tier-4A: Tool-augmented blind — model gets computed features (entropy, chi2,
          byte freq, block alignment, hex prefix) but NO metadata.
Tier-5:  Forced CoT reasoning — blind + step-by-step cryptanalytic reasoning.

Both use the same 5 backends, same 140-file manifest, same checkpoint/resume
and 429-backoff logic as the main runner.

Usage:
    python3 run_tier4a_t5.py --tier4a    # Run Tier-4A only
    python3 run_tier4a_t5.py --tier5     # Run Tier-5 only
    python3 run_tier4a_t5.py --both      # Run both
"""

import json, os, sys, hashlib, time, re, argparse
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import urllib.request, urllib.error

# ── Paths ──────────────────────────────────────────────────────────────────────

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage1_data/corpus_ultra"
MANIFEST_PATH = WORKSPACE / "stage2_execution/results/live_sample_140/manifest.json"
RESULTS_DIR = WORKSPACE / "stage2_execution/results"

# ── API configs ────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
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
                        if key:
                            return key
    return os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_KEY = _load_openrouter_key()

BACKENDS = {
    "gemma4:31b-cloud":           {"type": "ollama",      "model_id": "gemma4:31b-cloud"},
    "gpt-oss:120b-cloud":         {"type": "ollama",      "model_id": "gpt-oss:120b-cloud"},
    "nemotron-3-super:cloud":     {"type": "ollama",      "model_id": "nemotron-3-super:cloud"},
    "openrouter/owl-alpha":       {"type": "openrouter",  "model_id": "openrouter/owl-alpha"},
    "google/gemma-4-31b-it:free": {"type": "openrouter",  "model_id": "google/gemma-4-31b-it:free"},
}

# ── Stats helpers ──────────────────────────────────────────────────────────────

def compute_entropy(data: bytes) -> float:
    import math
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def compute_chi2(data: bytes) -> float:
    import math
    if not data:
        return 0.0
    n = len(data)
    expected = n / 256.0
    counts = Counter(data)
    return sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))

def top_bytes(data: bytes, k: int = 5) -> str:
    counts = Counter(data)
    top = counts.most_common(k)
    return ", ".join(f"0x{b:02x}({c})" for b, c in top)

def hex_preview(data: bytes, n: int = 128) -> str:
    return data[:n].hex()

def block_alignment_check(data: bytes) -> str:
    """Check if file size is divisible by common block sizes."""
    n = len(data)
    results = []
    for bs in [8, 16, 32, 64]:
        if n % bs == 0:
            results.append(f"divisible by {bs}")
        else:
            results.append(f"NOT divisible by {bs} (remainder {n % bs})")
    return "; ".join(results)

# ── Cipher normalization ──────────────────────────────────────────────────────

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

def normalize_prediction(raw: str) -> str:
    if not raw:
        return "UNKNOWN"
    text = raw.strip()
    # Try to extract the answer line first
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
        t = target.lower().strip(" `*-_\"")
        for alias, canonical in CIPHER_ALIASES.items():
            if alias in t:
                return canonical
    return "UNKNOWN"

# ── Prompts ────────────────────────────────────────────────────────────────────

def build_tier4a_prompt(file_size: int, entropy: float, chi2: float,
                         top_bytes_str: str, hex_str: str, block_info: str) -> str:
    """Tier-4A: Tool-augmented blind. Model gets computed features but NO metadata."""
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2:.2f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 128 bytes): {hex_str}\n"
        f"- Block alignment check: {block_info}\n\n"
        f"## AVAILABLE TOOLS (already computed above)\n"
        f"You have the entropy, chi-square, byte frequency, hex preview, and block-alignment\n"
        f"results above. Use them to reason about the cipher family.\n\n"
        f"## AVAILABLE CIPHER FAMILIES\n"
        f"1. AES-128 (16-byte blocks, PKCS7/ISO10126/Zero padding)\n"
        f"2. AES-256 (16-byte blocks, PKCS7/ISO10126/Zero padding)\n"
        f"3. 3DES (8-byte blocks, PKCS7/Zero padding)\n"
        f"4. DES (8-byte blocks, PKCS7/Zero padding)\n"
        f"5. ChaCha20 (stream cipher, no padding, ciphertext = plaintext size)\n"
        f"6. RSA-2048 (fixed 256-byte output for encryption)\n"
        f"7. ML-KEM-768 (post-quantum, fixed 1088-byte encapsulation)\n\n"
        f"## INSTRUCTIONS\n"
        f"Analyze the provided cryptographic features step by step.\n"
        f"Use the computed statistics to identify the cipher family.\n"
        f"Consider file size, entropy, block alignment, and byte distribution patterns.\n\n"
        f"Write EXACTLY one line:\n"
        f"FINAL_ANSWER: [cipher family name from the list above]"
    )

def build_tier5_prompt(file_size: int, entropy: float, chi2_pval: float,
                        top_bytes_str: str, hex_str: str, block_info: str) -> str:
    """Tier-5: Forced CoT reasoning — blind + step-by-step cryptanalytic analysis."""
    return (
        f"You are an expert forensic cryptographer participating in a controlled benchmark.\n"
        f"Your task is to identify the cipher family used to produce a ciphertext file\n"
        f"through rigorous, evidence-based analysis.\n\n"
        f"## CRITICAL INSTRUCTIONS\n"
        f"1. You MUST show your reasoning step-by-step. A single-word answer will be rejected.\n"
        f"2. You MUST cite specific evidence from the computed features.\n"
        f"3. You MUST explain WHY each alternative cipher family was eliminated.\n\n"
        f"## CIPHERTEXT FEATURES (no metadata available)\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2_pval:.2f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 128 bytes): {hex_str}\n"
        f"- Block alignment check: {block_info}\n\n"
        f"## AVAILABLE CIPHER FAMILIES\n"
        f"1. AES-128 (16-byte blocks, PKCS7/ISO10126/Zero padding)\n"
        f"2. AES-256 (16-byte blocks, PKCS7/ISO10126/Zero padding)\n"
        f"3. 3DES (8-byte blocks, PKCS7/Zero padding)\n"
        f"4. DES (8-byte blocks, PKCS7/Zero padding)\n"
        f"5. ChaCha20 (stream cipher, no padding, ciphertext = plaintext size)\n"
        f"6. RSA-2048 (fixed 256-byte output for encryption)\n"
        f"7. ML-KEM-768 (post-quantum, fixed 1088-byte encapsulation)\n\n"
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

# ── LLM callers ───────────────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, timeout: int = 180) -> dict:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            dur = result.get("eval_duration", 0)
            return {
                "raw_response": result.get("response", ""),
                "eval_count": result.get("eval_count", 0) or 0,
                "prompt_eval_count": result.get("prompt_eval_count", 0) or 0,
                "eval_duration": dur,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason} | {body[:200]}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def call_openrouter(model: str, prompt: str, timeout: int = 180) -> dict:
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

def call_llm(backend_name: str, prompt: str, timeout: int = 180) -> dict:
    cfg = BACKENDS[backend_name]
    if cfg["type"] == "openrouter":
        return call_openrouter(cfg["model_id"], prompt, timeout=180)
    else:
        return call_ollama(cfg["model_id"], prompt, timeout=timeout)

# ── Checkpoint/resume ─────────────────────────────────────────────────────────

def load_completed_set(jsonl_path: Path) -> set:
    done = set()
    if not jsonl_path.exists():
        return done
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                key = (
                    rec.get("backend", ""),
                    rec.get("tier", ""),
                    rec.get("filename", ""),
                    rec.get("variant") or "standard",
                )
                done.add(key)
            except Exception:
                pass
    return done

def append_result(jsonl_path: Path, record: dict):
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

# ── Main runner ───────────────────────────────────────────────────────────────

def run_tier(tier_name: str, jsonl_path: Path, prompt_builder, backends=None,
             timeout=180, delay=0.5):
    """Run a single tier across all backends with checkpoint/resume."""

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]

    if backends is None:
        backend_names = list(BACKENDS.keys())
    else:
        backend_names = backends

    completed = load_completed_set(jsonl_path)
    total_calls = 0
    t_start = time.time()

    print(f"\n🚀 {tier_name}: {len(samples)} files × {len(backend_names)} backends = "
          f"{len(samples) * len(backend_names)} calls")
    print(f"📋 Checkpoint: {len(completed)} results already in {jsonl_path.name}")

    for backend_name in backend_names:
        for sample in samples:
            filename = sample["filename"]
            file_key = (backend_name, tier_name, filename, "standard")

            if file_key in completed:
                continue

            filepath = CORPUS_DIR / filename
            if not filepath.exists():
                continue

            data = filepath.read_bytes()
            file_size = len(data)
            entropy = compute_entropy(data)
            chi2_val = compute_chi2(data)
            tb = top_bytes_str = top_bytes(data, 5)
            hp = hex_preview(data, 128)
            ba = block_alignment_check(data)

            prompt = prompt_builder(file_size, entropy, chi2_val, tb, hp, ba)

            # Retry with backoff
            max_retries = 3
            result = {"error": "Not called", "raw_response": ""}
            latency = 0.0
            for attempt in range(max_retries):
                t_call = time.time()
                result = call_llm(backend_name, prompt, timeout=timeout)
                latency = time.time() - t_call

                if "error" in result and result["error"]:
                    err_msg = result["error"]
                    if "429" in err_msg:
                        wait = (2 ** attempt) * 5 + 1
                        print(f"    ⏳ 429, retry in {wait}s")
                        time.sleep(wait)
                        continue
                    elif attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                break

            raw_response = result.get("raw_response", "")
            predicted = normalize_prediction(raw_response)
            correct = (predicted == sample["cipher_family"])

            eval_dur = result.get("eval_duration", 0) or 0
            if isinstance(eval_dur, (int, float)) and eval_dur > 1e9:
                latency_api = eval_dur / 1e9
            else:
                latency_api = latency

            record = {
                "backend": backend_name,
                "model_id": BACKENDS[backend_name]["model_id"],
                "tier": tier_name,
                "filename": filename,
                "ground_truth": sample["cipher_family"],
                "implementation": sample.get("implementation", "unknown"),
                "file_size": file_size,
                "prompt_sent": prompt,
                "raw_response": raw_response,
                "parsed_prediction": predicted,
                "correct": correct,
                "latency_s": round(latency, 3),
                "prompt_tokens": result.get("prompt_eval_count", 0) or 0,
                "completion_tokens": result.get("eval_count", 0) or 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": result.get("error", ""),
            }

            append_result(jsonl_path, record)
            completed.add(file_key)
            total_calls += 1

            status = "✅" if correct else "❌"
            err_str = f" ERR:{result['error'][:60]}" if result.get("error") else ""
            print(f"  {status} [{backend_name}] {tier_name} {filename}: "
                  f"GT={sample['cipher_family']} PRED={predicted} ({latency:.1f}s){err_str}")

            time.sleep(delay)

    elapsed = time.time() - t_start
    print(f"\n✅ {tier_name} COMPLETE: {total_calls} calls in {elapsed:.0f}s")
    return total_calls


def main():
    parser = argparse.ArgumentParser(description="Tier-4A and Tier-5 Live Evaluation")
    parser.add_argument("--tier4a", action="store_true", help="Run Tier-4A")
    parser.add_argument("--tier5", action="store_true", help="Run Tier-5")
    parser.add_argument("--both", action="store_true", help="Run both Tier-4A and Tier-5")
    parser.add_argument("--backends", nargs="+", default=None)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if args.both:
        args.tier4a = True
        args.tier5 = True

    if not args.tier4a and not args.tier5:
        print("ERROR: specify --tier4a, --tier5, or --both")
        sys.exit(1)

    jsonl_4a = RESULTS_DIR / "tier4a_full.jsonl"
    jsonl_5 = RESULTS_DIR / "tier5_live_full.jsonl"

    if args.tier4a:
        run_tier("tier4a", jsonl_4a, build_tier4a_prompt,
                 backends=args.backends, timeout=args.timeout, delay=args.delay)

    if args.tier5:
        run_tier("tier5", jsonl_5, build_tier5_prompt,
                 backends=args.backends, timeout=args.timeout, delay=args.delay)

    print(f"\n📁 Tier-4A: {jsonl_4a}")
    print(f"📁 Tier-5:  {jsonl_5}")


if __name__ == "__main__":
    main()
