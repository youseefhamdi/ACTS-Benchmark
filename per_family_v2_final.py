#!/usr/bin/env python3
"""
ACTS v2 FINAL — Per-family accuracy, confusion matrices, default guess rates.
Reads from live_matrix_full_v2_final.jsonl, tier4a_full_v2_final.jsonl, tier5_live_full_v2_final.jsonl.
Errors EXCLUDED. Only 20/family/backend expected.
"""

import json, math
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
RESULTS_DIR = WORKSPACE / "stage2_execution/results"
OUT_DIR = WORKSPACE / "stage7_assembly/scaled_results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CANONICAL = ['3des','aes-128','aes-256','chacha20','des','ml-kem-768','rsa-2048']

def load_good_records(jsonl_path):
    if not jsonl_path.exists():
        return []
    records = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("error") or r.get("parsed_prediction","UNKNOWN") == "UNKNOWN":
                    continue
                records.append(r)
            except:
                pass
    return records

def wilson_ci(k, n, z=1.96):
    if n == 0: return [0.0, 0.0]
    p = k / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    s = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5) / d
    return [round(max(0.0, c-s)*100, 1), round(min(1.0, c+s)*100, 1)]

def normalize(label):
    m = {'3DES':'3des','3des':'3des','AES-128':'aes-128','aes-128':'aes-128',
         'AES-256':'aes-256','aes-256':'aes-256','DES':'des','des':'des',
         'CHACHA20':'chacha20','ChaCha20':'chacha20','chacha20':'chacha20',
         'RSA-2048':'rsa-2048','rsa-2048':'rsa-2048',
         'ML-KEM-768':'ml-kem-768','ml-kem-768':'ml-kem-768'}
    return m.get(label, label.lower())

main = load_good_records(RESULTS_DIR / "live_matrix_full_v2_final.jsonl")
t4a = load_good_records(RESULTS_DIR / "tier4a_full_v2_final.jsonl")
t5 = load_good_records(RESULTS_DIR / "tier5_live_full_v2_final.jsonl")
all_records = main + t4a + t5

print(f"Loaded: {len(all_records)} good records")

BACKENDS = ['gemma4:31b-cloud','gpt-oss:120b-cloud','nemotron-3-super:cloud',
            'minimax-m3:cloud','openrouter/owl-alpha','google/gemma-4-31b-it:free']

result = {"generated_at": datetime.now(timezone.utc).isoformat(), "tiers": {}}

for tier_key in ["tier1","tier2","tier3","tier4a","tier5"]:
    tier_recs = [r for r in all_records if r.get("tier") == tier_key]
    if not tier_recs:
        continue
    
    result["tiers"][tier_key] = {"pooled": {}, "per_backend": {}, "confusion": {}, "default_guess": {}}
    
    # Normalize ground truth labels
    for r in tier_recs:
        r["gt"] = normalize(r.get("ground_truth",""))
    
    # Pooled per-family
    for fam in CANONICAL:
        fam_recs = [r for r in tier_recs if r["gt"] == fam]
        if not fam_recs:
            continue
        k = sum(1 for r in fam_recs if r.get("correct"))
        n = len(fam_recs)
        result["tiers"][tier_key]["pooled"][fam] = {
            "k": k, "n": n, "accuracy": round(k/n*100, 1), "ci": wilson_ci(k, n)
        }
    
    # Per-backend
    for b in BACKENDS:
        b_recs = [r for r in tier_recs if r.get("backend") == b]
        if not b_recs:
            continue
        
        # Per-family
        result["tiers"][tier_key]["per_backend"][b] = {}
        for fam in CANONICAL:
            fam_recs = [r for r in b_recs if r["gt"] == fam]
            if not fam_recs:
                continue
            k = sum(1 for r in fam_recs if r.get("correct"))
            n = len(fam_recs)
            result["tiers"][tier_key]["per_backend"][b][fam] = {
                "k": k, "n": n, "accuracy": round(k/n*100, 1), "ci": wilson_ci(k, n)
            }
        
        # Confusion matrix
        matrix = {}
        for r in b_recs:
            gt = r["gt"]
            pred = normalize(r.get("parsed_prediction",""))
            if gt not in matrix:
                matrix[gt] = {}
            matrix[gt][pred] = matrix[gt].get(pred, 0) + 1
        result["tiers"][tier_key]["confusion"][b] = matrix
        
        # Default guess
        preds = Counter(normalize(r.get("parsed_prediction","")) for r in b_recs)
        total = len(b_recs)
        modal = preds.most_common(1)[0] if preds else ("none", 0)
        result["tiers"][tier_key]["default_guess"][b] = {
            "total": total,
            "modal": modal[0],
            "modal_rate": round(modal[1]/total*100, 1) if total else 0,
            "distribution": {k: {"count": v, "rate": round(v/total*100, 1)} for k, v in preds.most_common()}
        }

# Save
out = OUT_DIR / "per_family_accuracy_v2_final.json"
with open(out, "w") as f:
    json.dump(result, f, indent=2)
print(f"Saved: {out}")

# Print summary
print("\n=== Per-Family Accuracy (Pooled) ===")
for tier_key in ["tier1","tier2","tier3","tier4a","tier5"]:
    if tier_key not in result["tiers"]:
        continue
    print(f"\n{tier_key}:")
    for fam in CANONICAL:
        if fam in result["tiers"][tier_key]["pooled"]:
            d = result["tiers"][tier_key]["pooled"][fam]
            print(f"  {fam:<14} {d['k']:>3}/{d['n']:<3} {d['accuracy']:>6.1f}% [{d['ci'][0]:.1f}%, {d['ci'][1]:.1f}%]")

print("\n=== T3 Per-Backend ===")
if "tier3" in result["tiers"]:
    for b in BACKENDS:
        if b in result["tiers"]["tier3"]["per_backend"]:
            fams = result["tiers"]["tier3"]["per_backend"][b]
            accs = [f"{fam}={d['accuracy']}%" for fam, d in sorted(fams.items())]
            print(f"  {b}: {', '.join(accs)}")
