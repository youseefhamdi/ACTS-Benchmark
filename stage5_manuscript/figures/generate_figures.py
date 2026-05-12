#!/usr/bin/env python3
"""Generate manuscript figures from real benchmark results."""

import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = Path("../../stage2_execution/results")
OUTPUT_DIR = Path(".")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_results(filename):
    with open(RESULTS_DIR / filename) as f:
        return json.load(f)


def figure1_accuracy_bars():
    """Fig 1: Multi-model accuracy across tiers (bar chart)."""
    models = {
        "gemma4_fixed.json": "Gemma 4 (31B)",
        "gptoss_all_tiers.json": "GPT-OSS (120B)",
        "nemotron_all_tiers.json": "Nemotron Super",
    }
    
    tiers = ["Tier-1\n(Meta)", "Tier-2\n(File)", "Tier-3\n(Blind)"]
    x = np.arange(len(tiers))
    width = 0.25
    colors = ['#2ecc71', '#3498db', '#e74c3c']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for i, (fn, name) in enumerate(models.items()):
        data = load_results(fn)
        from collections import defaultdict
        by_tier = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in data["results"]:
            by_tier[r["tier"]]["total"] += 1
            if r["correct"]:
                by_tier[r["tier"]]["correct"] += 1
        
        accs = []
        for tier in ["tier1", "tier2", "tier3"]:
            s = by_tier[tier]
            accs.append(s["correct"] / s["total"] * 100 if s["total"] > 0 else 0)
        
        offset = (i - 1) * width
        bars = ax.bar(x + offset, accs, width, label=name, color=colors[i], edgecolor='black', linewidth=0.5)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{height:.1f}%', ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title('ACTS v2 Pilot: Multi-Model Accuracy Across Metadata Tiers', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tiers, fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.set_ylim(0, 115)
    ax.axhline(y=100/7, color='gray', linestyle='--', alpha=0.5, label='Random baseline (14.3%)')
    ax.text(2.3, 100/7 + 2, 'Random\nbaseline', fontsize=8, color='gray')
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "figure1_accuracy_tiers.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {output_path}")


def figure2_confusion_matrix_nemotron():
    """Fig 2: Nemotron Tier-3 confusion matrix."""
    data = load_results("nemotron_all_tiers.json")
    
    ciphers = ["AES-128", "AES-256", "DES", "3DES", "ChaCha20", "RSA-2048", "ML-KEM-768"]
    n = len(ciphers)
    matrix = np.zeros((n, n), dtype=int)
    
    for r in data["results"]:
        if r["tier"] == "tier3":
            gt_idx = ciphers.index(r["ground_truth"])
            pred = r["predicted"]
            if pred in ciphers:
                pred_idx = ciphers.index(pred)
                matrix[gt_idx][pred_idx] = 1
    
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(matrix, cmap='YlGn', aspect='auto')
    
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(ciphers, rotation=45, ha='right', fontsize=9)
    ax.set_yticklabels(ciphers, fontsize=9)
    
    for i in range(n):
        for j in range(n):
            text = ax.text(j, i, matrix[i, j],
                          ha="center", va="center", color="black" if matrix[i, j] == 0 else "white",
                          fontsize=12, fontweight='bold')
    
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("Ground Truth", fontsize=11)
    ax.set_title("Nemotron Super: Tier-3 (Blind) Confusion Matrix\nn=7, Accuracy = 57.1%", 
                 fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "figure2_confusion_nemotron.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {output_path}")


def figure3_gap_comparison():
    """Fig 3: Metadata gap comparison across models."""
    models = {
        "gemma4_fixed.json": "Gemma 4 (31B)",
        "gptoss_all_tiers.json": "GPT-OSS (120B)",
        "nemotron_all_tiers.json": "Nemotron Super",
    }
    
    names = []
    gaps = []
    t3_accs = []
    
    for fn, name in models.items():
        data = load_results(fn)
        from collections import defaultdict
        by_tier = defaultdict(lambda: {"correct": 0, "total": 0})
        for r in data["results"]:
            by_tier[r["tier"]]["total"] += 1
            if r["correct"]:
                by_tier[r["tier"]]["correct"] += 1
        
        t1 = by_tier["tier1"]["correct"] / by_tier["tier1"]["total"]
        t3 = by_tier["tier3"]["correct"] / by_tier["tier3"]["total"]
        gap = (t1 - t3) * 100
        
        names.append(name)
        gaps.append(gap)
        t3_accs.append(t3 * 100)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Gap plot
    colors = ['#e74c3c', '#e67e22', '#f39c12']
    bars1 = ax1.barh(names, gaps, color=colors, edgecolor='black', linewidth=0.5)
    ax1.set_xlabel('Accuracy Gap (percentage points)', fontsize=11)
    ax1.set_title('Metadata Gap (T1 → T3)', fontsize=12, fontweight='bold')
    ax1.set_xlim(0, 100)
    for bar, gap in zip(bars1, gaps):
        ax1.text(gap + 1, bar.get_y() + bar.get_height()/2, f'{gap:.1f} pp',
                va='center', fontsize=10, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # Blind accuracy plot
    bars2 = ax2.barh(names, t3_accs, color=['#3498db', '#2ecc71', '#9b59b6'], edgecolor='black', linewidth=0.5)
    ax2.set_xlabel('Blind Accuracy (%)', fontsize=11)
    ax2.set_title('Tier-3 (Blind) Performance', fontsize=12, fontweight='bold')
    ax2.axvline(x=100/7, color='gray', linestyle='--', alpha=0.5)
    ax2.text(100/7 + 1, 0.5, 'Random (14.3%)', fontsize=9, color='gray')
    ax2.set_xlim(0, 65)
    for bar, acc in zip(bars2, t3_accs):
        ax2.text(acc + 1, bar.get_y() + bar.get_height()/2, f'{acc:.1f}%',
                va='center', fontsize=10, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "figure3_gap_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    figure1_accuracy_bars()
    figure2_confusion_matrix_nemotron()
    figure3_gap_comparison()
    print("\nAll figures generated successfully!")
