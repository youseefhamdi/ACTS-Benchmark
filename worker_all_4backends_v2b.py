#!/usr/bin/env python3
"""
Full 4-backend x 5-tier evaluation on regenerated v2 corpus (pad-diverse).
Backends: gemma4:31b-cloud, gpt-oss:120b-cloud, nemotron-3-super:cloud, openrouter/owl-alpha
Tiers: T1/T2/T3/T4A/T5
Checkpoint/resume per shard.
"""
import json, os, re, time, math, secrets
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage1_data/corpus_ultra"  # regenerated files copied here
MANIFEST_PATH = WORKSPACE / "stage2_execution/results/live_sample_140_v2/manifest.json"
RESULTS_DIR = WORKSPACE / "stage2_execution/results"

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_key():
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

OPENROUTER_KEY = _load_key()

BACKENDS = {
    "gemma4:31b-cloud":       {"type": "ollama",     "model_id": "gemma4:31b-cloud",       "delay": 2.0},
    "gpt-oss:120b-cloud":     {"type": "ollama",     "model_id": "gpt-oss:120b-cloud",     "delay": 2.0},
    "nemotron-3-super:cloud": {"type": "ollama",     "model_id": "nemotron-3-super:cloud", "delay": 30.0},
    "openrouter/owl-alpha":   {"type": "openrouter", "model_id": "openrouter/owl-alpha",   "delay": 3.0},
}

TIERS = ["tier1", "tier2", "tier3", "tier4a", "tier5"]
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

def normalize(raw):
    if not raw: return "UNKNOWN"
    text = raw.strip()
    answer_lines = []
    for line in text.split("\n"):
        ls = line.strip()
        if any(m in ls.upper() for m in [
            "FINAL_ANSWER", "FINAL DETERMINATION", "PREDICTED_CIPHER",
            "FINAL_PREDICTION", "CLASSIFICATION", "CIPHER FAMILY", "CIPHER:",
            "STEP 5", "CONCLUSIONS:", "ANSWER:"
        ]):
            if ":" in ls:
                answer_lines.append(ls.split(":", 1)[1].strip())
            else:
                answer_lines.append(ls)
    search_targets = answer_lines + list(reversed(text.strip().split("\n")[-20:]))
    search_targets.append(text)
    for target in search_targets:
        t = target.lower().strip(" `*_-'")
        for alias, canon in CIPHER_ALIASES.items():
            if alias in t:
                return canon
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
    r = []
    for bs in [8, 16, 32, 64]:
        if n%bs==0: r.append(f"divisible by {bs}")
        else: r.append(f"NOT divisible by {bs} (remainder {n%bs})")
    return "; ".join(r)

def build_t1_prompt(filename, file_size, cipher_family, implementation, padding_mode, key_size_bits, mode):
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

def build_t2_prompt(filename, file_size):
    return (
        f"You are a cryptographic analysis expert.\n\n"
        f"FILENAME: {filename}\n"
        f"FILE SIZE: {file_size} bytes\n\n"
        f"The filename may contain hints about the cipher family.\n\n"
        f"What cipher family produced this ciphertext?\n\n"
        f"POSSIBLE CIPHER FAMILIES: AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Respond with ONLY the cipher family name."
    )

def build_t3_prompt(file_size, entropy, chi2v, hex_p):
    return (
        f"You are a forensic cryptographer analyzing a ciphertext sample.\n\n"
        f"COMPUTED FEATURES:\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2v:.1f}\n"
        f"- Hex prefix (first 32 bytes): {hex_p}\n\n"
        f"POSSIBLE CIPHER FAMILIES: AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"What cipher family produced this ciphertext?\n\n"
        f"STEP 1 — ENTROPY ANALYSIS: [analyze]\n"
        f"STEP 2 — STRUCTURAL ANALYSIS: [file size and block alignment]\n"
        f"STEP 3 — FINAL DETERMINATION: [single cipher family name]"
    )

def build_t4a_prompt(file_size, entropy, chi2v, top_bytes_str, hex_str, block_info):
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2v:.1f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 64 bytes): {hex_str}\n"
        f"- Block alignment: {block_info}\n\n"
        f"## POSSIBLE CIPHER FAMILIES\n"
        f"AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"## TASK\n"
        f"Based on the computed features above, determine which cipher family produced this ciphertext.\n\n"
        f"Respond with ONLY the cipher family name."
    )

def build_t5_prompt(file_size, entropy, chi2v, top_bytes_str, hex_str, block_info):
    return (
        f"You are a forensic cryptographer with access to computational tools.\n\n"
        f"## CIPHERTEXT SAMPLE\n"
        f"The following computed features were extracted from a ciphertext file:\n\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2v:.1f}\n"
        f"- Top 5 byte frequencies: {top_bytes_str}\n"
        f"- Hex preview (first 64 bytes): {hex_str}\n"
        f"- Block alignment: {block_info}\n\n"
        f"## POSSIBLE CIPHER FAMILIES\n"
        f"AES-128, AES-256, 3DES, DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"## OUTPUT FORMAT\n"
        f"You MUST respond in this exact structure:\n\n"
        f"STEP 1 — ENTROPY ANALYSIS:\n"
        f"[analysis]\n\n"
        f"STEP 2 — STRUCTURAL ANALYSIS:\n"
        f"[analysis]\n\n"
        f"STEP 3 — STATISTICAL TESTING:\n"
        f"[analysis]\n\n"
        f"STEP 4 — ELIMINATION:\n"
        f"[which ciphers eliminated and why]\n\n"
        f"STEP 5 — FINAL DETERMINATION:\n"
        f"[ONE cipher family name]\n\n"
        f"CONFIDENCE: [0-100%]\n\n"
        f"BEGIN YOUR FORENSIC ANALYSIS:"
    )

def call_ollama(model, prompt, timeout=180):
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

def call_llm(backend_name, prompt, timeout=180):
    cfg = BACKENDS[backend_name]
    if cfg["type"] == "openrouter":
        return call_openrouter(cfg["model_id"], prompt, timeout=timeout)
    else:
        return call_ollama(cfg["model_id"], prompt, timeout=timeout)

def load_completed(shard_path):
    done = set()
    if not shard_path.exists(): return done
    with open(shard_path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                rec = json.loads(line)
                key = (rec.get("backend",""), rec.get("tier",""), rec.get("filename",""), rec.get("variant") or "standard")
                done.add(key)
            except: pass
    return done

def append_result(shard_path, record):
    with open(shard_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

def run():
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]

    # Build shard paths per backend
    shard_paths = {
        "gemma4:31b-cloud":       RESULTS_DIR / "gemma4_v2b_final.jsonl",
        "gpt-oss:120b-cloud":     RESULTS_DIR / "gptoss_v2b_final.jsonl",
        "nemotron-3-super:cloud": RESULTS_DIR / "nemotron_v2b_final.jsonl",
        "openrouter/owl-alpha":   RESULTS_DIR / "owlalpha_v2b_final.jsonl",
    }

    total_calls = 0
    total_skipped = 0
    t_start = time.time()

    for backend_name in BACKENDS:
        cfg = BACKENDS[backend_name]
        shard_path = shard_paths[backend_name]
        completed = load_completed(shard_path)
        print(f"\n[{backend_name}] Checkpoint: {len(completed)} results in {shard_path.name}")

        for tier in TIERS:
            for sample in samples:
                filename = sample["filename"]
                file_key = (backend_name, tier, filename, "standard")
                if file_key in completed:
                    total_skipped += 1
                    continue

                filepath = CORPUS_DIR / filename
                if not filepath.exists():
                    print(f"  File not found: {filename}")
                    continue

                data = filepath.read_bytes()
                file_size = len(data)
                entropy = compute_entropy(data)
                chi2v = compute_chi2(data)
                hex_p = hex_preview(data, 32)

                if tier == "tier1":
                    prompt = build_t1_prompt(
                        filename, file_size, sample["cipher_family"],
                        sample["implementation"], sample.get("padding_mode","unknown"),
                        sample.get("key_size_bits",0), sample.get("mode","unknown"))
                elif tier == "tier2":
                    prompt = build_t2_prompt(filename, file_size)
                elif tier == "tier3":
                    prompt = build_t3_prompt(file_size, entropy, chi2v, hex_p)
                elif tier == "tier4a":
                    prompt = build_t4a_prompt(file_size, entropy, chi2v, top_bytes(data),
                        hex_preview(data, 64), block_alignment(data))
                elif tier == "tier5":
                    prompt = build_t5_prompt(file_size, entropy, chi2v, top_bytes(data),
                        hex_preview(data, 64), block_alignment(data))
                else:
                    continue

                max_retries = 5
                result = {"error": "not called", "raw_response": ""}
                latency = 0.0
                for attempt in range(max_retries):
                    t_call = time.time()
                    result = call_llm(backend_name, prompt, timeout=TIMEOUT)
                    latency = time.time() - t_call
                    if "error" in result and result["error"]:
                        err = result["error"]
                        if "429" in err:
                            wait = min((2**attempt)*10+1, 120)
                            print(f"    429, retry {wait}s (attempt {attempt+1})")
                            time.sleep(wait)
                            continue
                        elif attempt < max_retries-1:
                            time.sleep(5)
                            continue
                    break

                raw = result.get("raw_response", "")
                predicted = normalize(raw)
                correct = (predicted == sample["cipher_family"])

                eval_dur = result.get("eval_duration", 0) or 0
                if isinstance(eval_dur, (int, float)) and eval_dur > 1e9:
                    latency_api = eval_dur / 1e9
                else:
                    latency_api = latency

                record = {
                    "backend": backend_name, "model_id": cfg["model_id"],
                    "tier": tier, "variant": None, "filename": filename,
                    "ground_truth": sample["cipher_family"],
                    "implementation": sample["implementation"],
                    "file_size": file_size, "parsed_prediction": predicted,
                    "correct": correct, "latency_s": round(latency, 3),
                    "latency_api_s": round(latency_api, 3),
                    "prompt_tokens": result.get("prompt_eval_count", 0) or 0,
                    "completion_tokens": result.get("eval_count", 0) or 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": result.get("error", ""),
                }
                append_result(shard_path, record)
                completed.add(file_key)
                total_calls += 1

                status = "OK" if correct else "  "
                err_str = f" ERR:{record['error'][:50]}" if record.get("error") else ""
                print(f"  {status} {tier} {filename}: GT={sample['cipher_family']} PRED={predicted} ({latency:.1f}s){err_str}")

                time.sleep(cfg["delay"])

        # Per-backend summary
        elapsed = time.time() - t_start
        print(f"\n[{backend_name}] Done. {total_calls} new calls, {total_skipped} skipped, {elapsed:.0f}s")

    print(f"\n=== ALL DONE: {total_calls} calls, {total_skipped} skipped ===")

if __name__ == "__main__":
    run()
