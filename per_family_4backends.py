#!/usr/bin/env python3
"""Per-family breakdown, confusion matrices, default-guess rates — 4 backends, clean labels."""
import json, math
from pathlib import Path
from collections import Counter, defaultdict

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")

ALLOWED = {"gemma4:31b-cloud","gpt-oss:120b-cloud","nemotron-3-super:cloud","openrouter/owl-alpha"}
SHARDS = ["live_matrix_full_v2_final.jsonl","tier4a_full_v2_final.jsonl",
          "tier5_live_full_v2_final.jsonl","owl_alpha_t4a_t5_v2_final.jsonl"]

# Load
records = []
seen = {}
for shard in SHARDS:
    p = RESULTS_DIR / shard
    if not p.exists(): continue
    with open(p) as f:
        for line in f:
            try: r = json.loads(line)
            except: continue
            if r.get("backend") not in ALLOWED: continue
            if r.get("error") and r["error"] not in ("",None): continue
            if r.get("parsed_prediction","UNKNOWN") == "UNKNOWN": continue
            key = (r["backend"],r["tier"],r["filename"],r.get("variant") or "standard")
            if key not in seen or r.get("timestamp","") > seen[key].get("timestamp",""):
                seen[key] = r
records = list(seen.values())

backends = sorted(ALLOWED)
tiers = ["tier1","tier2","tier3","tier4a","tier5"]
families = ["3DES","AES-128","AES-256","ChaCha20","DES","ML-KEM-768","RSA-2048"]

def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    s=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/d
    return (max(0.0,c-s),min(1.0,c+s))

# Label normalization map
LABEL_MAP = {"3DES":"3des","AES-128":"aes-128","AES-256":"aes-256","ChaCha20":"chacha20","DES":"des","ML-KEM-768":"ml-kem-768","RSA-2048":"rsa-2048"}
def norm(label): return LABEL_MAP.get(label, label.lower())

# ── Per-family table (T3 blind) ──
lines = []
lines.append("## 6. Per-Family Breakdown (Tier-3 Blind, 20 files/family/backend)\n")
lines.append("| Backend | Family (normalized) | k/N | Acc | 95% CI |")
lines.append("|---------|-------------------|-----|-----|--------|")
for b in backends:
    for fam in families:
        subset = [r for r in records if r["backend"]==b and r["tier"]=="tier3" and r["ground_truth"]==fam]
        if not subset: continue
        k = sum(1 for r in subset if r.get("correct"))
        n = len(subset)
        lo,hi = wilson(k,n)
        nf = norm(fam)
        lines.append(f"| {b} | {nf} | {k}/{n} | {k/n:.1%} | [{lo:.1%}, {hi:.1%}] |")
    lines.append("| | | | | |")

lines.append("")

# ── Confusion matrices (T3 pooled) ──
lines.append("## 7. Confusion Matrix — Tier-3 Pooled (4 backends)\n")
all_preds = sorted(set(r.get("parsed_prediction","?") for r in records if r["tier"]=="tier3"))
lines.append("| GT \\ PRED |" + "".join(f" {norm(p):>10s} |" for p in all_preds))
lines.append("|------------|" + "------------|" * len(all_preds))
for fam in families:
    row = f"| {norm(fam):>10s} |"
    for pred in all_preds:
        cnt = sum(1 for r in records if r["tier"]=="tier3" and r["ground_truth"]==fam and r.get("parsed_prediction")==pred)
        row += f" {cnt:>10d} |"
    lines.append(row)
lines.append("")

# ── Per-backend confusion matrices (T3) ──
lines.append("## 8. Confusion Matrices — Tier-3 Per Backend\n")
for b in backends:
    lines.append(f"\n### {b}\n")
    b_preds = sorted(set(r.get("parsed_prediction","?") for r in records if r["backend"]==b and r["tier"]=="tier3"))
    lines.append("| GT \\ PRED |" + "".join(f" {norm(p):>10s} |" for p in b_preds))
    lines.append("|------------|" + "------------|" * len(b_preds))
    for fam in families:
        row = f"| {norm(fam):>10s} |"
        for pred in b_preds:
            cnt = sum(1 for r in records if r["backend"]==b and r["tier"]=="tier3" and r["ground_truth"]==fam and r.get("parsed_prediction")==pred)
            row += f" {cnt:>10d} |"
        lines.append(row)
    lines.append("")

# ── Default-guess rates (T3) ──
lines.append("## 9. Default-Guess Rates (Tier-3)\n")
lines.append("| Backend | Top Guess | Rate | 2nd Guess | Rate | 3rd Guess | Rate |")
lines.append("|---------|-----------|------|-----------|------|-----------|------|")
for b in backends:
    subset = [r for r in records if r["backend"]==b and r["tier"]=="tier3"]
    if not subset: continue
    n = len(subset)
    preds = Counter(r.get("parsed_prediction","?") for r in subset)
    top3 = preds.most_common(3)
    row = f"| {b} |"
    for pred, cnt in top3:
        row += f" {norm(pred)} | {cnt/n:.1%} |"
    for _ in range(3-len(top3)):
        row += " — | — |"
    lines.append(row)
lines.append("")

md = "\n".join(lines)

# Append to stats MD
stats_md_path = RESULTS_DIR / "unified_v2_final_stats.md"
with open(stats_md_path, "a") as f:
    f.write("\n\n" + md)

print(f"Appended to {stats_md_path}")
print("\n" + md[:2000])
