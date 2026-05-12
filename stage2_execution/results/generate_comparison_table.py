#!/usr/bin/env python3
"""Generate LaTeX and Markdown comparison tables from real benchmark results."""

import json
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path(__file__).parent

MODELS = {
    "gemma4_fixed.json": "Gemma 4 (31B)",
    "gptoss_all_tiers.json": "GPT-OSS (120B)",
    "nemotron_all_tiers.json": "Nemotron Super",
}

def extract_accuracy(filepath):
    with open(filepath) as f:
        data = json.load(f)
    
    results = data["results"]
    
    by_tier = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in results:
        tier = r["tier"]
        by_tier[tier]["total"] += 1
        if r["correct"]:
            by_tier[tier]["correct"] += 1
    
    accs = {}
    for tier in ["tier1", "tier2", "tier3"]:
        stats = by_tier[tier]
        accs[tier] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
    
    return accs


def generate_markdown():
    rows = []
    all_tiers = {"tier1": [], "tier2": [], "tier3": []}
    
    for filename, display_name in MODELS.items():
        filepath = RESULTS_DIR / filename
        if not filepath.exists():
            continue
        accs = extract_accuracy(filepath)
        gap = (accs["tier1"] - accs["tier3"]) * 100
        rows.append({
            "model": display_name,
            "tier1": accs["tier1"] * 100,
            "tier2": accs["tier2"] * 100,
            "tier3": accs["tier3"] * 100,
            "gap": gap
        })
        for tier in ["tier1", "tier2", "tier3"]:
            all_tiers[tier].append(accs[tier])
    
    # Add average row
    if rows:
        rows.append({
            "model": "**Average**",
            "tier1": sum(all_tiers["tier1"]) / len(all_tiers["tier1"]) * 100,
            "tier2": sum(all_tiers["tier2"]) / len(all_tiers["tier2"]) * 100,
            "tier3": sum(all_tiers["tier3"]) / len(all_tiers["tier3"]) * 100,
            "gap": (sum(all_tiers["tier1"]) - sum(all_tiers["tier3"])) / len(all_tiers["tier3"]) * 100
        })
    
    md = "# Real Benchmark Results: Multi-Model Comparison\n\n"
    md += "| Model | Tier-1 (Meta) | Tier-2 (File) | Tier-3 (Blind) | Gap (T1→T3) |\n"
    md += "|-------|---------------|---------------|----------------|-------------|\n"
    
    for row in rows:
        md += f"| {row['model']} | {row['tier1']:.1f}% | {row['tier2']:.1f}% | {row['tier3']:.1f}% | {row['gap']:.1f} pp |\n"
    
    return md


def generate_latex():
    rows = []
    all_tiers = {"tier1": [], "tier2": [], "tier3": []}
    
    for filename, display_name in MODELS.items():
        filepath = RESULTS_DIR / filename
        if not filepath.exists():
            continue
        accs = extract_accuracy(filepath)
        gap = (accs["tier1"] - accs["tier3"]) * 100
        rows.append((
            display_name,
            f"{accs['tier1']*100:.1f}\\%",
            f"{accs['tier2']*100:.1f}\\%",
            f"{accs['tier3']*100:.1f}\\%",
            f"{gap:.1f} pp"
        ))
        for tier in ["tier1", "tier2", "tier3"]:
            all_tiers[tier].append(accs[tier])
    
    if rows:
        rows.append((
            "\\textbf{Average}",
            f"{sum(all_tiers['tier1'])/len(all_tiers['tier1'])*100:.1f}\\%",
            f"{sum(all_tiers['tier2'])/len(all_tiers['tier2'])*100:.1f}\\%",
            f"{sum(all_tiers['tier3'])/len(all_tiers['tier3'])*100:.1f}\\%",
            f"{(sum(all_tiers['tier1'])-sum(all_tiers['tier3']))/len(all_tiers['tier3'])*100:.1f} pp"
        ))
    
    latex = r"""\begin{table}[htbp]
\centering
\caption{Real multi-model benchmark results across metadata tiers (n=7 per model per tier)}
\label{tab:real_results}
\begin{tabular}{lcccc}
\toprule
\textbf{Model} & \textbf{Tier-1} & \textbf{Tier-2} & \textbf{Tier-3} & \textbf{Gap} \\
 & \textbf{(Meta)} & \textbf{(File)} & \textbf{(Blind)} & \textbf{T1$\\rightarrow$T3} \\
\midrule
"""
    for row in rows:
        latex += f"{' & '.join(row)} \\\\\n"
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    return latex


def generate_confusion_matrix():
    """Generate confusion matrix data for the best performing blind model (nemotron)."""
    filepath = RESULTS_DIR / "nemotron_all_tiers.json"
    if not filepath.exists():
        return "No nemotron data found."
    
    with open(filepath) as f:
        data = json.load(f)
    
    # Collect tier3 only
    tier3_results = [r for r in data["results"] if r["tier"] == "tier3"]
    
    ciphers = ["AES-128", "AES-256", "DES", "3DES", "ChaCha20", "RSA-2048", "ML-KEM-768"]
    
    matrix = {gt: {pred: 0 for pred in ciphers} for gt in ciphers}
    
    for r in tier3_results:
        gt = r["ground_truth"]
        pred = r["predicted"]
        if pred in ciphers:
            matrix[gt][pred] += 1
        else:
            matrix[gt]["UNKNOWN"] = matrix[gt].get("UNKNOWN", 0) + 1
    
    # Generate markdown table
    md = "# Nemotron-3 Tier-3 (Blind) Confusion Matrix\n\n"
    md += "| Ground Truth → Predicted | " + " | ".join(ciphers) + " |\n"
    md += "|" + "-" * 25 + "|" + "|".join(["-" * 10 for _ in ciphers]) + "|\n"
    
    for gt in ciphers:
        row = [gt]
        for pred in ciphers:
            val = matrix[gt].get(pred, 0)
            marker = "**1**" if val > 0 else "0"
            row.append(marker)
        md += "| " + " | ".join(row) + " |\n"
    
    return md


if __name__ == "__main__":
    print(generate_markdown())
    print("\n" + "=" * 70 + "\n")
    print(generate_latex())
    print("\n" + "=" * 70 + "\n")
    print(generate_confusion_matrix())
