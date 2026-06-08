#!/usr/bin/env python3
"""Backfill the single missing owl-alpha T5 file: ML-KEM-768_0004_openssl.bin"""
import json, os, re, time, math
from pathlib import Path
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage2_execution/results/live_sample_140_v2"
SHARD_PATH = WORKSPACE / "stage2_execution/results/owl_alpha_t4a_t5_v2_final.jsonl"
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
MODEL = "openrouter/owl-alpha"
BACKEND = "openrouter/owl-alpha"

CIPHER_ALIASES = {
    "aes-128": "AES-128", "aes128": "AES-128",
    "aes-256": "AES-256", "aes256": "AES-256",
    "3des": "3DES", "tripledes": "3DES",
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
    for line in text.split("\n"):
        ls = line.strip()
        if any(m in ls.upper() for m in ["FINAL_ANSWER","FINAL DETERMINATION","PREDICTED_CIPHER","FINAL_PREDICTION","CLASSIFICATION","CIPHER FAMILY","CIPHER:","STEP 5","CONCLUSIONS:","ANSWER:"]):
            if ":" in ls: ls = ls.split(":",1)[1].strip()
            t = ls.lower().strip(" `*_-'")
            for alias, canon in CIPHER_ALIASES.items():
                if alias in t: return canon
    t = text.lower()
    for alias, canon in CIPHER_ALIASES.items():
        if alias in t: return canon
    return "UNKNOWN"

def compute_entropy(d):
    if not d: return 0.0
    n = len(d); counts = {}
    for b in d: counts[b] = counts.get(b,0)+1
    return -sum((c/n)*math.log2(c/n) for c in counts.values())

def compute_chi2(d):
    if not d: return 0.0
    n = len(d); expected = n/256.0; counts = {}
    for b in d: counts[b] = counts.get(b,0)+1
    return sum(((counts.get(b,0)-expected)**2/expected) for b in range(256))

def hex_preview(d, n=32): return d[:n].hex()
def top_bytes(d, k=5):
    counts = {}
    for b in d: counts[b] = counts.get(b,0)+1
    return ", ".join(f"0x{b:02x}({c})" for b,c in sorted(counts.items(), key=lambda x:-x[1])[:k])

def block_alignment(d):
    n = len(d)
    r = []
    for bs in [8,16,32,64]:
        if n%bs==0: r.append(f"divisible by {bs}")
        else: r.append(f"NOT divisible by {bs} (remainder {n%bs})")
    return "; ".join(r)

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

def call_or(model, prompt, timeout=120):
    payload = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.2,"max_tokens":2048}).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer":"https://gidaai.local","X-Title":"ACTS_v2_Benchmark",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            choices = result.get("choices",[])
            usage = result.get("usage",{})
            content = choices[0].get("message",{}).get("content","") if choices else ""
            return {"raw_response":content,"eval_count":usage.get("completion_tokens",0) or 0,
                    "prompt_eval_count":usage.get("prompt_tokens",0) or 0,"eval_duration":0}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error":f"HTTP {e.code}: {e.reason} | {body[:200]}","raw_response":""}
    except Exception as e:
        return {"error":str(e),"raw_response":""}

# Load manifest to get ground truth
with open(WORKSPACE / "stage2_execution/results/live_sample_140_v2/manifest.json") as f:
    manifest = json.load(f)
samples = {s["filename"]: s for s in manifest["samples"]}

# The one missing file
MISSING_FILE = "ML-KEM-768_0004_openssl.bin"
sample = samples[MISSING_FILE]
filepath = CORPUS_DIR / MISSING_FILE
data = filepath.read_bytes()
file_size = len(data)

print(f"Backfilling: {MISSING_FILE} (GT={sample['cipher_family']}, size={file_size})")

entropy = compute_entropy(data)
chi2v = compute_chi2(data)
prompt = build_t5_prompt(file_size, entropy, chi2v, top_bytes(data), hex_preview(data,64), block_alignment(data))

max_retries = 5
result = {"error":"not called","raw_response":""}
latency = 0.0
for attempt in range(max_retries):
    t0 = time.time()
    result = call_or(MODEL, prompt, timeout=120)
    latency = time.time() - t0
    if "error" in result and result["error"]:
        err = result["error"]
        if "429" in err:
            wait = min((2**attempt)*10+1, 120)
            print(f"  429, retry in {wait}s (attempt {attempt+1})")
            time.sleep(wait)
            continue
        elif attempt < max_retries-1:
            print(f"  Error: {err[:80]}, retrying...")
            time.sleep(5)
            continue
    break

raw = result.get("raw_response","")
pred = normalize(raw)
correct = (pred == sample["cipher_family"])

record = {
    "backend": BACKEND, "model_id": MODEL, "tier": "tier5", "variant": None,
    "filename": MISSING_FILE, "ground_truth": sample["cipher_family"],
    "implementation": sample["implementation"], "file_size": file_size,
    "parsed_prediction": pred, "correct": correct, "latency_s": round(latency,3),
    "prompt_tokens": result.get("prompt_eval_count",0) or 0,
    "completion_tokens": result.get("eval_count",0) or 0,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "error": result.get("error",""),
}

with open(SHARD_PATH, "a") as f:
    f.write(json.dumps(record, default=str) + "\n")

status = "CORRECT" if correct else "WRONG"
print(f"  Result: PRED={pred} GT={sample['cipher_family']} {status} ({latency:.1f}s)")
if result.get("error"):
    print(f"  Error: {result['error'][:100]}")
