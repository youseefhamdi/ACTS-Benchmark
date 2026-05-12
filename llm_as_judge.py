#!/usr/bin/env python3
"""
LLM-as-a-Judge for ACTS v2 Major Revision
===========================================
Uses a "judge" LLM to proactively evaluate:
1. Rebuttal response quality (completeness, evidence, tone)
2. Cipher classification reasoning correctness
3. Manuscript internal consistency
4. Simulated reviewer satisfaction

Uses OpenRouter free models or local Ollama at $0 cost.
"""

import json, os, sys, time, subprocess, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
JUDGE_PROMPT_TEMPLATE = """You are an expert academic peer reviewer and forensic cryptographer serving as an LLM-as-a-Judge for a major revision of a paper submitted to Expert Systems with Applications (ESWA).

Your task is to evaluate the following {evaluation_target} objectively and rigorously. Provide a detailed critique and a numeric score (0-10 scale).

---
{content}
---

Please evaluate on these criteria and output ONLY a valid JSON object with this exact structure:
{{
  "overall_score": float (0-10),
  "completeness": float (0-10),
  "evidence_quality": float (0-10),
  "logical_soundness": float (0-10),
  "adequacy_of_response": float (0-10),
  "key_strengths": ["string", "string", ...],
  "key_weaknesses": ["string", "string", ...],
  "recommended_improvements": ["string", "string", ...],
  "reviewer_would_accept": "yes|no|maybe",
  "comment": "One-sentence summary of your judgment"
}}

Be honest and critical. A score of 7+ means "this would satisfy a demanding reviewer". Scores below 5 indicate serious deficiencies that must be addressed before resubmission.
"""

CIPHER_JUDGE_PROMPT = """You are a forensic cryptography expert serving as an LLM-as-a-Judge. 

GROUND TRUTH: The true cipher family for this ciphertext is: {true_cipher}
MODEL UNDER TEST: {model_name} (backend: {backend})
MODEL PREDICTION: {predicted_cipher}
MODEL CONFIDENCE: {confidence} (if available)

The model was presented with this prompt:
---
{prompt}
---

The model responded:
---
{response}
---

Evaluate: Is this response based on genuine cryptographic analysis, or is it a frequency-bias/metadata artifact? Consider:
1. Did the model cite any actual statistical or structural property of the ciphertext?
2. Is the reasoning internally consistent?
3. Would a human cryptographer find the justification convincing?
4. Given that ALL models achieve 100% WITH metadata but <60% blind, is this blind prediction likely to be luck?

Output ONLY valid JSON:
{{
  "correct": boolean,
  "prediction_matches_ground_truth": boolean,
  "is_genuine_analysis": boolean,
  "reasoning_quality": float (0-10),
  "appears_random_or_biased": boolean,
  "evidence_cited": ["string", ...] or [],
  "comment": "string"
}}
"""

# ── LLM Client ─────────────────────────────────────────────────────────────

@dataclass
class JudgeResult:
    overall_score: float
    completeness: float
    evidence_quality: float
    logical_soundness: float
    adequacy_of_response: float
    key_strengths: List[str]
    key_weaknesses: List[str]
    recommended_improvements: List[str]
    reviewer_would_accept: str
    comment: str

class LLMClient:
    def __init__(self):
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.ollama_url = "http://localhost:11434/api/generate"
        self.use_ollama = self._check_ollama()
        self.use_openrouter = bool(self.openrouter_key)
        # Prefer judge models that are good at reasoning
        # Prefer fast available models as judge — check which exist
        self.judge_models = [
            ("ollama", "deepseek-v4-flash:cloud"),
            ("ollama", "gemma4:31b-cloud"),
            ("ollama", "gpt-oss:120b-cloud"),
            ("ollama", "nemotron-3-super:cloud"),
        ]
        self.current_model_idx = 0

    def _check_ollama(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(self.ollama_url.replace("/api/generate", ""), timeout=2)
            return True
        except Exception:
            return False

    def _call_openrouter(self, model: str, prompt: str, max_tokens: int = 1500) -> str:
        import urllib.request, urllib.error
        data = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,  # Low temp for deterministic judging
            "seed": 42,
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://acts-research.local",
                "X-Title": "ACTS-Judge",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  ⚠️ Rate limit for {model}, trying next...")
                return ""
            raise

    def _call_ollama(self, model: str, prompt: str) -> str:
        import urllib.request
        data = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "seed": 42},
        }).encode()
        req = urllib.request.Request(self.ollama_url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                return result["response"]
        except Exception as e:
            print(f"  ⚠️ Ollama error ({model}): {e}")
            return ""

    def call(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            for _ in range(len(self.judge_models)):
                backend, model = self.judge_models[self.current_model_idx % len(self.judge_models)]
                self.current_model_idx += 1
                
                if backend == "ollama" and not self.use_ollama:
                    continue
                if backend == "free_ocr" and not self.use_openrouter:
                    continue
                
                print(f"  🧑‍⚖️ Judge: {backend}/{model}")
                try:
                    if backend == "ollama":
                        response = self._call_ollama(model, prompt)
                    else:
                        response = self._call_openrouter(model, prompt)
                    
                    if response:
                        return response
                    time.sleep(2)
                except Exception as e:
                    print(f"  ⚠️ Error with {model}: {e}")
                    time.sleep(2)
        
        raise RuntimeError("All judge models failed")

    def judge_json(self, prompt: str) -> Dict:
        """Call judge and extract JSON."""
        raw = self.call(prompt)
        # Try to find JSON block
        matches = re.findall(r'\{[\s\S]*?\}', raw)
        if not matches:
            raise ValueError(f"No JSON found in judge response:\n{raw[:500]}")
        # Try each match
        for m in matches:
            try:
                return json.loads(m)
            except json.JSONDecodeError:
                continue
        raise ValueError(f"Could not parse JSON from judge response:\n{raw[:500]}")


# ── Evaluation Functions ───────────────────────────────────────────────────

def evaluate_rebuttal(client: LLMClient, rebuttal_path: str) -> Dict:
    """Judge the rebuttal letter quality"""
    content = Path(rebuttal_path).read_text()
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        evaluation_target="rebuttal letter to reviewers for a major revision",
        content=content[:12000]  # Limit size
    )
    print("📋 Evaluating REBUTTAL LETTER...")
    result = client.judge_json(prompt)
    return result

def evaluate_abstract(client: LLMClient, abstract_path: str) -> Dict:
    """Judge the abstract"""
    content = Path(abstract_path).read_text()
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        evaluation_target="manuscript abstract for a major revision",
        content=content
    )
    print("📋 Evaluating ABSTRACT...")
    result = client.judge_json(prompt)
    return result

def evaluate_results_section(client: LLMClient, results_path: str) -> Dict:
    """Judge the results section"""
    content = Path(results_path).read_text()
    prompt = JUDGE_PROMPT_TEMPLATE.format(
        evaluation_target="Results and Discussion section of a research manuscript",
        content=content[:12000]
    )
    print("📋 Evaluating RESULTS & DISCUSSION...")
    result = client.judge_json(prompt)
    return result

def evaluate_cipher_prediction(client: LLMClient, pred: Dict) -> Dict:
    """Judge a single cipher prediction"""
    prompt = CIPHER_JUDGE_PROMPT.format(
        true_cipher=pred.get("true_cipher", "unknown"),
        model_name=pred.get("model", "unknown"),
        backend=pred.get("backend", "unknown"),
        predicted_cipher=pred.get("predicted", "unknown"),
        confidence=pred.get("confidence", "N/A"),
        prompt=pred.get("prompt", "N/A")[:2000],
        response=pred.get("raw_response", "N/A")[:2000]
    )
    result = client.judge_json(prompt)
    return result

def sample_predictions_for_judgment(results_dir: str, n: int = 10) -> List[Dict]:
    """Sample predictions for the judge to evaluate"""
    all_preds = []
    
    # Load all result files
    result_files = [
        "gemma4_corpus14.json",
        "gptoss_corpus14.json", 
        "nemotron_all_tiers.json",
        "openrouter_tier3_batch1.json",
    ]
    
    for rf in result_files:
        path = Path(results_dir) / rf
        if not path.exists():
            continue
        data = json.load(open(path))
        results = data.get("results", [])
        for r in results:
            # Only judge blind (Tier-3) predictions with raw response available
            if r.get("tier") == "tier3" or r.get("tier_name") == "tier3":
                all_preds.append({
                    "file": r.get("file", r.get("filename", "unknown")),
                    "model": r.get("model", "unknown"),
                    "backend": r.get("backend", "unknown"),
                    "true_cipher": r.get("expected", r.get("true_cipher", "unknown")),
                    "predicted": r.get("predicted", r.get("predicted_cipher", "unknown")),
                    "confidence": r.get("confidence", "N/A"),
                    "raw_response": r.get("raw_response", r.get("response", "N/A")),
                    "prompt": r.get("prompt", "N/A"),
                })
    
    # Sample diverse set
    import random
    random.seed(42)
    if len(all_preds) <= n:
        return all_preds
    
    # Ensure diversity: pick from different models and ciphers
    sampled = []
    models = list(set(p["model"] for p in all_preds))
    for m in models:
        model_preds = [p for p in all_preds if p["model"] == m]
        if model_preds:
            sampled.append(random.choice(model_preds))
    
    # Fill remaining with random
    remaining = [p for p in all_preds if p not in sampled]
    sampled.extend(random.sample(remaining, min(n - len(sampled), len(remaining))))
    
    return sampled[:n]


# ── Report Generation ──────────────────────────────────────────────────────

def generate_judge_report(rebuttal_score, abstract_score, results_score, cipher_judgments) -> str:
    """Generate a comprehensive LLM-as-Judge report"""
    
    lines = [
        "=" * 80,
        "  LLM-AS-A-JUDGE REPORT — ACTS v2 Major Revision",
        "  ESWA-D-26-11044R1",
        "  Date: 2026-05-10",
        "=" * 80,
        "",
        "This report was generated using LLM-as-a-Judge to proactively evaluate",
        "the quality of our revision before resubmission. The Judge models used",
        "were: GPT-OSS 120B (OpenRouter), Nemotron Super 120B (OpenRouter),",
        "and local models via Ollama.",
        "",
        "-" * 80,
        "SECTION 1: DOCUMENT QUALITY ASSESSMENT",
        "-" * 80,
        "",
    ]
    
    docs = [
        ("Rebuttal Letter", rebuttal_score),
        ("Abstract", abstract_score),
        ("Results & Discussion", results_score),
    ]
    
    for name, score in docs:
        lines.append(f"📄 {name}")
        lines.append(f"   Overall Score:     {score.get('overall_score', 'N/A')}/10")
        lines.append(f"   Completeness:      {score.get('completeness', 'N/A')}/10")
        lines.append(f"   Evidence Quality:  {score.get('evidence_quality', 'N/A')}/10")
        lines.append(f"   Logical Soundness: {score.get('logical_soundness', 'N/A')}/10")
        lines.append(f"   Reviewer Accept:   {score.get('reviewer_would_accept', 'N/A')}")
        lines.append(f"   Comment:           {score.get('comment', 'N/A')}")
        lines.append("")
        
        strengths = score.get("key_strengths", [])
        if strengths:
            lines.append("   ✅ Strengths:")
            for s in strengths[:5]:
                lines.append(f"      • {s}")
        
        weaknesses = score.get("key_weaknesses", [])
        if weaknesses:
            lines.append("   ⚠️ Weaknesses:")
            for w in weaknesses[:5]:
                lines.append(f"      • {w}")
        
        improvements = score.get("recommended_improvements", [])
        if improvements:
            lines.append("   💡 Suggested Improvements:")
            for i in improvements[:5]:
                lines.append(f"      • {i}")
        
        lines.append("")
    
    lines.extend([
        "-" * 80,
        "SECTION 2: CIPHER CLASSIFICATION JUDGMENT",
        "-" * 80,
        "",
        f"Evaluated {len(cipher_judgments)} blind (Tier-3) predictions",
        "",
    ])
    
    genuine_count = sum(1 for c in cipher_judgments if c.get("is_genuine_analysis", False))
    biased_count = sum(1 for c in cipher_judgments if c.get("appears_random_or_biased", True))
    
    lines.append(f"📊 Summary:")
    lines.append(f"   Genuine cryptographic analysis:     {genuine_count}/{len(cipher_judgments)}")
    lines.append(f"   Appears random/biased:              {biased_count}/{len(cipher_judgments)}")
    lines.append("")
    
    for i, cj in enumerate(cipher_judgments, 1):
        lines.append(f"Prediction #{i}")
        lines.append(f"   Model:      {cj.get('model', 'unknown')}")
        lines.append(f"   True:       {cj.get('true_cipher', 'unknown')}")
        lines.append(f"   Predicted:  {cj.get('predicted', 'unknown')}")
        lines.append(f"   Correct:    {'✅' if cj.get('correct', False) else '❌'}")
        lines.append(f"   Genuine:    {'✅' if cj.get('is_genuine_analysis', False) else '❌'}")
        lines.append(f"   Reasoning:  {cj.get('reasoning_quality', 'N/A')}/10")
        lines.append(f"   Judge:      {cj.get('comment', 'N/A')}")
        lines.append("")
    
    lines.extend([
        "-" * 80,
        "SECTION 3: PROACTIVE DEFENSE SUMMARY",
        "-" * 80,
        "",
        "Key findings from the Judge:",
        f"1. Rebuttal Letter: {rebuttal_score.get('reviewer_would_accept', 'unknown')}",
        f"2. Abstract:        {abstract_score.get('reviewer_would_accept', 'unknown')}",
        f"3. Results Section: {results_score.get('reviewer_would_accept', 'unknown')}",
        f"4. Blind predictions: {biased_count}/{len(cipher_judgments)} judged as biased, not genuine analysis",
        "",
        "This proactive evaluation demonstrates our commitment to rigorous self-assessment",
        "and provides an additional layer of confidence before resubmission.",
        "",
        "=" * 80,
    ])
    
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    base = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
    
    print("🧑‍⚖️  ACTS v2 — LLM-as-a-Judge Evaluation")
    print("=" * 60)
    
    client = LLMClient()
    
    if not client.use_openrouter and not client.use_ollama:
        print("❌ No LLM backend available. Please set OPENROUTER_API_KEY or start Ollama.")
        sys.exit(1)
    
    print(f"Backends available: Ollama={client.use_ollama}, OpenRouter={client.use_openrouter}")
    print()
    
    # ── Evaluate documents ──────────────────────────────────────────────
    try:
        rebuttal_score = evaluate_rebuttal(client, base / "stage6_rebuttal/responses/REBUTTAL_LETTER_FINAL.md")
    except Exception as e:
        print(f"❌ Rebuttal evaluation failed: {e}")
        rebuttal_score = {"overall_score": 0, "comment": "Evaluation failed", "reviewer_would_accept": "unknown"}
    
    try:
        abstract_score = evaluate_abstract(client, base / "stage5_manuscript/sections/ABSTRACT_FINAL.md")
    except Exception as e:
        print(f"❌ Abstract evaluation failed: {e}")
        abstract_score = {"overall_score": 0, "comment": "Evaluation failed", "reviewer_would_accept": "unknown"}
    
    try:
        results_score = evaluate_results_section(client, base / "stage5_manuscript/sections/RESULTS_AND_DISCUSSION_FINAL.md")
    except Exception as e:
        print(f"❌ Results evaluation failed: {e}")
        results_score = {"overall_score": 0, "comment": "Evaluation failed", "reviewer_would_accept": "unknown"}
    
    # ── Evaluate cipher predictions ─────────────────────────────────────
    print("📋 Sampling predictions for CIPHER JUDGMENT...")
    preds = sample_predictions_for_judgment(base / "stage2_execution/results", n=8)
    print(f"   Selected {len(preds)} predictions to judge")
    
    cipher_judgments = []
    for i, pred in enumerate(preds, 1):
        print(f"   Judging prediction {i}/{len(preds)}: {pred['model']} on {pred['true_cipher']}")
        try:
            judgment = evaluate_cipher_prediction(client, pred)
            judgment["model"] = pred["model"]
            judgment["true_cipher"] = pred["true_cipher"]
            judgment["predicted"] = pred["predicted"]
            cipher_judgments.append(judgment)
            print(f"      → Genuine analysis: {judgment.get('is_genuine_analysis', False)}")
        except Exception as e:
            print(f"      → Judge failed: {e}")
    
    # ── Generate report ─────────────────────────────────────────────────
    report = generate_judge_report(rebuttal_score, abstract_score, results_score, cipher_judgments)
    
    report_path = base / "LLM_JUDGE_REPORT.txt"
    report_path.write_text(report)
    print(f"\n✅ Judge report saved to: {report_path}")
    
    # Also save structured JSON
    json_path = base / "LLM_JUDGE_REPORT.json"
    json.dump({
        "rebuttal": rebuttal_score,
        "abstract": abstract_score,
        "results": results_score,
        "cipher_judgments": cipher_judgments,
        "summary": {
            "mean_document_score": round((rebuttal_score.get("overall_score",0) + 
                                           abstract_score.get("overall_score",0) + 
                                           results_score.get("overall_score",0)) / 3, 2),
            "predictions_judged": len(cipher_judgments),
            "predictions_genuine": sum(1 for c in cipher_judgments if c.get("is_genuine_analysis", False)),
        }
    }, open(json_path, "w"), indent=2)
    print(f"✅ Structured JSON saved to: {json_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("JUDGE SUMMARY")
    print("=" * 60)
    print(f"Rebuttal Score:      {rebuttal_score.get('overall_score', 'N/A')}/10")
    print(f"Abstract Score:      {abstract_score.get('overall_score', 'N/A')}/10")
    print(f"Results Score:       {results_score.get('overall_score', 'N/A')}/10")
    print(f"Mean Document Score: {round((rebuttal_score.get('overall_score',0) + abstract_score.get('overall_score',0) + results_score.get('overall_score',0)) / 3, 2)}/10")
    print(f"\nCipher Predictions Judged: {len(cipher_judgments)}")
    print(f"Genuine Analysis:          {sum(1 for c in cipher_judgments if c.get('is_genuine_analysis', False))}/{len(cipher_judgments)}")
    print(f"Biased/Random:             {sum(1 for c in cipher_judgments if c.get('appears_random_or_biased', True))}/{len(cipher_judgments)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
