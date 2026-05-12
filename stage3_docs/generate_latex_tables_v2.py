#!/usr/bin/env python3
"""Generate updated LaTeX tables from expanded corpus benchmark results."""

import json
import math
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("../stage2_execution/results")
OUTPUT_DIR = Path(".")

def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denom
    margin = z * math.sqrt((p*(1-p) + z*z/(4*n)) / n) / denom
    return (centre - margin, centre + margin)

# Load merged results
with open(RESULTS_DIR / "merged_corpus_results.json") as f:
    merged = json.load(f)

results = merged["results"]
by_model = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))
for r in results:
    by_model[r["model"]][r["tier"]]["total"] += 1
    if r["correct"]:
        by_model[r["model"]][r["tier"]]["correct"] += 1

# Table 1: Overview
latex1 = r"""\begin{table}[htbp]
\centering
\caption{Expanded multi-model cipher identification accuracy across metadata tiers. Gemma 4 and GPT-OSS: $n=14$ per tier. Nemotron: $n=7$ (T1/T2), $n=21$ (T3).}
\label{tab:corpus14_multimodel}
\begin{tabular}{lccc@{\hspace{1em}}c}
\toprule
\textbf{Model} & \textbf{Tier-1 (Meta)} & \textbf{Tier-2 (File)} & \textbf{Tier-3 (Blind)} & \textbf{Gap} \\
\midrule
"""

for model in ["gemma4:31b-cloud", "gpt-oss:120b-cloud", "nemotron-3-super:cloud"]:
    tiers = by_model[model]
    t1 = tiers.get("tier1", {"correct":0,"total":1})
    t2 = tiers.get("tier2", {"correct":0,"total":1})
    t3 = tiers.get("tier3", {"correct":0,"total":1})
    
    t1_acc = t1["correct"] / t1["total"] if t1["total"] > 0 else 0
    t2_acc = t2["correct"] / t2["total"] if t2["total"] > 0 else 0
    t3_acc = t3["correct"] / t3["total"] if t3["total"] > 0 else 0
    gap = t1_acc - t3_acc
    
    display = {"gemma4:31b-cloud": "Gemma 4 (31B)", "gpt-oss:120b-cloud": "GPT-OSS (120B)", "nemotron-3-super:cloud": "Nemotron Super"}[model]
    
    latex1 += f"{display} & {t1['correct']}/{t1['total']} ({t1_acc:.1%}) & {t2['correct']}/{t2['total']} ({t2_acc:.1%}) & {t3['correct']}/{t3['total']} ({t3_acc:.1%}) & {gap:.1%} \\\\\n"

# Average row
all_t1 = [by_model[m]["tier1"]["correct"]/by_model[m]["tier1"]["total"] for m in by_model if "tier1" in by_model[m]]
all_t2 = [by_model[m]["tier2"]["correct"]/by_model[m]["tier2"]["total"] for m in by_model if "tier2" in by_model[m]]
all_t3 = [by_model[m]["tier3"]["correct"]/by_model[m]["tier3"]["total"] for m in by_model if "tier3" in by_model[m]]

latex1 += r"\midrule" + "\n"
latex1 += f"\\textbf{{Average}} & {sum(all_t1)/len(all_t1):.1%} & {sum(all_t2)/len(all_t2):.1%} & {sum(all_t3)/len(all_t3):.1%} & {sum(all_t1)/len(all_t1)-sum(all_t3)/len(all_t3):.1%} \\\\\n"
latex1 += r"""\bottomrule
\end{tabular}
\end{table}
"""

with open(OUTPUT_DIR / "table1_overview_v2.tex", "w") as f:
    f.write(latex1)
print("Generated: table1_overview_v2.tex")

# Table 2: Wilson CI for T3
latex2 = r"""\begin{table}[htbp]
\centering
\caption{Wilson 95\% confidence intervals for blind (Tier-3) accuracy (expanded corpus)}
\label{tab:wilson_ci_v2}
\begin{tabular}{lcccc}
\toprule
\textbf{Model} & \textbf{$n$} & \textbf{Correct} & \textbf{Accuracy} & \textbf{Wilson 95\% CI} \\
\midrule
"""

for model in ["gemma4:31b-cloud", "gpt-oss:120b-cloud", "nemotron-3-super:cloud"]:
    t3 = by_model[model]["tier3"]
    n = t3["total"]
    k = t3["correct"]
    acc = k / n
    lower, upper = wilson_ci(k, n)
    display = {"gemma4:31b-cloud": "Gemma 4", "gpt-oss:120b-cloud": "GPT-OSS", "nemotron-3-super:cloud": "Nemotron"}[model]
    latex2 += f"{display} & {n} & {k}/{n} & {acc:.1%} & [{lower:.3f}, {upper:.3f}] \\\\\n"

latex2 += r"""\bottomrule
\end{tabular}
\end{table}
"""

with open(OUTPUT_DIR / "table2_wilson_v2.tex", "w") as f:
    f.write(latex2)
print("Generated: table2_wilson_v2.tex")

# Table 3: McNemar
latex3 = r"""\begin{table}[htbp]
\centering
\caption{McNemar test for Tier-1 vs Tier-3 prediction difference (expanded)}
\label{tab:mcnemar_v2}
\begin{tabular}{lcccc}
\toprule
\textbf{Model} & \textbf{Discordant (T1$\checkmark$,T3$\times$)} & \textbf{Discordant (T1$\times$,T3$\checkmark$)} & \textbf{$\chi^2$} & \textbf{$p$-value} \\
\midrule
"""

for model in ["gemma4:31b-cloud", "gpt-oss:120b-cloud", "nemotron-3-super:cloud"]:
    # Build paired results for files that exist in both tiers
    model_results = [r for r in results if r["model"] == model]
    by_file = defaultdict(dict)
    for r in model_results:
        by_file[r["filename"]][r["tier"]] = r["correct"]
    
    b = 0
    c = 0
    for file_tiers in by_file.values():
        t1_ok = file_tiers.get("tier1", False)
        t3_ok = file_tiers.get("tier3", False)
        if t1_ok and not t3_ok:
            b += 1
        elif not t1_ok and t3_ok:
            c += 1
    
    if b + c > 0:
        chi2 = (b - c) ** 2 / (b + c)
        p = math.exp(-chi2 / 2)
    else:
        chi2 = 0
        p = 1.0
    
    display = {"gemma4:31b-cloud": "Gemma 4", "gpt-oss:120b-cloud": "GPT-OSS", "nemotron-3-super:cloud": "Nemotron"}[model]
    latex3 += f"{display} & {b} & {c} & {chi2:.2f} & {p:.4f} \\\\\n"

latex3 += r"""\bottomrule
\end{tabular}
\end{table}
"""

with open(OUTPUT_DIR / "table3_mcnemar_v2.tex", "w") as f:
    f.write(latex3)
print("Generated: table3_mcnemar_v2.tex")
print("\nAll v2 LaTeX tables generated!")
