#!/usr/bin/env python3
"""
Tier-5 Benchmark Runner v2 — ACTS v2
=====================================
Supports both Ollama (local) and OpenRouter (cloud) backends.
Runs pilot (14 files) or full (140 files) corpus.

Usage:
    python3 tier5_runner_v2.py --tier 5a --model gemma4:31b-cloud --backend ollama --pilot
    python3 tier5_runner_v2.py --tier 5b --model nvidia/nemotron-3-super-120b-a12b:free --backend openrouter --pilot
"""

import json, os, sys, argparse, math, time, re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple
import urllib.request

# ── Constants ────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

CIPHER_FAMILIES = {
    "aes_128": "aes128",
    "aes_256": "aes256",
    "3des": "3des",
    "des": "des",
    "chacha20": "chacha20",
    "rsa_2048": "rsa2048",
    "ml_kem_768": "mlkem768",
}

CIPHER_ALIASES = {
    "aes-128": "aes128", "aes128": "aes128",
    "aes-256": "aes256", "aes256": "aes256",
    "3des": "3des", "tripledes": "3des",
    "des": "des",
    "chacha20": "chacha20", "chacha": "chacha20",
    "rsa-2048": "rsa2048", "rsa2048": "rsa2048", "rsa": "rsa2048",
    "ml-kem-768": "mlkem768", "mlkem768": "mlkem768",
    "ml-kem": "mlkem768", "ml": "mlkem768",
    "aes": "aes128",
}

# ── Stats tools ──────────────────────────────────────────────────────────────

def compute_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def compute_chi2(data: bytes) -> Tuple[float, float]:
    if not data:
        return 0.0, 1.0
    n = len(data)
    expected = n / 256.0
    counts = Counter(data)
    chi2 = sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))
    df = 255
    if chi2 < df:
        p = 1.0
    elif chi2 < 2 * df:
        p = 0.5
    else:
        p = 0.01
    return chi2, p

def top_bytes(data: bytes, k: int = 5) -> str:
    counts = Counter(data)
    top = counts.most_common(k)
    return ", ".join(f"0x{b:02x}({c})" for b, c in top)

def hex_preview(data: bytes, n: int = 128) -> str:
    return data[:n].hex()[:256]

# ── File mapping ─────────────────────────────────────────────────────────────

def extract_ground_truth(filename: str, manifest: Optional[Dict] = None) -> str:
    if manifest and filename in manifest:
        raw = manifest[filename]
        return CIPHER_ALIASES.get(raw.lower(), raw.lower())

    name_lower = filename.lower()
    for prefix, normalized in CIPHER_FAMILIES.items():
        prefix_variants = [prefix, prefix.replace("_", "")]
        for pv in prefix_variants:
            if pv in name_lower:
                return normalized
    return "unknown"

def load_manifest(corpus_dir: Path) -> Dict:
    manifest_path = corpus_dir.parent / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        if "samples" in data:
            return {s["filename"]: s["cipher_family"] for s in data["samples"]}
    return {}

def load_pilot_mapping(base_dir: Path) -> List[str]:
    mapping_path = base_dir / "stage1_data" / "corpus_14_sample_mapping.json"
    if mapping_path.exists():
        return list(json.loads(mapping_path.read_text()).keys())
    return []

# ── Prompt builder ───────────────────────────────────────────────────────────

def build_prompt(tier: str, filepath: str, filename: str, prompts_dir: Path) -> str:
    data = open(filepath, "rb").read()
    chi2, chi2_p = compute_chi2(data)

    common = {
        "filename": filename,
        "file_size": len(data),
        "hex_preview": hex_preview(data, 128),
        "entropy": compute_entropy(data),
        "chi2": chi2,
        "chi2_p": chi2_p,
        "top_bytes": top_bytes(data, 5),
    }

    if tier == "5a":
        template_path = prompts_dir / "tier5a_cot_enforced.md"
    elif tier == "5b":
        common["hex_preview"] = hex_preview(data, 256)
        template_path = prompts_dir / "tier5b_code_reasoning.md"
    elif tier == "5c":
        template_path = prompts_dir / "tier5c_self_correction.md"
    else:
        raise ValueError(f"Unknown tier: {tier}")

    template = template_path.read_text()
    return template.format(**common)

# ── LLM inference ────────────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, timeout: int = 180) -> Dict:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "seed": 42, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return {
                "raw_response": result.get("response", ""),
                "done": result.get("done", False),
                "eval_count": result.get("eval_count", 0),
            }
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def call_openrouter(model: str, prompt: str, timeout: int = 120) -> Dict:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode()
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
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
                return {"raw_response": content, "done": True, "eval_count": 0}
            return {"error": "Empty response from OpenRouter", "raw_response": ""}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "raw_response": ""}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def call_llm(model: str, prompt: str, backend: str = "ollama", timeout: int = 180) -> Dict:
    if backend == "openrouter":
        return call_openrouter(model, prompt, timeout=120)
    else:
        return call_ollama(model, prompt, timeout=timeout)

# ── Response parsing ─────────────────────────────────────────────────────────

def extract_prediction(raw: str, tier: str) -> Dict:
    text_lower = raw.lower()
    result = {
        "final_answer_text": "",
        "confidence": None,
        "cot_present": False,
        "code_present": False,
        "self_critique_present": False,
    }

    cot_markers = ["step 1", "step 2", "step 3", "entropy analysis", "structural analysis", "final determination"]
    result["cot_present"] = any(m in text_lower for m in cot_markers)
    result["code_present"] = "```python" in raw or "def analyze_ciphertext" in raw
    result["self_critique_present"] = "fallacy" in text_lower and ("round 2" in text_lower or "self-critique" in text_lower)

    for line in raw.split("\n"):
        line_stripped = line.strip().lower()
        if any(marker in line_stripped for marker in [
            "final determination:", "predicted_cipher:", "final_prediction:",
            "step 5", "classification:", "cipher family:", "answer:"
        ]):
            result["final_answer_text"] = line.strip()
            break

    conf_match = re.search(r'confidence[:\s]+(\d+)', text_lower)
    if conf_match:
        result["confidence"] = int(conf_match.group(1))

    return result

def normalize_prediction(raw: str, final_answer_text: str = "") -> str:
    text_lower = raw.lower()
    # 1st priority: the final answer line
    search_targets = [final_answer_text.lower()] if final_answer_text else []
    # 2nd priority: last 20 lines (reverse order to get the final answer)
    lines = raw.strip().split("\n")
    search_targets.extend(reversed(lines[-20:]))
    # 3rd priority: full text (but we already search in priority order)
    search_targets.append(text_lower)

    for target in search_targets:
        t = target.lower()
        for alias, normalized in CIPHER_ALIASES.items():
            if alias in t:
                return normalized
    return "unknown"

# ── Main benchmark runner ────────────────────────────────────────────────────

def run_benchmark(args) -> Dict:
    corpus_dir = Path(args.samples)
    prompts_dir = Path(args.prompts_dir)
    base_dir = corpus_dir.parent.parent

    manifest = load_manifest(corpus_dir)
    pilot_files = load_pilot_mapping(base_dir) if args.pilot else None

    if pilot_files:
        all_files = [corpus_dir / f for f in pilot_files]
        all_files = [f for f in all_files if f.exists()]
    else:
        all_files = sorted(corpus_dir.glob("*.bin"))

    if args.limit:
        all_files = all_files[:args.limit]

    print(f"🚀 Tier-5 ({args.tier}) Benchmark: {args.model} [{args.backend}]")
    print(f"   Files: {len(all_files)} ({'PILOT' if args.pilot else 'FULL'})")
    print()

    results = []
    correct = 0
    total = 0
    errors = 0

    for i, filepath in enumerate(all_files, 1):
        filename = filepath.name
        true_cipher = extract_ground_truth(filename, manifest)

        print(f"[{i}/{len(all_files)}] {filename} → True: {true_cipher}")

        prompt = build_prompt(args.tier, str(filepath), filename, prompts_dir)

        start = time.time()
        inference = call_llm(args.model, prompt, backend=args.backend, timeout=args.timeout)
        elapsed = time.time() - start

        if "error" in inference and inference["error"]:
            print(f"   ❌ ERROR: {inference['error']}")
            errors += 1
            results.append({
                "file": filename,
                "true_cipher": true_cipher,
                "predicted": "ERROR",
                "correct": False,
                "confidence": None,
                "cot_present": False,
                "code_present": False,
                "self_critique_present": False,
                "raw_response": inference.get("raw_response", ""),
                "elapsed_seconds": round(elapsed, 2),
                "model": args.model,
                "backend": args.backend,
            })
            continue

        parsed = extract_prediction(inference["raw_response"], args.tier)
        predicted = normalize_prediction(inference["raw_response"], parsed.get("final_answer_text", ""))

        entry = {
            "file": filename,
            "true_cipher": true_cipher,
            "predicted": predicted,
            "correct": (predicted == true_cipher),
            "confidence": parsed.get("confidence"),
            "cot_present": parsed.get("cot_present", False),
            "code_present": parsed.get("code_present", False),
            "self_critique_present": parsed.get("self_critique_present", False),
            "raw_response": inference["raw_response"],
            "elapsed_seconds": round(elapsed, 2),
            "model": args.model,
            "backend": args.backend,
        }

        if entry["correct"]:
            correct += 1
        total += 1

        print(f"   Predicted: {predicted} | CoT: {entry['cot_present']} | Time: {elapsed:.1f}s")
        results.append(entry)

        time.sleep(args.delay)

    completed = len([r for r in results if r["predicted"] != "ERROR"])
    accuracy = correct / total if total > 0 else 0

    summary = {
        "metadata": {
            "tier": args.tier,
            "subtier": f"tier{args.tier}_cot_enforced" if args.tier == "5a" else (
                f"tier{args.tier}_code_reasoning" if args.tier == "5b" else f"tier{args.tier}_self_correction"
            ),
            "model": args.model,
            "backend": args.backend,
            "total_tests": len(all_files),
            "completed": completed,
            "accuracy": round(accuracy, 4),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "aggregate": {
            "cot_present_rate": round(sum(1 for r in results if r["cot_present"]) / max(len(results), 1), 4),
            "code_present_rate": round(sum(1 for r in results if r["code_present"]) / max(len(results), 1), 4),
            "self_critique_rate": round(sum(1 for r in results if r["self_critique_present"]) / max(len(results), 1), 4),
            "mean_confidence": round(sum((r["confidence"] or 0) for r in results) / max(len(results), 1), 2),
            "mean_response_time_seconds": round(sum(r["elapsed_seconds"] for r in results) / max(len(results), 1), 2),
        },
        "results": results,
    }

    return summary

def safe_model_name(model: str) -> str:
    return model.replace("/", "_").replace(":", "_").replace(".", "_")

def main():
    parser = argparse.ArgumentParser(description="ACTS v2 — Tier-5 Benchmark Runner v2")
    parser.add_argument("--samples", default="stage1_data/corpus")
    parser.add_argument("--prompts-dir", default="stage2_execution/prompts")
    parser.add_argument("--tier", choices=["5a", "5b", "5c"], default="5a")
    parser.add_argument("--model", default="gemma4:31b-cloud")
    parser.add_argument("--backend", choices=["ollama", "openrouter"], default="ollama")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    summary = run_benchmark(args)

    if not args.output:
        mode = "pilot" if args.pilot else "full"
        safe_name = safe_model_name(args.model)
        args.output = f"stage2_execution/results/tier{args.tier}_{mode}_{safe_name}_{args.backend}.json"

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(out_path, "w"), indent=2)

    print()
    print("=" * 60)
    print(f"✅ Tier-5{args.tier} Complete")
    print(f"   Model:    {args.model}")
    print(f"   Backend:  {args.backend}")
    print(f"   Mode:     {'PILOT' if args.pilot else 'FULL'}")
    print(f"   Files:    {summary['metadata']['total_tests']}")
    print(f"   Completed:{summary['metadata']['completed']}")
    print(f"   Accuracy: {summary['metadata']['accuracy']:.1%}")
    print(f"   CoT Rate: {summary['aggregate']['cot_present_rate']:.1%}")
    print(f"   Code Rate:{summary['aggregate']['code_present_rate']:.1%}")
    print(f"   Crit Rate:{summary['aggregate']['self_critique_rate']:.1%}")
    print(f"   Output:   {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
