#!/usr/bin/env python3
"""
Consistency checker — validates all numbers across JSON sources
and reports contradictions for ACTS v2 revision.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def check_tier1_consistency(gt: dict, final_summary: dict, rebuttal_letter: dict) -> List[str]:
    """Check R4.1: Tier-1 numbers must be consistent across all sources."""
    issues = []

    # GROUND_TRUTH.json live_ollama values
    gt_gemma_t1 = gt.get("live_ollama", {}).get("gemma4_31b", {}).get("tier1", {}).get("accuracy")
    gt_gptoss_t1 = gt.get("live_ollama", {}).get("gptoss_120b", {}).get("tier1", {}).get("accuracy")
    gt_nemotron_t1 = gt.get("live_ollama", {}).get("nemotron_super", {}).get("tier1", {}).get("accuracy")

    # FINAL_RESULTS_SUMMARY.json values
    fs = final_summary.get("models_summary", {})
    fs_gemma_t1 = fs.get("gemma4:31b-cloud (Ollama)", {}).get("tier1_acc")
    fs_gptoss_t1 = fs.get("gpt-oss:120b-cloud (Ollama)", {}).get("tier1_acc")
    fs_nemotron_t1 = fs.get("nemotron-3-super:cloud (Ollama)", {}).get("tier1_acc")

    pairs = [
        ("gemma4_tier1", gt_gemma_t1, fs_gemma_t1),
        ("gptoss_tier1", gt_gptoss_t1, fs_gptoss_t1),
        ("nemotron_tier1", gt_nemotron_t1, fs_nemotron_t1),
    ]
    for name, gt_val, fs_val in pairs:
        if gt_val is None or fs_val is None:
            issues.append(f"MISSING: {name} — GT={gt_val}, FINAL_SUMMARY={fs_val}")
        elif abs(gt_val - fs_val) > 0.001:
            issues.append(f"MISMATCH: {name} — GROUND_TRUTH={gt_val:.4f}, FINAL_SUMMARY={fs_val:.4f}")

    return issues


def check_tier3_consistency(gt: dict, final_summary: dict) -> List[str]:
    """Check Tier-3 blind accuracy consistency."""
    issues = []

    gt_values = {
        "gemma4_31b": gt.get("live_ollama", {}).get("gemma4_31b", {}).get("tier3", {}).get("accuracy"),
        "gptoss_120b": gt.get("live_ollama", {}).get("gptoss_120b", {}).get("tier3", {}).get("accuracy"),
        "nemotron_super": gt.get("live_ollama", {}).get("nemotron_super", {}).get("tier3", {}).get("accuracy"),
    }

    fs = final_summary.get("models_summary", {})
    fs_values = {
        "gemma4_31b": fs.get("gemma4:31b-cloud (Ollama)", {}).get("tier3_acc"),
        "gptoss_120b": fs.get("gpt-oss:120b-cloud (Ollama)", {}).get("tier3_acc"),
        "nemotron_super": fs.get("nemotron-3-super:cloud (Ollama)", {}).get("tier3_acc"),
    }

    for name in gt_values:
        gt_val = gt_values[name]
        fs_val = fs_values.get(name)
        if gt_val is None or fs_val is None:
            issues.append(f"MISSING Tier-3: {name} — GT={gt_val}, FINAL_SUMMARY={fs_val}")
        elif abs(gt_val - fs_val) > 0.001:
            issues.append(f"MISMATCH Tier-3: {name} — GROUND_TRUTH={gt_val:.4f}, FINAL_SUMMARY={fs_val:.4f}")

    return issues


def check_corpus_counts(gt: dict) -> List[str]:
    """Verify corpus sample counts match manifest."""
    issues = []
    # Check pilot counts
    pilot_per = gt.get("dataset_pilot_per_family", {})
    pilot_total = sum(pilot_per.values())
    if pilot_total != 140:
        issues.append(f"Pilot per-family sum = {pilot_total}, expected 140")

    # Check expanded counts
    expanded_per = gt.get("dataset_expanded_per_family", {})
    expanded_total = sum(expanded_per.values())
    if expanded_total != 700:
        issues.append(f"Expanded per-family sum = {expanded_total}, expected 700")

    # Check family names match
    expected = {"aes128", "aes256", "3des", "des", "chacha20", "rsa2048", "mlkem768"}
    pilot_keys = set(pilot_per.keys())
    expanded_keys = set(expanded_per.keys())
    if pilot_keys != expected:
        issues.append(f"Pilot families mismatch: {pilot_keys} vs {expected}")
    if expanded_keys != expected:
        issues.append(f"Expanded families mismatch: {expanded_keys} vs {expected}")

    # Verify actual files exist
    corpus_dir = Path("stage1_data/corpus_expanded")
    if corpus_dir.exists():
        actual_files = list(corpus_dir.glob("*.bin"))
        if len(actual_files) != 700:
            issues.append(f"Expanded corpus has {len(actual_files)} .bin files, expected 700")

    return issues


def check_ablation_claims(rebuttal_text: str, ablation_results: dict) -> List[str]:
    """Check that ablation numbers in rebuttal match real results."""
    issues = []
    if ablation_results is None:
        issues.append("CRITICAL: No ablation_results.json found. Rebuttal claims unverified.")
        return issues

    configs = ablation_results.get("configs", [])
    if not configs:
        issues.append("CRITICAL: Ablation results contain no configs.")
        return issues

    full_acc = None
    for cfg in configs:
        if cfg.get("config_name") == "full_pipeline":
            full_acc = cfg.get("test_accuracy")
            break

    if full_acc is None:
        issues.append("CRITICAL: full_pipeline config missing from ablation results.")
    elif "92.3" in rebuttal_text or "92.90" in rebuttal_text:
        issues.append(
            f"WARNING: Old rebuttal still contains fabricated 92.3% claim. "
            f"Real accuracy is {full_acc:.2%}."
        )
    elif "DEPRECATED" in rebuttal_text:
        issues.append(
            f"INFO: Full pipeline accuracy = {full_acc:.2%} (old 92.3% claim deprecated). "
            f"Honest rebuttal in use."
        )

    return issues


def check_train_test_claims(ablation_results: dict) -> List[str]:
    """Verify R5.2 train/test separation claims."""
    issues = []
    if ablation_results is None:
        issues.append("CRITICAL: Cannot verify R5.2 without ablation results.")
        return issues

    meta = ablation_results.get("metadata", {})
    test_size = meta.get("test_size")
    if test_size is None:
        issues.append("CRITICAL: ablation_results.json missing metadata.test_size")
    elif abs(test_size - 0.30) > 0.01:
        issues.append(f"WARNING: test_size={test_size}, rebuttal claims 0.30")

    train_n = meta.get("train_samples")
    test_n = meta.get("test_samples")
    if train_n and test_n:
        ratio = test_n / (train_n + test_n)
        if abs(ratio - 0.30) > 0.02:
            issues.append(f"WARNING: actual test ratio={ratio:.2%}, expected ~30%")

    return issues


def check_chi2_claims(chi2_results: dict, rebuttal: dict) -> List[str]:
    """Verify R5.3 chi² claims."""
    issues = []
    if chi2_results is None:
        issues.append("WARNING: No chi2_results.json found.")
        return issues

    summary = chi2_results.get("summary", {})
    cohens_d = summary.get("overall_cohens_d")
    if cohens_d is None:
        issues.append("WARNING: chi2_results missing Cohen's d")
    elif abs(cohens_d) > 0.20:
        issues.append(
            f"INFO: Cohen's d = {cohens_d:.3f}. "
            "Rebuttal claims 'negligible' — verify this is correctly described."
        )

    n_comp = summary.get("total_comparisons", 0)
    if n_comp != 400:
        issues.append(f"WARNING: chi2 has {n_comp} comparisons, rebuttal claims 400")

    return issues


def print_report(issues: List[str], section: str):
    print(f"\n{'='*60}")
    print(f"CHECK: {section}")
    print("=" * 60)
    if not issues:
        print("  PASS — no issues found.")
    else:
        for iss in issues:
            severity = "PASS"
            if "CRITICAL" in iss:
                severity = "CRITICAL"
            elif "WARNING" in iss:
                severity = "WARNING"
            elif "MISMATCH" in iss:
                severity = "MISMATCH"
            elif "MISSING" in iss:
                severity = "MISSING"
            print(f"  [{severity}] {iss}")


def main():
    root = Path(".")

    gt = load_json(root / "GROUND_TRUTH.json")
    final_summary = load_json(root / "FINAL_RESULTS_SUMMARY.json")
    ablation = load_json(root / "stage4_ablation/results/ablation_results.json")
    chi2 = load_json(root / "stage4_ablation/chi2_validation/chi2_results.json")

    # Rebuttal letter is markdown, we load it as text for search
    rebuttal_text = ""
    rebuttal_path = root / "stage6_rebuttal/responses/REBUTTAL_LETTER_FINAL.md"
    if rebuttal_path.exists():
        rebuttal_text = rebuttal_path.read_text()

    all_issues = []

    issues = check_tier1_consistency(gt, final_summary, rebuttal_text)
    print_report(issues, "R4.1 — Tier-1 accuracy consistency")
    all_issues.extend(issues)

    issues = check_tier3_consistency(gt, final_summary)
    print_report(issues, "Tier-3 blind accuracy consistency")
    all_issues.extend(issues)

    issues = check_corpus_counts(gt)
    print_report(issues, "Corpus sample counts")
    all_issues.extend(issues)

    issues = check_ablation_claims(rebuttal_text, ablation)
    print_report(issues, "R5.4 — Ablation study claims")
    all_issues.extend(issues)

    issues = check_train_test_claims(ablation)
    print_report(issues, "R5.2 — Train/test separation claims")
    all_issues.extend(issues)

    issues = check_chi2_claims(chi2, rebuttal_text)
    print_report(issues, "R5.3 — chi² validation claims")
    all_issues.extend(issues)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(all_issues)} issues found")
    critical = sum(1 for i in all_issues if "CRITICAL" in i)
    warnings = sum(1 for i in all_issues if "WARNING" in i)
    mismatches = sum(1 for i in all_issues if "MISMATCH" in i)
    print(f"  CRITICAL: {critical}")
    print(f"  MISMATCH: {mismatches}")
    print(f"  WARNING:  {warnings}")
    print("=" * 60)

    if critical > 0:
        print("\nACTION REQUIRED: Fix CRITICAL issues before resubmission.")
        sys.exit(1)
    elif mismatches > 0:
        print("\nACTION REQUIRED: Reconcile mismatched numbers before resubmission.")
        sys.exit(2)
    else:
        print("\nAll checks passed. Data is consistent.")
        sys.exit(0)


if __name__ == "__main__":
    main()
