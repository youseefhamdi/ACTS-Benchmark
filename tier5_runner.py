#!/usr/bin/env python3
"""
Tier-5 Benchmark Runner — ACTS v2
===================================
Runs the highest-tier evaluation: Forced Chain-of-Thought + Evidence Citation
Tests whether forcing explicit reasoning exposes the lack of genuine cryptanalysis.

Sub-tiers:
- 5A: Forced CoT with evidence citation
- 5B: Code-as-reasoning (must write Python analysis)
- 5C: Self-correction with contradiction detection

Usage:
    python3 tier5_runner.py --samples corpus/ --tier 5a --model gemma4:31b-cloud
    python3 tier5_runner.py --samples corpus/ --tier 5b --model gpt-oss:120b-cloud
    python3 tier5_runner.py --samples corpus/ --tier 5c --model nemotron-3-super:cloud
"""

import json, os, sys, argparse, hashlib, math, time
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional

# ── Stats tools (same as original benchmark) ─────────────────────────────────

def compute_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())

def compute_chi2(data: bytes) -> tuple:
    if not data:
        return 0.0, 1.0
    n = len(data)
    expected = n / 256.0
    counts = Counter(data)
    chi2 = sum(((counts.get(b, 0) - expected) ** 2 / expected) for b in range(256))
    # Approximate p-value (for display only; exact requires scipy)
    df = 255
    # Rough approximation: if chi2 << df, p ≈ 1; if chi2 > 2*df, p < 0.01
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

# ── Prompt builder ───────────────────────────────────────────────────────────

def load_prompt(template_path: str, **kwargs) -> str:
    template = Path(template_path).read_text()
    return template.format(**kwargs)

def build_tier5_prompt(tier: str, filepath: str, filename: str) -> str:
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
        return load_prompt("stage2_execution/prompts/tier5a_cot_enforced.md", **common)
    elif tier == "5b":
        common["hex_preview"] = hex_preview(data, 256)
        return load_prompt("stage2_execution/prompts/tier5b_code_reasoning.md", **common)
    elif tier == "5c":
        return load_prompt("stage2_execution/prompts/tier5c_self_correction.md", **common)
    else:
        raise ValueError(f"Unknown tier: {tier}")

# ── LLM inference ────────────────────────────────────────────────────────────

def call_ollama(model: str, prompt: str, timeout: int = 180) -> Dict:
    import urllib.request
    data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "seed": 42, "num_ctx": 8192},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            return {
                "raw_response": result["response"],
                "done": result.get("done", False),
                "eval_count": result.get("eval_count", 0),
                "tokens_per_second": result.get("eval_count", 1) / max(result.get("total_duration", 1) / 1e9, 0.001),
            }
    except Exception as e:
        return {"error": str(e), "raw_response": ""}

def extract_prediction_tier5(raw: str, tier: str) -> Dict:
    """Extract structured prediction from Tier-5 response"""
    text = raw.lower()
    
    # Try to find the final answer section
    result = {
        "tier": f"tier{tier}",
        "raw_response": raw,
        "final_answer_text": "",
        "confidence": None,
        "cot_present": False,
        "evidence_cited": [],
        "reasoning_quality": 0,  # Will be judged externally
    }
    
    # Check for CoT markers (Tier 5A)
    cot_markers = ["step 1", "step 2", "step 3", "entropy analysis", "structural analysis", "final determination"]
    result["cot_present"] = any(marker in text for marker in cot_markers)
    
    # Check for code blocks (Tier 5B)
    result["code_present"] = "```python" in raw or "def analyze_ciphertext" in raw
    
    # Check for self-critique (Tier 5C)
    result["self_critique_present"] = "fallacy" in text and "round 2" in text
    
    # Extract final answer
    for line in raw.split("\n"):
        line_stripped = line.strip().lower()
        if any(marker in line_stripped for marker in [
            "final determination:", "predicted_cipher:", "final_prediction:",
            "step 5", "classification:", "cipher family:", "answer:"
        ]):
            result["final_answer_text"] = line.strip()
            break
    
    # Extract confidence
    import re
    conf_match = re.search(r'confidence[:\s]+(\d+)', raw.lower())
    if conf_match:
        result["confidence"] = int(conf_match.group(1))
    
    return result

# ── Main runner ──────────────────────────────────────────────────────────────

def run_tier5_benchmark(args) -> Dict:
    corpus_dir = Path(args.samples)
    tier = args.tier
    model = args.model
    
    print(f"🚀 Tier-5 ({tier}) Benchmark: {model}")
    print(f"   Corpus: {corpus_dir}")
    print(f"   Files:  scanning...")
    
    # Collect test files
    test_files = []
    for f in sorted(corpus_dir.glob("*.bin")):
        # Extract cipher from filename (for ground truth)
        cipher = f.stem.split("_")[1] if "_" in f.stem else "unknown"
        # Normalize cipher names
        cipher_map = {
            "enc": "aes128", "aes": "aes128", "aes128": "aes128",
            "aes256": "aes256",
            "3des": "3des", "tripledes": "3des",
            "des": "des",
            "chacha20": "chacha20", "chacha": "chacha20",
            "rsa2048": "rsa2048", "rsa": "rsa2048", "rsa-2048": "rsa2048",
            "mlkem768": "mlkem768", "ml": "mlkem768", "ml-kem": "mlkem768", "ml-kem-768": "mlkem768",
        }
        cipher = cipher_map.get(cipher, cipher)
        test_files.append((f, cipher))
    
    if args.limit:
        test_files = test_files[:args.limit]
    
    print(f"   Found:  {len(test_files)} files")
    print()
    
    results = []
    correct = 0
    total = 0
    
    for i, (filepath, true_cipher) in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] {filepath.name} → {true_cipher}")
        
        prompt = build_tier5_prompt(tier, str(filepath), filepath.name)
        
        start = time.time()
        inference = call_ollama(model, prompt, timeout=args.timeout)
        elapsed = time.time() - start
        
        if "error" in inference:
            print(f"   ❌ ERROR: {inference['error']}")
            continue
        
        parsed = extract_prediction_tier5(inference["raw_response"], tier)
        parsed["file"] = filepath.name
        parsed["true_cipher"] = true_cipher
        parsed["model"] = model
        parsed["backend"] = "ollama"
        parsed["elapsed_seconds"] = round(elapsed, 2)
        parsed["prompt_tokens"] = len(prompt.split())
        
        # Try to normalize predicted cipher
        response_lower = inference["raw_response"].lower()
        predicted = None
        # Check longer/more specific strings first to avoid substring false matches
        # 3des variants must come BEFORE "des"; "triple des" must come before "des" too
        CIPHER_MATCH = [
            ("aes-128", "aes128"), ("aes128", "aes128"),
            ("aes-256", "aes256"), ("aes256", "aes256"),
            ("aes", "aes128"),
            ("3des", "3des"), ("tripledes", "3des"), ("3-des", "3des"),
            ("triple des", "3des"), ("triple-des", "3des"),
            ("des", "des"),
            ("chacha20", "chacha20"),
            ("rsa-2048", "rsa2048"), ("rsa2048", "rsa2048"),
            ("ml-kem-768", "mlkem768"), ("mlkem768", "mlkem768"),
        ]
        for pattern, canonical in CIPHER_MATCH:
            if pattern in response_lower:
                predicted = canonical
                break
        
        parsed["predicted"] = predicted or "unknown"
        parsed["correct"] = (parsed["predicted"] == true_cipher)
        
        if parsed["correct"]:
            correct += 1
        total += 1
        
        print(f"   Predicted: {parsed['predicted']} | CoT: {parsed.get('cot_present', False)} | Time: {elapsed:.1f}s")
        results.append(parsed)
        
        time.sleep(args.delay)
    
    accuracy = correct / total if total > 0 else 0
    
    summary = {
        "metadata": {
            "tier": tier,
            "model": model,
            "total_tests": total,
            "completed": len(results),
            "accuracy": round(accuracy, 3),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "results": results,
        "aggregate": {
            "cot_present_rate": sum(1 for r in results if r.get("cot_present")) / max(len(results), 1),
            "code_present_rate": sum(1 for r in results if r.get("code_present")) / max(len(results), 1),
            "self_critique_rate": sum(1 for r in results if r.get("self_critique_present")) / max(len(results), 1),
            "mean_confidence": sum(r.get("confidence", 0) or 0 for r in results) / max(len(results), 1),
        }
    }
    
    return summary

# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACTS v2 — Tier-5 Benchmark Runner")
    parser.add_argument("--samples", default="stage1_data/corpus",
                        help="Path to corpus directory with .bin files")
    parser.add_argument("--tier", choices=["5a", "5b", "5c"], default="5a",
                        help="Tier-5 sub-variant")
    parser.add_argument("--model", default="gemma4:31b-cloud",
                        help="Ollama model name")
    parser.add_argument("--output", default="",
                        help="Output JSON path (auto-generated if omitted)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of files (0 = all)")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Inference timeout per file")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between requests (seconds)")
    args = parser.parse_args()
    
    summary = run_tier5_benchmark(args)
    
    # Save
    if not args.output:
        args.output = f"stage2_execution/results/tier5{args.tier}_{args.model.replace('/', '_').replace(':', '_')}.json"
    
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(summary, open(out_path, "w"), indent=2)
    
    print()
    print("=" * 60)
    print(f"✅ Tier-5{args.tier} Complete")
    print(f"   Model:    {args.model}")
    print(f"   Files:    {summary['metadata']['total_tests']}")
    print(f"   Accuracy: {summary['metadata']['accuracy']:.1%}")
    print(f"   CoT Rate: {summary['aggregate']['cot_present_rate']:.1%}")
    print(f"   Output:   {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
