#!/usr/bin/env python3
"""
Targeted backfill: run only missing (backend, tier, filename) cells.
Reads the existing JSONL to determine what's missing, then runs only those cells.
Supports per-backend delay to handle rate limits.
"""

import json, os, sys, hashlib, time, re, argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage2_execution/results/live_sample_140_v2"
MANIFEST_PATH = WORKSPACE / "stage2_execution/results/live_sample_140_v2/manifest.json"
JSONL_PATH = WORKSPACE / "stage2_execution/results/live_matrix_full_v2.jsonl"

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
    "nemotron-3-super:cloud":     {"type": "ollama",      "model_id": "nemotron-3-super:cloud"},
    "openrouter/owl-alpha":       {"type": "openrouter",  "model_id": "openrouter/owl-alpha"},
    "google/gemma-4-31b-it:free": {"type": "openrouter",  "model_id": "google/gemma-4-31b-it:free"},
}

# Per-backend delays (seconds) — nemotron needs much longer to avoid 429s
BACKEND_DELAYS = {
    "nemotron-3-super:cloud":     30.0,
    "openrouter/owl-alpha":       5.0,
    "google/gemma-4-31b-it:free": 5.0,
}

def compute_entropy(data):
    if not data: return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * __import__('math').log2(c / n) for c in counts.values()) if n > 0 else 0.0

def compute_chi2(data):
    if not data: return 0.0
    counts = Counter(data)
    n = len(data)
    expected = n / 256.0
    return sum(((counts.get(i, 0) - expected) ** 2) / expected for i in range(256))

def hex_prefix(data, n):
    return data[:n].hex()

def normalize_prediction(raw):
    raw = raw.strip().upper()
    # Extract cipher name from response
    for name in ["AES-256", "AES-128", "3DES", "DES", "CHACHA20", "RSA-2048", "ML-KEM-768"]:
        if name.upper() in raw:
            return name
    # Check for UNK/UNKNOWN
    if "UNK" in raw or "UNKNOWN" in raw:
        return "UNKNOWN"
    # Try to find any cipher name
    for name in ["AES", "DES", "CHACHA", "RSA", "ML-KEM"]:
        if name in raw:
            if "256" in raw and "AES" in raw:
                return "AES-256"
            if "128" in raw and "AES" in raw:
                return "AES-128"
            if "3DES" in raw or "TRIPLE" in raw:
                return "3DES"
            if "DES" in raw:
                return "DES"
            if "CHACHA" in raw:
                return "ChaCha20"
            if "RSA" in raw:
                return "RSA-2048"
            if "ML" in raw or "KEM" in raw:
                return "ML-KEM-768"
    return "UNKNOWN"

def build_tier1_prompt(filename, file_size, cipher_family, implementation, padding_mode, key_size_bits, mode):
    return (
        f"You are a cryptographic analysis expert.\n\n"
        f"Given the following KNOWN metadata:\n"
        f"- Cipher family: {cipher_family}\n"
        f"- Mode: {mode}\n"
        f"- Implementation: {implementation}\n\n"
        f"Confirm the cipher family name from this list: "
        f"AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Your answer (cipher name only):"
    )

def build_tier2_prompt(filename, file_size):
    return (
        f"You are a cryptographic forensics expert.\n\n"
        f"A ciphertext file is named: \"{filename}\"\n"
        f"File size: {file_size} bytes\n\n"
        f"Based on the filename and typical naming conventions, what cipher family\n"
        f"was likely used?\n\n"
        f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Your answer (cipher name only):"
    )

def build_tier3_prompt(file_size, entropy, chi2, hex_p, variant="stats_only"):
    base = (
        f"You are a cryptographic forensics expert.\n\n"
        f"Analyze the following ciphertext sample and identify the cipher family.\n\n"
        f"Ciphertext Statistics:\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2:.2f}\n"
        f"- Hex prefix (first 32 bytes): {hex_p}\n"
    )
    if variant == "tier3_raw":
        base += f"\nAdditional raw hex preview (first 256 bytes):\n[RAW_HEX_WILL_BE_INSERTED]\n"
    base += (
        f"\nCipher family options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Rules:\n"
        f"1. Provide ONLY the cipher name from the list above\n"
        f"2. No explanation needed\n"
        f"3. If uncertain, provide your best guess\n\n"
        f"Your answer (cipher name only):"
    )
    return base

def call_llm(backend_name, prompt, timeout=180):
    cfg = BACKENDS[backend_name]
    if cfg["type"] == "ollama":
        return call_ollama(cfg["model_id"], prompt, timeout)
    else:
        return call_openrouter(cfg["model_id"], prompt, timeout)

def call_ollama(model_id, prompt, timeout):
    payload = json.dumps({"model": model_id, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "num_predict": 300}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return {"raw_response": data.get("response", ""), "prompt_eval_count": data.get("prompt_eval_count", 0), "eval_count": data.get("eval_count", 0), "eval_duration": data.get("eval_duration", 0), "error": ""}
    except Exception as e:
        return {"raw_response": "", "error": str(e)}

def call_openrouter(model_id, prompt, timeout):
    payload = json.dumps({"model": model_id, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0.0}).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENROUTER_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            return {"raw_response": content, "prompt_tokens": usage.get("prompt_tokens", 0), "completion_tokens": usage.get("completion_tokens", 0), "error": ""}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"raw_response": "", "error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"raw_response": "", "error": str(e)}

def load_completed_set(jsonl_path):
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
                # Only count non-error records as "completed"
                if not rec.get("error"):
                    v = rec.get("variant") or "standard"
                    key = (rec.get("backend", ""), rec.get("tier", ""), rec.get("filename", ""), v)
                    done.add(key)
            except Exception:
                pass
    return done

def append_result(jsonl_path, record):
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

def main():
    parser = argparse.ArgumentParser(description="Targeted backfill for missing cells")
    parser.add_argument("--backends", nargs="+", required=True, help="Backends to run")
    parser.add_argument("--tiers", nargs="+", default=["tier3"], help="Tiers to run")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]

    completed = load_completed_set(JSONL_PATH)
    print(f"📋 Checkpoint: {len(completed)} completed cells in {JSONL_PATH.name}")

    total_calls = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for backend_name in args.backends:
        delay = BACKEND_DELAYS.get(backend_name, 5.0)
        print(f"\n🔧 Backend: {backend_name} (delay={delay}s)")

        for tier in args.tiers:
            print(f"  📊 Tier: {tier}")
            tier3_variant = None

            for sample in samples:
                filename = sample["filename"]
                variant = None
                file_key = (backend_name, tier, filename, "standard")

                if file_key in completed:
                    skipped += 1
                    continue

                filepath = CORPUS_DIR / filename
                if not filepath.exists():
                    print(f"    ⚠️ File not found: {filename}")
                    errors += 1
                    continue

                data = filepath.read_bytes()
                file_size = len(data)
                entropy = compute_entropy(data)
                chi2 = compute_chi2(data)
                hex_p = hex_prefix(data, 32)

                # Build prompt
                if tier == "tier1":
                    prompt = build_tier1_prompt(filename, file_size, sample["cipher_family"], sample["implementation"], sample.get("padding_mode", "unknown"), sample.get("key_size_bits", 0), sample.get("mode", "unknown"))
                elif tier == "tier2":
                    prompt = build_tier2_prompt(filename, file_size)
                elif tier == "tier3":
                    prompt = build_tier3_prompt(file_size, entropy, chi2, hex_p, "stats_only")
                    tier3_variant = "tier3_raw"
                else:
                    continue

                # Call LLM with retry
                max_retries = 5 if backend_name == "nemotron-3-super:cloud" else 3
                result = {"error": "Not called yet", "raw_response": ""}
                latency = 0.0

                for attempt in range(max_retries):
                    t_call = time.time()
                    result = call_llm(backend_name, prompt, timeout=args.timeout)
                    latency = time.time() - t_call

                    if "error" in result and result["error"]:
                        err_msg = result["error"]
                        if "429" in err_msg:
                            wait = (2 ** attempt) * 10 + 5  # 15s, 25s, 45s, 85s, 165s
                            print(f"    ⏳ 429, retry in {wait}s (attempt {attempt+1}/{max_retries})")
                            time.sleep(wait)
                            continue
                        elif attempt < max_retries - 1:
                            print(f"    ⏳ Error: {err_msg[:60]}, retrying...")
                            time.sleep(5)
                            continue
                    break

                raw_response = result.get("raw_response", "")
                predicted = normalize_prediction(raw_response)
                correct = (predicted == sample["cipher_family"])

                record = {
                    "backend": backend_name, "model_id": BACKENDS[backend_name]["model_id"],
                    "tier": tier, "variant": variant, "filename": filename,
                    "ground_truth": sample["cipher_family"], "implementation": sample["implementation"],
                    "file_size": file_size, "prompt_sent": prompt, "raw_response": raw_response,
                    "parsed_prediction": predicted, "correct": correct,
                    "latency_s": round(latency, 3), "latency_api_s": round(latency, 3),
                    "prompt_tokens": result.get("prompt_tokens", result.get("prompt_eval_count", 0)),
                    "completion_tokens": result.get("completion_tokens", result.get("eval_count", 0)),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": result.get("error", ""),
                }
                append_result(JSONL_PATH, record)
                completed.add(file_key)
                total_calls += 1

                status = "✅" if correct else "❌"
                err_str = f" ERROR:{record['error'][:50]}" if record.get("error") else ""
                print(f"    {status} {tier} {filename}: GT={sample['cipher_family']} PRED={predicted} ({latency:.1f}s){err_str}")

                # Tier3 raw variant
                if tier == "tier3" and tier3_variant == "tier3_raw":
                    raw_key = (backend_name, tier, filename, "tier3_raw")
                    if raw_key in completed:
                        skipped += 1
                    else:
                        raw_hex = data[:256].hex()
                        raw_prompt = build_tier3_prompt(file_size, entropy, chi2, hex_p, "tier3_raw").replace("[RAW_HEX_WILL_BE_INSERTED]", raw_hex)

                        raw_result = {"error": "Not called yet", "raw_response": ""}
                        raw_latency = 0.0

                        for attempt in range(max_retries):
                            t_call = time.time()
                            raw_result = call_llm(backend_name, raw_prompt, timeout=args.timeout)
                            raw_latency = time.time() - t_call

                            if "error" in raw_result and raw_result["error"]:
                                if "429" in raw_result["error"]:
                                    wait = (2 ** attempt) * 10 + 5
                                    print(f"    ⏳ tier3_raw 429, retry in {wait}s")
                                    time.sleep(wait)
                                    continue
                                elif attempt < max_retries - 1:
                                    time.sleep(5)
                                    continue
                            break

                        raw_response_t3r = raw_result.get("raw_response", "")
                        predicted_t3r = normalize_prediction(raw_response_t3r)

                        raw_record = {
                            "backend": backend_name, "model_id": BACKENDS[backend_name]["model_id"],
                            "tier": tier, "variant": "tier3_raw", "filename": filename,
                            "ground_truth": sample["cipher_family"], "implementation": sample["implementation"],
                            "file_size": file_size, "prompt_sent": raw_prompt, "raw_response": raw_response_t3r,
                            "parsed_prediction": predicted_t3r, "correct": (predicted_t3r == sample["cipher_family"]),
                            "latency_s": round(raw_latency, 3), "latency_api_s": round(raw_latency, 3),
                            "prompt_tokens": raw_result.get("prompt_tokens", raw_result.get("prompt_eval_count", 0)),
                            "completion_tokens": raw_result.get("completion_tokens", raw_result.get("eval_count", 0)),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "error": raw_result.get("error", ""),
                        }
                        append_result(JSONL_PATH, raw_record)
                        completed.add(raw_key)
                        total_calls += 1

                        status = "✅" if raw_record["correct"] else "❌"
                        err_str = f" ERROR:{raw_record['error'][:50]}" if raw_record.get("error") else ""
                        print(f"    {status} tier3_raw {filename}: GT={sample['cipher_family']} PRED={predicted_t3r} ({raw_latency:.1f}s){err_str}")

                time.sleep(delay)

    elapsed = time.time() - t_start
    print(f"\n{'='*70}")
    print(f"✅ BACKFILL COMPLETE: {total_calls} calls in {elapsed:.0f}s | skipped={skipped} errors={errors}")
    print(f"   Results saved to: {JSONL_PATH}")

if __name__ == "__main__":
    main()
