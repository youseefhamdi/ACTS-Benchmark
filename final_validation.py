#!/usr/bin/env python3
"""Final validation: ensure all key numbers are consistent across deliverables."""

import json
from pathlib import Path
from collections import defaultdict

def check_consistency():
    errors = []
    warnings = []
    
    # 1. Check real results match merged summary
    real_results = Path("stage2_execution/results")
    
    models = {
        "gemma4_fixed.json": {"tier1": {"correct": 7, "total": 7}, "tier2": {"correct": 6, "total": 7}, "tier3": {"correct": 1, "total": 7}},
        "gptoss_all_tiers.json": {"tier1": {"correct": 7, "total": 7}, "tier2": {"correct": 6, "total": 7}, "tier3": {"correct": 3, "total": 7}},
        "nemotron_all_tiers.json": {"tier1": {"correct": 7, "total": 7}, "tier2": {"correct": 7, "total": 7}, "tier3": {"correct": 4, "total": 7}},
    }
    
    for fn, expected in models.items():
        path = real_results / fn
        if not path.exists():
            errors.append(f"MISSING: {fn}")
            continue
        
        with open(path) as f:
            data = json.load(f)
        
        by_tier = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in data["results"]:
            by_tier[r["tier"]]["total"] += 1
            if r["correct"]:
                by_tier[r["tier"]]["correct"] += 1
        
        for tier, exp_stats in expected.items():
            acc = by_tier[tier]["correct"] / by_tier[tier]["total"]
            exp_acc = exp_stats["correct"] / exp_stats["total"]
            if abs(acc - exp_acc) > 0.001:
                errors.append(f"MISMATCH in {fn} {tier}: got {acc:.4f}, expected {exp_acc:.4f}")
    
    # 2. Check merged results match individual files
    merged_path = real_results / "merged_real_results.json"
    if merged_path.exists():
        with open(merged_path) as f:
            merged = json.load(f)
        
        avg_t3 = merged.get("summary", {}).get("tier3_avg")
        if avg_t3 is not None:
            computed_avg = sum(m["tier3"]["correct"] / m["tier3"]["total"] 
                              for m in models.values()) / len(models)
            computed_avg = float(computed_avg)
            if abs(avg_t3 - computed_avg) > 0.001:
                errors.append(f"merged_real_results.json tier3_avg mismatch: {avg_t3} vs {computed_avg}")
    else:
        warnings.append("merged_real_results.json not found")
    
    # 3. Check corpus size
    corpus_dir = Path("stage1_data/corpus")
    if corpus_dir.exists():
        bin_files = list(corpus_dir.glob("*.bin"))
        if len(bin_files) != 140:
            warnings.append(f"Corpus has {len(bin_files)} .bin files, expected 140")
        else:
            print(f"✓ Corpus: {len(bin_files)} .bin files")
    else:
        errors.append("stage1_data/corpus directory not found")
    
    # 4. Check test samples
    test_dir = Path("stage1_data/test_samples")
    if test_dir.exists():
        test_files = [f for f in test_dir.iterdir() if f.suffix == '.bin']
        if len(test_files) < 7:
            warnings.append(f"Test samples: {len(test_files)} files, expected 7")
        else:
            print(f"✓ Test samples: {len(test_files)} files")
    
    # 5. Check ablation results
    ablation_path = Path("../ablation_results.json")
    if ablation_path.exists():
        with open(ablation_path) as f:
            ablation = json.load(f)
        configs = ablation.get("results", [])
        if len(configs) != 10:
            warnings.append(f"Ablation has {len(configs)} configs, expected 10")
        else:
            print(f"✓ Ablation: {len(configs)} configurations")
    else:
        warnings.append("ablation_results.json not found")
    
    # 6. Check chi2 results
    chi2_path = Path("../chi2_results.json")
    if chi2_path.exists():
        with open(chi2_path) as f:
            chi2 = json.load(f)
        comparisons = chi2.get("comparisons", [])
        if len(comparisons) != 400:
            warnings.append(f"χ² has {len(comparisons)} comparisons, expected 400")
        else:
            print(f"✓ χ² validation: {len(comparisons)} comparisons")
    else:
        warnings.append("chi2_results.json not found")
    
    # 7. Check scripts exist
    required_scripts = [
        "generate_corpus.py", "split_protocol.py", "chi2_validator.py",
        "ablation_runner.py", "statistical_analysis.py", "consistency_checker.py",
        "ollama_benchmark_runner.py"
    ]
    script_base = Path("..")
    for script in required_scripts:
        if not (script_base / script).exists():
            errors.append(f"MISSING SCRIPT: {script}")
    
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    
    if errors:
        print("\n❌ ERRORS:")
        for e in errors:
            print(f"  - {e}")
    
    if warnings:
        print("\n⚠️ WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    
    if not errors and not warnings:
        print("\n✅ ALL CHECKS PASSED")
    elif not errors:
        print("\n✅ NO ERRORS (warnings only)")
    
    return len(errors) == 0

if __name__ == "__main__":
    import os
    os.chdir("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
    check_consistency()
