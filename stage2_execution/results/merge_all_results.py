#!/usr/bin/env python3
"""Merge all corpus benchmark results into a unified report."""

import json
from pathlib import Path
from collections import defaultdict

def merge():
    results_dir = Path(".")
    
    # Load all result files
    files = {
        "gemma4_corpus14.json": "gemma4:31b-cloud",
        "gptoss_corpus14.json": "gpt-oss:120b-cloud",
        "nemotron_all_tiers.json": "nemotron-3-super:cloud",
        "nemotron_corpus14_tier3only.json": "nemotron-3-super:cloud",
    }
    
    merged_results = []
    
    for fn, model in files.items():
        path = results_dir / fn
        if not path.exists():
            print(f"SKIP: {fn} not found")
            continue
        with open(path) as f:
            data = json.load(f)
        for r in data["results"]:
            r["model"] = model  # normalize model name
            merged_results.append(r)
    
    # Deduplicate by (model, file, tier)
    seen = set()
    deduped = []
    for r in merged_results:
        key = (r["model"], r["filename"], r["tier"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    
    # Stats
    by_model = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
    for r in deduped:
        by_model[r["model"]][r["tier"]]["total"] += 1
        if r["correct"]:
            by_model[r["model"]][r["tier"]]["correct"] += 1
    
    summary = {}
    for model, tiers in by_model.items():
        summary[model] = {}
        for tier, stats in tiers.items():
            summary[model][tier] = {
                "correct": stats["correct"],
                "total": stats["total"],
                "accuracy": stats["correct"] / stats["total"]
            }
    
    output = {
        "metadata": {
            "description": "Merged corpus benchmark results (all models, all tiers)",
            "total_inferences": len(deduped),
            "models": list(by_model.keys()),
            "date": "2026-05-10"
        },
        "summary": summary,
        "results": deduped
    }
    
    with open(results_dir / "merged_corpus_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Merged {len(deduped)} inferences into merged_corpus_results.json")
    
    # Print table
    print("\n" + "="*70)
    print("MERGED RESULTS SUMMARY")
    print("="*70)
    print(f"{'Model':<30} {'Tier-1':<12} {'Tier-2':<12} {'Tier-3':<12} {'Gap'}")
    print("-"*70)
    
    for model in sorted(by_model.keys()):
        tiers = by_model[model]
        t1 = tiers.get("tier1", {"correct":0,"total":1})
        t2 = tiers.get("tier2", {"correct":0,"total":1})
        t3 = tiers.get("tier3", {"correct":0,"total":1})
        
        t1_acc = t1["correct"] / t1["total"] if t1["total"] > 0 else 0
        t2_acc = t2["correct"] / t2["total"] if t2["total"] > 0 else 0
        t3_acc = t3["correct"] / t3["total"] if t3["total"] > 0 else 0
        gap = t1_acc - t3_acc
        
        print(f"{model:<30} {t1_acc:>6.1%}      {t2_acc:>6.1%}      {t3_acc:>6.1%}      {gap:>6.1%}")
    
    return output

if __name__ == "__main__":
    merge()
