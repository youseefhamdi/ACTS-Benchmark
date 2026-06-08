#!/usr/bin/env python3
"""
ACTS v2 FINAL — Complete 6×6 matrix runner.
6 backends × 6 tiers × 140 files = 5,040 unique (backend, tier, filename) cells.
Tier-3 has 2 variants (stats_only + tier3_raw), T4A and T5 are separate tiers.
Errors are EXCLUDED from scoring (not counted as wrong).
Thinking models: response may be empty; parse thinking field for answer.
"""

import json, os, sys, math, time, re, argparse
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage2_execution/results/live_sample_140_v2"
MANIFEST_PATH = WORKSPACE / "stage2_execution/results/live_sample_140_v2/manifest.json"
RESULTS_DIR = WORKSPACE / "stage2_execution/results"
PROGRESS_LOG = WORKSPACE / "r3_progress.md"

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_or_key():
    env_path = Path("/home/elaref/.hermes/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2 and parts[0] == "OPENROUTER_API_KEY":
                        return parts[1]
    return os.environ.get("OPENROUTER_API_KEY", "")

OR_KEY = _load_or_key()

# ── 6 Backends ──
BACKENDS = {
    "gemma4:31b-cloud":       {"type": "ollama",     "model_id": "gemma4:31b-cloud",       "delay": 2.0, "max_tokens": 300},
    "gpt-oss:120b-cloud":     {"type": "ollama",     "model_id": "gpt-oss:120b-cloud",     "delay": 2.0, "max_tokens": 300},
    "nemotron-3-super:cloud": {"type": "ollama",     "model_id": "nemotron-3-super:cloud", "delay": 3.0, "max_tokens": 500},
    "openrouter/owl-alpha":   {"type": "openrouter", "model_id": "openrouter/owl-alpha",   "delay": 5.0, "max_tokens": 300},
    "google/gemma-4-31b-it:free": {"type": "openrouter", "model_id": "google/gemma-4-31b-it:free", "delay": 5.0, "max_tokens": 300},
    "minimax-m3:cloud":       {"type": "ollama",     "model_id": "minimax-m3:cloud",       "delay": 5.0, "max_tokens": 4000},
}
# Thinking models need higher token limits and answer extraction from thinking field
THINKING_MODELS = {"minimax-m3:cloud"}

# ── Helpers ──
def compute_entropy(data):
    if not data: return 0.0
    counts = Counter(data); n = len(data)
    return -sum((c/n)*math.log2(c/n) for c in counts.values()) if n else 0.0

def compute_chi2(data):
    if not data: return 0.0
    counts = Counter(data); n = len(data); exp = n/256.0
    return sum(((counts.get(i,0)-exp)**2)/exp for i in range(256))

def hex_prefix(data, n): return data[:n].hex()

LABEL_MAP = {
    "AES-256":"AES-256","AES-128":"AES-128","3DES":"3DES","DES":"DES",
    "CHACHA20":"ChaCha20","CHACHA":"ChaCha20","CHAHA":"ChaCha20","CHACHA2O":"ChaCha20",
    "RSA-2048":"RSA-2048","RSA":"RSA-2048",
    "ML-KEM-768":"ML-KEM-768","ML-KEM":"ML-KEM-768",
    "UNKNOWN":"UNKNOWN","UNK":"UNKNOWN",
}

def normalize_prediction(raw, thinking=""):
    text = (raw if raw else thinking).upper().strip()
    for pat in ["AES-256","AES-128","ML-KEM-768","RSA-2048","CHACHA20","3DES","DES"]:
        if pat in text:
            return LABEL_MAP.get(pat, pat.lower())
    if "CHACHA" in text: return "ChaCha20"
    if "RSA" in text: return "RSA-2048"
    if "ML-KEM" in text: return "ML-KEM-768"
    if "AES" in text and "256" in text: return "AES-256"
    if "AES" in text and "128" in text: return "AES-128"
    if "TRIPLE" in text: return "3DES"
    if "DES" in text: return "DES"
    return "UNKNOWN"

def call_ollama(model_id, prompt, max_tokens=300, timeout=120):
    payload = json.dumps({"model": model_id, "prompt": prompt, "stream": False,
                          "options": {"temperature": 0.0, "num_predict": max_tokens}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            raw = data.get("response", "")
            thinking = data.get("thinking", "")
            return {"raw_response": raw, "thinking": thinking,
                    "parsed": normalize_prediction(raw, thinking), "error": ""}
    except Exception as e:
        return {"raw_response": "", "thinking": "", "parsed": "UNKNOWN", "error": str(e)}

def call_openrouter(model_id, prompt, max_tokens=300, timeout=120):
    payload = json.dumps({"model": model_id, "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": 0.0}).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=payload,
                                  headers={"Content-Type": "application/json", "Authorization": f"Bearer {OR_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            raw = data.get("choices",[{}])[0].get("message",{}).get("content","")
            thinking = data.get("choices",[{}])[0].get("message",{}).get("reasoning","")
            return {"raw_response": raw, "thinking": thinking,
                    "parsed": normalize_prediction(raw, thinking), "error": ""}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"raw_response": "", "thinking": "", "parsed": "UNKNOWN", "error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"raw_response": "", "thinking": "", "parsed": "UNKNOWN", "error": str(e)}

def call_llm(backend_name, prompt, timeout=120):
    cfg = BACKENDS[backend_name]
    mt = cfg["max_tokens"]
    if cfg["type"] == "ollama":
        return call_ollama(cfg["model_id"], prompt, max_tokens=mt, timeout=timeout)
    else:
        return call_openrouter(cfg["model_id"], prompt, max_tokens=mt, timeout=timeout)

# ── Prompt builders ──
def build_t1(sample, file_size):
    return (f"You are a cryptographic analysis expert.\n\nGiven the following KNOWN metadata:\n"
            f"- Cipher family: {sample['cipher_family']}\n- Mode: {sample.get('mode','unknown')}\n"
            f"- Implementation: {sample['implementation']}\n\n"
            f"Confirm the cipher family name from this list: "
            f"AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t2(sample, file_size):
    return (f"You are a cryptographic forensics expert.\n\n"
            f"A ciphertext file is named: \"{sample['filename']}\"\n"
            f"File size: {file_size} bytes\n\n"
            f"Based on the filename and typical naming conventions, what cipher family\nwas likely used?\n\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t3(file_size, entropy, chi2, hex_p, variant="stats_only"):
    base = (f"You are a cryptographic forensics expert.\n\n"
            f"Analyze the following ciphertext sample and identify the cipher family.\n\n"
            f"Ciphertext Statistics:\n"
            f"- File size: {file_size} bytes\n"
            f"- Shannon entropy: {entropy:.4f} bits/byte\n"
            f"- Chi-square statistic: {chi2:.2f}\n"
            f"- Hex prefix (first 32 bytes): {hex_p}\n")
    if variant == "tier3_raw":
        base += "\nAdditional raw hex preview (first 256 bytes):\n[RAW_HEX]\n"
    base += ("\nCipher family options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
             "Rules:\n1. Provide ONLY the cipher name from the list above\n"
             "2. No explanation needed\n3. If uncertain, provide your best guess\n\n"
             "Your answer (cipher name only):")
    return base

def build_t4a(file_size, entropy, chi2, hex_p, block_aligned):
    return (f"You are a cryptographic forensics expert with access to computed features.\n\n"
            f"Ciphertext Features:\n"
            f"- File size: {file_size} bytes\n"
            f"- Shannon entropy: {entropy:.4f} bits/byte\n"
            f"- Chi-square statistic: {chi2:.2f}\n"
            f"- Block alignment: {'16-byte aligned' if block_aligned else 'not 16-byte aligned'}\n"
            f"- Byte frequency: {'uniform' if entropy > 7.9 else 'non-uniform'}\n"
            f"- Hex prefix (first 32 bytes): {hex_p}\n\n"
            f"Based on these computed features, identify the cipher family.\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t5(file_size, entropy, chi2):
    return (f"You are a cryptographic forensics expert.\n\n"
            f"Analyze the following ciphertext sample step by step.\n\n"
            f"Ciphertext Statistics:\n"
            f"- File size: {file_size} bytes\n"
            f"- Shannon entropy: {entropy:.4f} bits/byte\n"
            f"- Chi-square statistic: {chi2:.2f}\n\n"
            f"Think through the cryptanalytic reasoning:\n"
            f"1. What does the file size suggest about block vs stream cipher?\n"
            f"2. What does the entropy suggest about cipher strength?\n"
            f"3. What does the chi-square suggest about byte distribution?\n"
            f"4. Which cipher family best matches these characteristics?\n\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"After your reasoning, provide ONLY the cipher family name on the last line.\n"
            f"Your answer (cipher name only):")

# ── Checkpoint ──
def load_completed(jsonl_path):
    done = set()
    if not jsonl_path.exists(): return done
    with open(jsonl_path) as f:
        for line in f:
            try:
                rec = json.loads(line)
                if not rec.get("error") and rec.get("parsed","UNKNOWN") != "UNKNOWN":
                    v = rec.get("variant") or "standard"
                    done.add((rec["backend"], rec["tier"], rec["filename"], v))
            except: pass
    return done

def append_result(jsonl_path, record):
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

# ── Main runner ──
def run_all(backends=None, delay_override=None):
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]
    
    backend_names = backends or list(BACKENDS.keys())
    tiers = ["tier1","tier2","tier3_raw","tier4a","tier5"]
    
    JSONL_PATH = RESULTS_DIR / "live_matrix_full_v2_final.jsonl"
    T4A_PATH = RESULTS_DIR / "tier4a_full_v2_final.jsonl"
    T5_PATH = RESULTS_DIR / "tier5_live_full_v2_final.jsonl"
    
    completed_main = load_completed(JSONL_PATH)
    completed_t4a = load_completed(T4A_PATH)
    completed_t5 = load_completed(T5_PATH)
    
    total_calls = 0
    skipped = 0
    errors = 0
    t_start = time.time()
    
    for bi, backend_name in enumerate(backend_names):
        cfg = BACKENDS[backend_name]
        delay = delay_override if delay_override else cfg["delay"]
        is_thinking = backend_name in THINKING_MODELS
        
        print(f"\n[{bi+1}/{len(backend_names)}] {backend_name} (delay={delay}s, max_tokens={cfg['max_tokens']})")
        
        for tier in tiers:
            # Select checkpoint and prompt builder
            if tier == "tier3_raw":
                # tier3_raw is stored in main JSONL with variant=tier3_raw
                # But we also need the stats_only variant in main JSONL
                # Actually, tier3 stats_only goes to main JSONL with tier=tier3
                # tier3_raw goes to main JSONL with tier=tier3, variant=tier3_raw
                # For simplicity, run both variants through main JSONL
                checkpoint = completed_main
                jsonl_path = JSONL_PATH
                tier_key = "tier3"  # main tier name
            elif tier == "tier4a":
                checkpoint = completed_t4a
                jsonl_path = T4A_PATH
                tier_key = "tier4a"
            elif tier == "tier5":
                checkpoint = completed_t5
                jsonl_path = T5_PATH
                tier_key = "tier5"
            else:
                checkpoint = completed_main
                jsonl_path = JSONL_PATH
                tier_key = tier
            
            si = 0
            for sample in samples:
                filename = sample["filename"]
                filepath = CORPUS_DIR / filename
                if not filepath.exists():
                    print(f"  ⚠ File not found: {filename}"); continue
                
                data = filepath.read_bytes()
                file_size = len(data)
                entropy = compute_entropy(data)
                chi2 = compute_chi2(data)
                hp = hex_prefix(data, 32)
                block_aligned = (file_size % 16 == 0)
                
                # For tier3, we need two variants
                variants_to_run = []
                if tier == "tier3_raw":
                    # Run stats_only variant
                    if (backend_name, "tier3", filename, "standard") not in checkpoint:
                        variants_to_run.append(("standard", build_t3(file_size, entropy, chi2, hp, "stats_only")))
                    # Run tier3_raw variant
                    if (backend_name, "tier3", filename, "tier3_raw") not in checkpoint:
                        raw_hex = data[:256].hex()
                        variants_to_run.append(("tier3_raw", build_t3(file_size, entropy, chi2, hp, "tier3_raw").replace("[RAW_HEX]", raw_hex)))
                else:
                    variant = "standard"
                    key = (backend_name, tier_key, filename, variant)
                    if key in checkpoint:
                        skipped += 1
                        continue
                    # Build prompt
                    if tier == "tier1":
                        prompt = build_t1(sample, file_size)
                    elif tier == "tier2":
                        prompt = build_t2(sample, file_size)
                    elif tier == "tier4a":
                        prompt = build_t4a(file_size, entropy, chi2, hp, block_aligned)
                    elif tier == "tier5":
                        prompt = build_t5(file_size, entropy, chi2)
                    else:
                        continue
                    variants_to_run.append((variant, prompt))
                
                for variant, prompt in variants_to_run:
                    # Retry with backoff
                    max_retries = 5
                    result = None
                    latency = 0.0
                    for attempt in range(max_retries):
                        t_call = time.time()
                        result = call_llm(backend_name, prompt, timeout=180)
                        latency = time.time() - t_call
                        
                        if result.get("error"):
                            err = result["error"]
                            if "429" in err:
                                wait = min((2**attempt)*5 + 1, 60)
                                print(f"    ⏳ 429, retry in {wait}s (attempt {attempt+1})")
                                time.sleep(wait)
                                continue
                            elif attempt < max_retries-1:
                                time.sleep(3)
                                continue
                        # Check if we got a valid answer
                        if result.get("parsed","UNKNOWN") != "UNKNOWN" or not result.get("error"):
                            break
                        if attempt < max_retries-1:
                            time.sleep(2)
                    
                    if result is None:
                        result = {"raw_response":"","thinking":"","parsed":"UNKNOWN","error":"No result"}
                    
                    parsed = result.get("parsed","UNKNOWN")
                    gt = sample["cipher_family"]
                    correct = (parsed == gt) if parsed != "UNKNOWN" else False
                    has_error = bool(result.get("error")) or parsed == "UNKNOWN"
                    
                    # For tier3 variants, store with appropriate tier/variant
                    if tier == "tier3_raw":
                        rec_tier = "tier3"
                        rec_variant = variant  # "standard" or "tier3_raw"
                    else:
                        rec_tier = tier_key
                        rec_variant = variant
                    
                    record = {
                        "backend": backend_name, "model_id": cfg["model_id"],
                        "tier": rec_tier, "variant": rec_variant,
                        "filename": filename, "ground_truth": gt,
                        "implementation": sample["implementation"],
                        "file_size": file_size, "parsed_prediction": parsed,
                        "correct": correct, "latency_s": round(latency,3),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": result.get("error",""),
                    }
                    
                    append_result(jsonl_path, record)
                    
                    if not has_error:
                        checkpoint_key = (backend_name, rec_tier, filename, rec_variant)
                        if tier == "tier3_raw":
                            completed_main.add(checkpoint_key)
                        elif tier == "tier4a":
                            completed_t4a.add(checkpoint_key)
                        elif tier == "tier5":
                            completed_t5.add(checkpoint_key)
                        else:
                            completed_main.add(checkpoint_key)
                        total_calls += 1
                    else:
                        errors += 1
                    
                    si += 1
                    sym = "✅" if correct else ("❌" if not has_error else "⚠️")
                    print(f"  {sym} {rec_tier:10s} {rec_variant:12s} {filename[:25]:25s} GT={gt:10s} PRED={parsed:12s} ({latency:.1f}s)")
                    
                    time.sleep(delay)
            
            # Progress after each tier
            print(f"  ✓ {tier} complete for {backend_name}")
    
    elapsed = time.time() - t_start
    
    # Final coverage report
    print(f"\n{'='*70}")
    print(f"DONE: {total_calls} new calls in {elapsed:.0f}s | skipped={skipped} errors={errors}")
    
    # Count coverage
    all_completed_main = load_completed(JSONL_PATH)
    all_completed_t4a = load_completed(T4A_PATH)
    all_completed_t5 = load_completed(T5_PATH)
    
    print(f"\n=== Coverage ===")
    for b in backend_names:
        for t in ["tier1","tier2","tier3"]:
            files = set(k[2] for k in all_completed_main if k[0]==b and k[1]==t)
            variants = Counter(k[3] for k in all_completed_main if k[0]==b and k[1]==t)
            print(f"  {b:40s} {t}: {len(files)}/140  variants:{dict(variants)}")
        for t, cp in [("tier4a", all_completed_t4a), ("tier5", all_completed_t5)]:
            files = set(k[2] for k in cp if k[0]==b)
            print(f"  {b:40s} {t}: {len(files)}/140")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--backends", nargs="*", default=None)
    parser.add_argument("--delay", type=float, default=None)
    args = parser.parse_args()
    run_all(backends=args.backends, delay_override=args.delay)
