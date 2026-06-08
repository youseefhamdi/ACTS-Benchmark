#!/usr/bin/env python3
"""
Parallel Worker A: minimax-m3 — ALL 5 tiers (T1/T2/T3/T4A/T5), all 140 files.
Thinking model: strip <think>...</think>, extract final label only.
High num_predict for thinking. Checkpoint/resume per-shard.
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
SHARD_PATH = RESULTS_DIR / "minimax_m3_all_v2_final.jsonl"

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
                        if key: return key
    return os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_KEY = _load_openrouter_key()

MODEL = "minimax-m3:cloud"
BACKEND_NAME = "minimax-m3:cloud"

TIERS = ["tier1", "tier2", "tier3", "tier4a", "tier5"]
DELAY = 2.0  # seconds between calls
TIMEOUT = 300  # 5 min timeout for thinking model

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

def strip_thinking(text):
    if not text: return ""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    if '</think>' in text:
        after = text.split('</think>', 1)[-1].strip()
        if after: return after
    if '</thinking>' in text:
        after = text.split('</thinking>', 1)[-1].strip()
        if after: return after
    return text.strip()

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

def build_tier1_prompt(filename, file_size, cipher_family, implementation, padding_mode, key_size_bits, mode):
    return (
        f"You are a cryptographic analysis expert.\n\n"
        f"Given the following KNOWN metadata:\n"
        f"- Filename: {filename}\n"
        f"- File size: {file_size} bytes\n"
        f"- Cipher family: {cipher_family}\n"
        f"- Implementation: {implementation}\n"
        f"- Padding mode: {padding_mode}\n"
        f"- Key size: {key_size_bits} bits\n"
        f"- Mode: {mode}\n\n"
        f"What is the cipher family?\n\n"
        f"Respond with ONLY the cipher family name (e.g., AES-256, 3DES, ChaCha20, DES, RSA-2048, ML-KEM-768)."
    )

def build_tier2_prompt(filename, file_size):
    return (
        f"You are a cryptographic analysis expert.\n\n"
        f"FILENAME: {filename}\n"
        f"FILE SIZE: {file_size} bytes\n\n"
        f"The filename may contain hints about the cipher family.\n\n"
        f"What cipher family produced this ciphertext?\n\n"
        f"POSSIBLE CIPHER FAMILIES: AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Respond with ONLY the cipher family name."
    )

def build_tier3_prompt(file_size, entropy, chi2, hex_p, variant="stats_only"):
    return (
        f"You are a forensic cryptographer analyzing a ciphertext sample.\n\n"
        f"COMPUTED FEATURES:\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2:.1f}\n"
        f"- Hex prefix (first 32 bytes): {hex_p}\n\n"
        f"POSSIBLE CIPHER FAMILIES: AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"What cipher family produced this ciphertext?\n\n"
        f"STEP 1 — ENTROPY ANALYSIS: [analyze the entropy]\n"
        f"STEP 2 — STRUCTURAL ANALYSIS: [file size and block alignment]\n"
        f"STEP 3 — FINAL DETERMINATION: [single cipher family name]"
    )

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

def build_tier5_prompt(file_size, entropy, chi2_pval, top_bytes_str, hex_str, block_info):
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2_pval:.1f}\n"
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

def call_ollama(model, prompt, timeout=300):
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 4096},
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
    print(f"[minimax-m3] Checkpoint: {len(completed)} results in {SHARD_PATH.name}")

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
            hex_p = hex_preview(data, 32)

            if tier == "tier1":
                prompt = build_tier1_prompt(filename, file_size, sample["cipher_family"],
                    sample["implementation"], sample.get("padding_mode","unknown"),
                    sample.get("key_size_bits",0), sample.get("mode","unknown"))
            elif tier == "tier2":
                prompt = build_tier2_prompt(filename, file_size)
            elif tier == "tier3":
                prompt = build_tier3_prompt(file_size, entropy, chi2, hex_p)
            elif tier == "tier4a":
                prompt = build_tier4a_prompt(file_size, entropy, chi2, top_bytes(data),
                    hex_preview(data, 64), block_alignment(data))
            elif tier == "tier5":
                prompt = build_tier5_prompt(file_size, entropy, chi2, top_bytes(data),
                    hex_preview(data, 64), block_alignment(data))
            else:
                continue

            # Call with retry
            max_retries = 5
            result = {"error": "not called", "raw_response": ""}
            latency = 0.0
            for attempt in range(max_retries):
                t_call = time.time()
                result = call_ollama(MODEL, prompt, timeout=TIMEOUT)
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
            stripped = strip_thinking(raw_response)
            predicted = normalize_prediction(stripped)
            correct = (predicted == sample["cipher_family"])

            eval_dur = result.get("eval_duration", 0) or 0
            if isinstance(eval_dur, (int, float)) and eval_dur > 1e9:
                latency_api = eval_dur / 1e9
            else:
                latency_api = latency

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
                "latency_api_s": round(latency_api, 3),
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
    print(f"\n[minimax-m3] COMPLETE: {total_calls} calls in {elapsed:.0f}s | skipped={skipped} errors={errors}")
    print(f"   Shard: {SHARD_PATH}")

if __name__ == "__main__":
    run()
