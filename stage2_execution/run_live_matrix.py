#!/usr/bin/env python3
"""
Unified Live Evaluation Matrix Runner
======================================
Runs Tier-1/2/3 prompts against 5 backends (3 Ollama + 2 OpenRouter)
on the 140-file corpus_ultra sample. Checkpoint/resume supported.

Usage:
    python3 run_live_matrix.py --smoke          # 7 files × 5 backends × tier1 = 35 calls
    python3 run_live_matrix.py --full            # 140 files × 5 backends × 3 tiers = 2100 calls

Backends:
    gemma4:31b-cloud           → Ollama (local)
    gpt-oss:120b-cloud         → Ollama (local)
    nemotron-3-super:cloud     → Ollama (local)
    openrouter/owl-alpha       → OpenRouter (free)
    google/gemma-4-31b-it:free → OpenRouter (free)
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
JSONL_PATH = RESULTS_DIR / "live_matrix_full.jsonl"
SMOKE_RESULTS_PATH = RESULTS_DIR / "smoke_test.json"

# ── API configs ────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_openrouter_key():
    """Read OpenRouter API key from Hermes .env file. Never hardcode."""
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
    # Fallback: try os.environ (for cases where it's been injected)
    return os.environ.get("OPENROUTER_API_KEY", "")

OPENROUTER_KEY = _load_openrouter_key()

BACKENDS = {
    "gemma4:31b-cloud":           {"type": "ollama",      "model_id": "gemma4:31b-cloud"},
    "gpt-oss:120b-cloud":         {"type": "ollama",      "model_id": "gpt-oss:120b-cloud"},
    "nemotron-3-super:cloud":     {"type": "ollama",      "model_id": "nemotron-3-super:cloud"},
    "openrouter/owl-alpha":       {"type": "openrouter",  "model_id": "openrouter/owl-alpha"},
    "google/gemma-4-31b-it:free": {"type": "openrouter",  "model_id": "google/gemma-4-31b-it:free"},
}

# Tier mapping (spec uses 1/2/3; internal files use tier1/tier2/tier3)
TIER_ALIASES = {"1": "tier1", "2": "tier2", "3": "tier3",
                "tier1": "tier1", "tier2": "tier2", "tier3": "tier3"}

# ── Exact prompts from actual_prompt_used_in_corpus14_runs ────────────────────
# These are the VERBATIC prompts from the live_eval_spec.json
# (section_3_prompt_templates, actual_prompt_used_in_corpus14_runs)
# We reconstruct them from the manifest fields.

def build_tier1_prompt(filename: str, file_size: int, cipher_family: str,
                       implementation: str, padding_mode: str, key_size_bits: int,
                       mode: str) -> str:
    """Actual prompt used in corpus-14 Tier-1 runs (from spec)."""
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

def build_tier2_prompt(filename: str, file_size: int) -> str:
    """Actual prompt used in corpus-14 Tier-2 runs (from spec)."""
    return (
        f"You are a cryptographic forensics expert.\n\n"
        f"A ciphertext file is named: \"{filename}\"\n"
        f"File size: {file_size} bytes\n\n"
        f"Based on the filename and typical naming conventions, what cipher family\n"
        f"was likely used?\n\n"
        f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Your answer (cipher name only):"
    )

def build_tier3_prompt(file_size: int, entropy: float, chi2: float, hex_prefix: str,
                       variant: str = "stats_only") -> str:
    """
    Actual prompt used in corpus-14 Tier-3 runs (from spec).
    stats_only: the stats-only variant (original)
    tier3_raw:  additionally includes first 256 bytes as hex for blind analysis
    """
    base = (
        f"You are a cryptographic forensics expert.\n\n"
        f"Analyze the following ciphertext sample and identify the cipher family.\n\n"
        f"Ciphertext Statistics:\n"
        f"- File size: {file_size} bytes\n"
        f"- Shannon entropy: {entropy:.4f} bits/byte\n"
        f"- Chi-square statistic: {chi2:.2f}\n"
        f"- Hex prefix (first 32 bytes): {hex_prefix}\n"
    )

    if variant == "tier3_raw":
        base += (
            f"\nAdditional raw hex preview (first 256 bytes):\n"
            f"[RAW_HEX_WILL_BE_INSERTED]\n"
        )

    base += (
        f"\nCipher family options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
        f"Rules:\n"
        f"1. Provide ONLY the cipher name from the list above\n"
        f"2. No explanation needed\n"
        f"3. If uncertain, provide your best guess\n\n"
        f"Your answer (cipher name only):"
    )
    return base

# ── Stats helpers (reused from live_validation_100.py) ─────────────────────────

def compute_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math_log2(c / n) for c in counts.values()) if n > 0 else 0.0

def math_log2(x):
    import math
    return math.log2(x)

def compute_chi2_stat(data: bytes):
    if not data:
        return 0.0
    import math
    n = len(data)
    expected = n / 256.0
    counts = Counter(data)
    return sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))

def hex_prefix(data: bytes, n: int = 32) -> str:
    return data[:n].hex()

# ── Cipher normalization (reused from tier5_runner_v2.py) ──────────────────────

CIPHER_ALIASES = {
    "aes-128": "AES-128", "aes128": "AES-128",
    "aes-256": "AES-256", "aes256": "AES-256",
    # 3des variants MUST come before "des"
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
    """Map raw model response to canonical cipher family name."""
    if not raw:
        return "UNKNOWN"
    text = raw.strip()
    # Try to extract the answer line first
    answer_lines = []
    for line in text.split("\n"):
        line_s = line.strip()
        if any(marker in line_s.upper() for marker in [
            "FINAL_ANSWER", "ANSWER:", "PREDICTION", "CLASSIFICATION",
            "CIPHER FAMILY", "CIPHER:"
        ]):
            # Extract the part after the colon
            if ":" in line_s:
                answer_lines.append(line_s.split(":", 1)[1].strip())
            else:
                answer_lines.append(line_s)

    # Search in priority: answer lines first, then last 20 lines, then full text
    search_targets = answer_lines + list(reversed(text.strip().split("\n")[-20:]))
    search_targets.append(text)

    for target in search_targets:
        t = target.lower().strip(" `*-_\"")
        for alias, canonical in CIPHER_ALIASES.items():
            if alias in t:
                return canonical

    return "UNKNOWN"

# ── LLM callers (reused from tier5_runner_v2.py, enhanced) ────────────────────

def call_ollama(model: str, prompt: str, timeout: int = 180) -> dict:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return {
                "raw_response": result.get("response", ""),
                "done": result.get("done", False),
                "eval_count": result.get("eval_count", 0),
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "total_duration": result.get("total_duration", 0),
                "load_duration": result.get("load_duration", 0),
                "eval_duration": result.get("eval_duration", 0),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason} | {body[:200]}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def call_openrouter(model: str, prompt: str, timeout: int = 120) -> dict:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 300,
    }).encode()
    req = urllib.request.Request(
        OPENROUTER_URL, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "https://gidaai.local",
            "X-Title": "ACTS_v2_Benchmark",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            choices = result.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                return {
                    "raw_response": content,
                    "done": True,
                    "eval_count": usage.get("completion_tokens", 0),
                    "prompt_eval_count": usage.get("prompt_tokens", 0),
                    "total_duration": 0,
                }
            return {"error": "Empty response from OpenRouter", "raw_response": ""}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason} | {body[:200]}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def call_llm(backend_name: str, prompt: str, timeout: int = 180) -> dict:
    cfg = BACKENDS[backend_name]
    if cfg["type"] == "openrouter":
        return call_openrouter(cfg["model_id"], prompt, timeout=120)
    else:
        return call_ollama(cfg["model_id"], prompt, timeout=timeout)

# ── Checkpoint/resume ─────────────────────────────────────────────────────────

def load_completed_set(jsonl_path: Path) -> set:
    """Load set of (backend, tier, filename, variant) tuples that are already done."""
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
                v = rec.get("variant") or "standard"
                key = (rec.get("backend", ""), rec.get("tier", ""), rec.get("filename", ""), v)
                done.add(key)
            except Exception:
                pass
    return done

def append_result(jsonl_path: Path, record: dict):
    """Append one result record to JSONL file."""
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")

# ── Main runner ───────────────────────────────────────────────────────────────

def run_matrix(smoke=False, tiers=None, backends=None, delay=1.0, timeout=180):
    """
    Run the evaluation matrix.
    smoke=True: 1 file per family × all backends × tier1 only = 35 calls
    """
    # Load manifest
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    samples = manifest["samples"]

    # Filter tiers
    if tiers is None:
        tiers = ["tier1", "tier2", "tier3"]

    # Filter backends
    if backends is None or (len(backends) == 1 and backends[0] == "all"):
        backend_names = list(BACKENDS.keys())
    else:
        backend_names = backends

    # Smoke test: 1 file per family × all backends × tier1
    if smoke:
        seen_families = set()
        smoke_samples = []
        for s in samples:
            if s["cipher_family"] not in seen_families:
                seen_families.add(s["cipher_family"])
                smoke_samples.append(s)
        samples = smoke_samples
        tiers = ["tier1"]  # Only tier1 for smoke
        print(f"🔥 SMOKE TEST: {len(samples)} files (1 per family) × {len(backend_names)} backends × 1 tier = {len(samples) * len(backend_names)} calls")
    else:
        print(f"🚀 FULL MATRIX: {len(samples)} files × {len(backend_names)} backends × {len(tiers)} tiers = {len(samples) * len(backend_names) * len(tiers)} calls")

    # Load checkpoint
    jsonl_path = SMOKE_RESULTS_PATH if smoke else JSONL_PATH
    completed = load_completed_set(jsonl_path)
    print(f"📋 Checkpoint: {len(completed)} results already in {jsonl_path.name}")

    total_calls = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for backend_name in backend_names:
        for tier in tiers:
            variant = None
            tier3_variant = None
            actual_tier = tier  # for prompt building

            for sample in samples:
                filename = sample["filename"]
                file_key = (backend_name, tier, filename, variant or "standard")

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

                # Compute stats for tier3
                entropy = compute_entropy(data)
                chi2 = compute_chi2_stat(data)
                hex_p = hex_prefix(data, 32)

                # Build prompt
                if tier == "tier1":
                    prompt = build_tier1_prompt(
                        filename=filename,
                        file_size=file_size,
                        cipher_family=sample["cipher_family"],
                        implementation=sample["implementation"],
                        padding_mode=sample.get("padding_mode", "unknown"),
                        key_size_bits=sample.get("key_size_bits", 0),
                        mode=sample.get("mode", "unknown"),
                    )
                elif tier == "tier2":
                    prompt = build_tier2_prompt(filename=filename, file_size=file_size)
                elif tier == "tier3":
                    prompt = build_tier3_prompt(
                        file_size=file_size, entropy=entropy,
                        chi2=chi2, hex_prefix=hex_p,
                        variant="stats_only"
                    )
                    tier3_variant = "tier3_raw"  # secondary variant flag
                else:
                    print(f"  ⚠️ Unknown tier: {tier}")
                    continue

                # ── Call LLM (with retry for OpenRouter 429) ──
                max_retries = 3
                result = {"error": "Not called yet", "raw_response": ""}
                latency = 0.0
                for attempt in range(max_retries):
                    t_call = time.time()
                    result = call_llm(backend_name, prompt, timeout=timeout)
                    latency = time.time() - t_call

                    if "error" in result and result["error"]:
                        err_msg = result["error"]
                        if "429" in err_msg:
                            wait = (2 ** attempt) * 5 + 1
                            print(f"    ⏳ 429 rate-limit, retry in {wait}s (attempt {attempt+1}/{max_retries})")
                            time.sleep(wait)
                            continue
                        elif attempt < max_retries - 1:
                            print(f"    ⏳ Error: {err_msg[:80]}, retrying...")
                            time.sleep(2)
                            continue
                    break

                # Parse response
                raw_response = result.get("raw_response", "")
                predicted = normalize_prediction(raw_response)
                correct = (predicted == sample["cipher_family"])

                # Token counts
                prompt_tokens = result.get("prompt_eval_count", 0) or 0
                completion_tokens = result.get("eval_count", 0) or 0
                # Ollama returns nanoseconds
                eval_dur = result.get("eval_duration", 0) or 0
                if isinstance(eval_dur, (int, float)) and eval_dur > 1e9:
                    latency_api = eval_dur / 1e9
                else:
                    latency_api = latency

                record = {
                    "backend": backend_name,
                    "model_id": BACKENDS[backend_name]["model_id"],
                    "tier": tier,
                    "variant": variant,
                    "filename": filename,
                    "ground_truth": sample["cipher_family"],
                    "implementation": sample["implementation"],
                    "file_size": file_size,
                    "prompt_sent": prompt,
                    "raw_response": raw_response,
                    "parsed_prediction": predicted,
                    "correct": correct,
                    "latency_s": round(latency, 3),
                    "latency_api_s": round(latency_api, 3),
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": result.get("error", ""),
                }

                # Tier-3 raw variant: send additional prompt with raw hex
                if tier == "tier3" and tier3_variant == "tier3_raw":
                    raw_hex = data[:256].hex()
                    tier3_raw_prompt = build_tier3_prompt(
                        file_size=file_size, entropy=entropy,
                        chi2=chi2, hex_prefix=hex_p, variant="tier3_raw"
                    ).replace("[RAW_HEX_WILL_BE_INSERTED]", raw_hex)

                    raw_result = {"error": "Not called yet", "raw_response": ""}
                    raw_latency = 0.0
                    for attempt in range(max_retries):
                        t_call = time.time()
                        raw_result = call_llm(backend_name, tier3_raw_prompt, timeout=timeout)
                        raw_latency = time.time() - t_call

                        if "error" in raw_result and raw_result["error"]:
                            if "429" in raw_result["error"]:
                                wait = (2 ** attempt) * 5 + 1
                                print(f"    ⏳ tier3_raw 429, retry in {wait}s")
                                time.sleep(wait)
                                continue
                            elif attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                        break

                    raw_response_t3r = raw_result.get("raw_response", "")
                    predicted_t3r = normalize_prediction(raw_response_t3r)

                    # Store tier3_raw as a separate record
                    raw_record = {
                        "backend": backend_name,
                        "model_id": BACKENDS[backend_name]["model_id"],
                        "tier": tier,
                        "variant": "tier3_raw",
                        "filename": filename,
                        "ground_truth": sample["cipher_family"],
                        "implementation": sample["implementation"],
                        "file_size": file_size,
                        "prompt_sent": tier3_raw_prompt,
                        "raw_response": raw_response_t3r,
                        "parsed_prediction": predicted_t3r,
                        "correct": (predicted_t3r == sample["cipher_family"]),
                        "latency_s": round(raw_latency, 3),
                        "prompt_tokens": raw_result.get("prompt_eval_count", 0),
                        "completion_tokens": raw_result.get("eval_count", 0),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error": raw_result.get("error", ""),
                    }
                    append_result(jsonl_path, raw_record)

                # Checkpoint: write immediately
                append_result(jsonl_path, record)
                completed.add(file_key)
                total_calls += 1

                status = "✅" if correct else "❌"
                err_str = f" ERROR:{record['error'][:60]}" if record.get("error") else ""
                print(f"  {status} [{backend_name}] {tier} {filename}: GT={sample['cipher_family']} PRED={predicted} ({latency:.1f}s){err_str}")

                time.sleep(delay)

    elapsed = time.time() - t_start
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE: {total_calls} calls in {elapsed:.0f}s | skipped={skipped} errors={errors}")
    print(f"   Results saved to: {jsonl_path}")
    print(f"   Throughput: {total_calls / elapsed * 60:.1f} calls/min" if elapsed > 0 else "")
    print(f"{'='*70}")

    return {
        "total_calls": total_calls,
        "skipped": skipped,
        "errors": errors,
        "elapsed_s": round(elapsed, 1),
        "output_file": str(jsonl_path),
    }

# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACTS v2 Live Evaluation Matrix")
    parser.add_argument("--smoke", action="store_true", help="Run smoke test (1 file/family × all backends × tier1)")
    parser.add_argument("--full", action="store_true", help="Run full matrix (140 files × all backends × 3 tiers)")
    parser.add_argument("--tier", nargs="+", default=None, help="Tiers to run: 1 2 3")
    parser.add_argument("--backend", nargs="+", default=None, help="Backend(s) to run (or 'all')")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between calls (seconds)")
    parser.add_argument("--timeout", type=int, default=180, help="LLM timeout (seconds)")
    parser.add_argument("--stats-only", action="store_true",
                        help="Re-compute stats from existing JSONL, skip inference")
    args = parser.parse_args()

    tiers = None
    if args.tier:
        tiers = [TIER_ALIASES.get(t, t) for t in args.tier]

    backends = args.backend

    # Stats-only mode: recompute from existing JSONL
    if args.stats_only:
        jsonl_path = JSONL_PATH if JSONL_PATH.exists() else SMOKE_RESULTS_PATH
        stats_out = WORKSPACE / "stage7_assembly/scaled_results/live_stats.json"
        summary_out = WORKSPACE / "stage7_assembly/scaled_results/live_summary.md"
        stats_out.parent.mkdir(parents=True, exist_ok=True)
        write_stats(jsonl_path, stats_out, summary_out)
        return

    if not args.smoke and not args.full and not args.tier:
        print("ERROR: specify --smoke, --full, or --tier")
        sys.exit(1)

    result = run_matrix(
        smoke=args.smoke,
        tiers=tiers,
        backends=backends,
        delay=args.delay,
        timeout=args.timeout,
    )

    # After full run, auto-compute stats
    if args.full:
        jsonl_path = JSONL_PATH
        stats_out = WORKSPACE / "stage7_assembly/scaled_results/live_stats.json"
        summary_out = WORKSPACE / "stage7_assembly/scaled_results/live_summary.md"
        stats_out.parent.mkdir(parents=True, exist_ok=True)
        write_stats(jsonl_path, stats_out, summary_out)
        print(f"\n📁 Stats: {stats_out}")
        print(f"📁 Summary: {summary_out}")

if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════════
# PART C: Stats computation — Wilson CI, per-backend/tier/family breakdown
# ══════════════════════════════════════════════════════════════════════════════

def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple:
    """Wilson score interval for binomial proportion. Returns (lower, upper)."""
    import math
    if n == 0:
        return (0.0, 0.0)
    p_hat = k / n
    denom = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denom
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denom
    return (max(0.0, center - spread), min(1.0, center + spread))


def compute_stats(jsonl_path: Path) -> dict:
    """
    Read the JSONL results and compute:
    - Per (backend, tier): accuracy + Wilson 95% CI
    - Per (backend, tier, family): accuracy + Wilson 95% CI
    - Overall per-tier accuracy with CI
    - Tier-1 vs Tier-3 non-overlap check per backend
    - Total inferences, errors, missing cells
    """
    import math

    records = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass

    if not records:
        print("ERROR: no records found in JSONL")
        return {}

    # Determine which tiers/variants to include in main stats
    standard_records = [r for r in records if r.get("variant") is None or r.get("variant") == "stats_only"]
    tier3_raw_records = [r for r in records if r.get("variant") == "tier3_raw"]

    backends = sorted(set(r["backend"] for r in standard_records))
    tiers = sorted(set(r["tier"] for r in standard_records))
    families = sorted(set(r["ground_truth"] for r in standard_records))

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(records),
        "standard_records": len(standard_records),
        "tier3_raw_records": len(tier3_raw_records),
        "backends": backends,
        "tiers": tiers,
        "families": families,
    }

    # ── Per (backend, tier) ──
    bt_stats = {}
    for backend in backends:
        for tier in tiers:
            subset = [r for r in standard_records if r["backend"] == backend and r["tier"] == tier]
            if not subset:
                bt_stats[(backend, tier)] = {"k": 0, "n": 0, "accuracy": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "missing": True}
                continue
            k = sum(1 for r in subset if r.get("correct"))
            n = len(subset)
            errors = sum(1 for r in subset if r.get("error"))
            lo, hi = wilson_ci(k, n)
            bt_stats[(backend, tier)] = {
                "k": k, "n": n,
                "accuracy": round(k / n, 4),
                "ci_lower": round(lo, 4),
                "ci_upper": round(hi, 4),
                "errors": errors,
                "avg_latency_s": round(sum(r.get("latency_s", 0) for r in subset) / n, 2),
                "avg_prompt_tokens": round(sum(r.get("prompt_tokens", 0) for r in subset) / n, 0),
                "avg_completion_tokens": round(sum(r.get("completion_tokens", 0) for r in subset) / n, 0),
            }
    stats["per_backend_tier"] = {f"{b}|{t}": v for (b, t), v in sorted(bt_stats.items())}

    # ── Per (backend, tier, family) ──
    btf_stats = {}
    for backend in backends:
        for tier in tiers:
            for family in families:
                subset = [r for r in standard_records
                          if r["backend"] == backend and r["tier"] == tier and r["ground_truth"] == family]
                if not subset:
                    btf_stats[(backend, tier, family)] = {"k": 0, "n": 0, "accuracy": 0.0, "ci_lower": 0.0, "ci_upper": 0.0, "missing": True}
                    continue
                k = sum(1 for r in subset if r.get("correct"))
                n = len(subset)
                lo, hi = wilson_ci(k, n)
                btf_stats[(backend, tier, family)] = {
                    "k": k, "n": n,
                    "accuracy": round(k / n, 4),
                    "ci_lower": round(lo, 4),
                    "ci_upper": round(hi, 4),
                }
    stats["per_backend_tier_family"] = {
        f"{b}|{t}|{f}": v for (b, t, f), v in sorted(btf_stats.items())
    }

    # ── Overall per-tier ──
    for tier in tiers:
        subset = [r for r in standard_records if r["tier"] == tier]
        if not subset:
            stats[f"overall_{tier}"] = {"k": 0, "n": 0, "accuracy": 0.0}
            continue
        k = sum(1 for r in subset if r.get("correct"))
        n = len(subset)
        lo, hi = wilson_ci(k, n)
        stats[f"overall_{tier}"] = {
            "k": k, "n": n,
            "accuracy": round(k / n, 4),
            "ci_lower": round(lo, 4),
            "ci_upper": round(hi, 4),
        }

    # ── Tier-1 vs Tier-3 non-overlap check per backend ──
    non_overlap = {}
    for backend in backends:
        t1 = bt_stats.get((backend, "tier1"), {})
        t3 = bt_stats.get((backend, "tier3"), {})
        if t1 and t3 and not t1.get("missing") and not t3.get("missing"):
            # Non-overlap: CI upper of one doesn't cross CI lower of other
            t1_lo, t1_hi = t1["ci_lower"], t1["ci_upper"]
            t3_lo, t3_hi = t3["ci_lower"], t3["ci_upper"]
            non_overlap_flag = t1_hi < t3_lo or t3_hi < t1_lo
            non_overlap[backend] = {
                "tier1_accuracy": t1["accuracy"],
                "tier1_ci": [t1_lo, t1_hi],
                "tier3_accuracy": t3["accuracy"],
                "tier3_ci": [t3_lo, t3_hi],
                "non_overlap": non_overlap_flag,
                "gap": round(t1["accuracy"] - t3["accuracy"], 4),
            }
    stats["tier1_tier3_non_overlap"] = non_overlap

    # ── tier3_raw summary ──
    for backend in backends:
        subset = [r for r in tier3_raw_records if r["backend"] == backend]
        if subset:
            k = sum(1 for r in subset if r.get("correct"))
            n = len(subset)
            lo, hi = wilson_ci(k, n)
            stats[f"tier3_raw_{backend}"] = {
                "k": k, "n": n, "accuracy": round(k / n, 4),
                "ci_lower": round(lo, 4), "ci_upper": round(hi, 4),
            }

    # ── Error summary ──
    total_errors = sum(1 for r in standard_records if r.get("error"))
    stats["total_errors"] = total_errors
    stats["error_rate"] = round(total_errors / max(len(standard_records), 1), 4)

    # Check for missing cells
    expected_cells = len(backends) * len(tiers)  # standard
    missing_cells = sum(1 for (b, t), v in bt_stats.items() if v.get("missing"))
    stats["expected_backend_tier_cells"] = expected_cells
    stats["missing_backend_tier_cells"] = missing_cells

    # Family-level: expected = backends × tiers × (files_per_family = 20)
    expected_family_cells = len(backends) * len(tiers) * len(families)
    missing_family_cells = sum(1 for v in btf_stats.values() if v.get("missing"))
    stats["expected_backend_tier_family_cells"] = expected_family_cells
    stats["missing_backend_tier_family_cells"] = missing_family_cells

    return stats


def generate_summary_md(stats: dict, jsonl_path: Path) -> str:
    """Generate human-readable markdown summary."""
    lines = []
    lines.append("# ACTS v2 Live Evaluation — Results Summary")
    lines.append(f"\nGenerated: {stats.get('generated_at', 'N/A')}")
    lines.append(f"Source: `{jsonl_path}`")
    lines.append(f"\n**Total records:** {stats.get('total_records', 0)}")
    lines.append(f"**Standard records:** {stats.get('standard_records', 0)}")
    lines.append(f"**tier3_raw records:** {stats.get('tier3_raw_records', 0)}")
    lines.append(f"**Total errors:** {stats.get('total_errors', 0)} ({stats.get('error_rate', 0):.1%})")

    # Overall per-tier
    lines.append("\n\n## Overall Per-Tier Accuracy (Wilson 95% CI)\n")
    lines.append("| Tier | k/N | Accuracy | 95% CI |")
    lines.append("|------|-----|----------|--------|")
    for tier in stats.get("tiers", []):
        key = f"overall_{tier}"
        if key in stats:
            v = stats[key]
            if v["n"] > 0:
                lines.append(f"| {tier} | {v['k']}/{v['n']} | {v['accuracy']:.1%} | [{v['ci_lower']:.1%}, {v['ci_upper']:.1%}] |")

    # Per backend × tier
    lines.append("\n\n## Per-Backend × Tier Accuracy\n")
    backends = stats.get("backends", [])
    tiers = stats.get("tiers", [])

    header = "| Backend |" + "".join(f" {tier} |" for tier in tiers)
    sep = "|---------|" + "--------|" * len(tiers)
    lines.append(header)
    lines.append(sep)

    for backend in backends:
        row = f"| {backend} |"
        for tier in tiers:
            key = f"{backend}|{tier}"
            v = stats.get("per_backend_tier", {}).get(key, {})
            if v.get("missing"):
                row += " N/A |"
            elif v.get("n", 0) > 0:
                row += f" {v['accuracy']:.0%} [{v['ci_lower']:.0%},{v['ci_upper']:.0%}] ({v['k']}/{v['n']}) |"
            else:
                row += " — |"
        lines.append(row)

    # Tier-1 vs Tier-3 non-overlap
    non_ov = stats.get("tier1_tier3_non_overlap", {})
    if non_ov:
        lines.append("\n\n## Tier-1 vs Tier-3 Non-Overlap Check\n")
        lines.append("| Backend | Tier-1 Acc (CI) | Tier-3 Acc (CI) | Gap | Non-Overlap? |")
        lines.append("|---------|------------------|------------------|-----|--------------|")
        for backend in sorted(non_ov.keys()):
            v = non_ov[backend]
            no_str = "✅ Yes" if v["non_overlap"] else "❌ No (overlap)"
            lines.append(
                f"| {backend} "
                f"| {v['tier1_accuracy']:.1%} [{v['tier1_ci'][0]:.1%},{v['tier1_ci'][1]:.1%}] "
                f"| {v['tier3_accuracy']:.1%} [{v['tier3_ci'][0]:.1%},{v['tier3_ci'][1]:.1%}] "
                f"| {v['gap']:.1%} "
                f"| {no_str} |"
            )

    # Missing cells
    lines.append(f"\n\n## Coverage\n")
    lines.append(f"- Expected backend×tier cells: {stats.get('expected_backend_tier_cells', 0)}")
    lines.append(f"- Missing: {stats.get('missing_backend_tier_cells', 0)}")
    lines.append(f"- Expected backend×tier×family cells: {stats.get('expected_backend_tier_family_cells', 0)}")
    lines.append(f"- Missing: {stats.get('missing_backend_tier_family_cells', 0)}")

    if stats.get("total_errors", 0) > 0:
        lines.append(f"- Records with errors: {stats['total_errors']} ({stats['error_rate']:.1%})")

    lines.append("\n\n*CI = Wilson score 95% confidence interval*")
    return "\n".join(lines)


def write_stats(jsonl_path: Path, stats_out_path: Path, summary_out_path: Path):
    """Compute stats and write both JSON stats and markdown summary."""
    print("\n📊 Computing statistics...")
    stats = compute_stats(jsonl_path)

    if not stats:
        print("ERROR: stats computation failed")
        return

    # Save JSON stats
    with open(stats_out_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print(f"   Stats saved to: {stats_out_path}")

    # Save markdown summary
    md = generate_summary_md(stats, jsonl_path)
    with open(summary_out_path, "w") as f:
        f.write(md)
    print(f"   Summary saved to: {summary_out_path}")

    # Print key lines
    print("\n" + "=" * 70)
    for line in md.split("\n"):
        if line.startswith("|") and "—" not in line:
            print(line)
    print("=" * 70)



