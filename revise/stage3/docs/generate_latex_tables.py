#!/usr/bin/env python3
"""Generate LaTeX tables for manuscript from real benchmark results."""

import json
import math
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("../stage2_execution/results")
OUTPUT_DIR = Path(".")
OUTPUT_DIR.mkdir(exist_ok=True)

def wilson_ci(k, n, confidence=0.95):
    """Wilson score interval."""
    if n == 0:
        return (0.0, 0.0)
    z = 1.96  # 95%
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / denom
    return (centre - margin, centre + margin)


def load_results(filename):
    with open(RESULTS_DIR / filename) as f:
        return json.load(f)


def generate_table1_overview():
    """Table 1: Multi-model accuracy across tiers."""
    models = {
        "gemma4_fixed.json": "Gemma 4 (31B)",
        "gptoss_all_tiers.json": "GPT-OSS (120B)",
        "nemotron_all_tiers.json": "Nemotron Super",
    }
    
    rows = []
    tier_sums = {"tier1": [], "tier2": [], "tier3": []}
    
    for fn, name in models.items():
        data = load_results(fn)
        by_tier = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in data["results"]:
            by_tier[r["tier"]]["total"] += 1
            if r["correct"]:
                by_tier[r["tier"]]["correct"] += 1
        
        t1 = by_tier["tier1"]
        t2 = by_tier["tier2"]
        t3 = by_tier["tier3"]
        
        ci1 = wilson_ci(t1["correct"], t1["total"])
        ci2 = wilson_ci(t2["correct"], t2["total"])
        ci3 = wilson_ci(t3["correct"], t3["total"])
        
        tier_sums["tier1"].append(t1["correct"] / t1["total"])
        tier_sums["tier2"].append(t2["correct"] / t2["total"])
        tier_sums["tier3"].append(t3["correct"] / t3["total"])
        
        rows.append(
            f"{name} & "
            f"{t1['correct']}/{t1['total']} ({t1['correct']/t1['total']:.1%}) & "
            f"{t2['correct']}/{t2['total']} ({t2['correct']/t2['total']:.1%}) & "
            f"{t3['correct']}/{t3['total']} ({t3['correct']/t3['total']:.1%}) & "
            f"{(t1['correct']/t1['total'] - t3['correct']/t3['total']):.1%} \\\\"
        )
    
    # Average row
    avg_t1 = sum(tier_sums["tier1"]) / len(tier_sums["tier1"])
    avg_t2 = sum(tier_sums["tier2"]) / len(tier_sums["tier2"])
    avg_t3 = sum(tier_sums["tier3"]) / len(tier_sums["tier3"])
    rows.append(
        r"\midrule" + "\n" +
        f"\\textbf{{Average}} & "
        f"{avg_t1:.1%} & {avg_t2:.1%} & {avg_t3:.1%} & {avg_t1 - avg_t3:.1%} \\\\"
    )
    
    latex = r"""\begin{table}[htbp]
\centering
\caption{Multi-model cipher identification accuracy across metadata tiers (n=7 per model per tier)}
\label{tab:real_multimodel}
\begin{tabular}{lccc@{\hspace{1em}}c}
\toprule
\textbf{Model} & \textbf{Tier-1 (Meta)} & \textbf{Tier-2 (File)} & \textbf{Tier-3 (Blind)} & \textbf{Gap} \\
\midrule
"""
    latex += "\n".join(rows)
    latex += r"""
\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_table2_wilson():
    """Table 2: Wilson 95\% CI for blind accuracy."""
    data = load_results("merged_real_results.json")
    
    latex = r"""\begin{table}[htbp]
\centering
\caption{Wilson 95\% confidence intervals for blind (Tier-3) accuracy}
\label{tab:wilson_ci}
\begin{tabular}{lcccc}
\toprule
\textbf{Model} & \textbf{$n$} & \textbf{Correct} & \textbf{Accuracy} & \textbf{Wilson 95\% CI} \\
\midrule
"""
    
    for model, stats in data["by_model"].items():
        t3 = stats["tier3"]
        n = t3["total"]
        k = t3["correct"]
        acc = t3["accuracy"]
        lower, upper = wilson_ci(k, n)
        
        display = {
            "gemma4:31b-cloud": "Gemma 4",
            "gpt-oss:120b-cloud": "GPT-OSS",
            "nemotron-3-super:cloud": "Nemotron"
        }[model]
        
        latex += f"{display} & {n} & {k}/{n} & {acc:.1%} & [{lower:.3f}, {upper:.3f}] \\\\\n"
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_table3_mcnemar():
    """Table 3: McNemar test results."""
    models = {
        "gemma4_fixed.json": "Gemma 4",
        "gptoss_all_tiers.json": "GPT-OSS",
        "nemotron_all_tiers.json": "Nemotron",
    }
    
    latex = r"""\begin{table}[htbp]
\centering
\caption{McNemar test for Tier-1 vs Tier-3 prediction difference}
\label{tab:mcnemar}
\begin{tabular}{lcccc}
\toprule
\textbf{Model} & \textbf{Discordant (T1$\checkmark$,T3$\times$)} & \textbf{Discordant (T1$\times$,T3$\checkmark$)} & \textbf{$\chi^2$} & \textbf{$p$-value} \\
\midrule
"""
    
    for fn, name in models.items():
        data = load_results(fn)
        # Build paired results
        results_by_file = defaultdict(dict)
        for r in data["results"]:
            key = r["filename"]
            results_by_file[key][r["tier"]] = r["correct"]
        
        b = 0  # T1 correct, T3 wrong
        c = 0  # T1 wrong, T3 correct
        
        for file_results in results_by_file.values():
            t1_ok = file_results.get("tier1", False)
            t3_ok = file_results.get("tier3", False)
            if t1_ok and not t3_ok:
                b += 1
            elif not t1_ok and t3_ok:
                c += 1
        
        if b + c > 0:
            chi2 = (b - c) ** 2 / (b + c)
            # p-value approximation
            from math import exp
            p = exp(-chi2 / 2)
        else:
            chi2 = 0
            p = 1.0
        
        latex += f"{name} & {b} & {c} & {chi2:.2f} & {p:.4f} \\\\\n"
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    return latex


if __name__ == "__main__":
    tables = {
        "table1_overview.tex": generate_table1_overview(),
        "table2_wilson.tex": generate_table2_wilson(),
        "table3_mcnemar.tex": generate_table3_mcnemar(),
    }
    
    for filename, content in tables.items():
        output_path = OUTPUT_DIR / filename
        with open(output_path, "w") as f:
            f.write(content)
        print(f"Generated: {output_path}")
