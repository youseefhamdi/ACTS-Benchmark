import json
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results")

# Load ALL v2_final shards EXCEPT minimax archive
SHARDS = [
    "live_matrix_full_v2_final.jsonl",
    "tier4a_full_v2_final.jsonl",
    "tier5_live_full_v2_final.jsonl",
    "owl_alpha_t4a_t5_v2_final.jsonl",
]

records = []
seen = {}
for shard in SHARDS:
    p = RESULTS_DIR / shard
    if not p.exists():
        print(f"  WARNING: {shard} not found")
        continue
    with open(p) as f:
        for line in f:
            try:
                r = json.loads(line)
            except:
                continue
            if r.get("backend") == "minimax-m3:cloud":
                continue  # EXCLUDE
            if r.get("error") and r["error"] not in ("", None):
                continue
            if r.get("parsed_prediction", "UNKNOWN") == "UNKNOWN":
                continue
            key = (r.get("backend",""), r.get("tier",""), r.get("filename",""), r.get("variant") or "standard")
            if key not in seen or r.get("timestamp","") > seen[key].get("timestamp",""):
                seen[key] = r

records = list(seen.values())
backends = sorted(set(r["backend"] for r in records))
tiers = sorted(set(r["tier"] for r in records))

print(f"Total records (4 backends): {len(records)}")
print(f"Backends: {backends}")
print()

# Per-backend coverage
print("=== Coverage (4 backends) ===")
for b in backends:
    row = f"{b:<40s}"
    for t in tiers:
        have = set(r["filename"] for r in records if r["backend"]==b and r["tier"]==t)
        n = len(have)
        if n >= 140:
            row += f"  OK({n})"
        else:
            row += f"  {n}/140"
    print(row)

# Check for missing files per (backend, tier)
print("\n=== Missing Files Check ===")
manifest_path = RESULTS_DIR / "live_sample_140_v2/manifest.json"
with open(manifest_path) as f:
    manifest = json.load(f)
all_files = set(s["filename"] for s in manifest["samples"])

for b in backends:
    for t in tiers:
        have = set(r["filename"] for r in records if r["backend"]==b and r["tier"]==t)
        missing = all_files - have
        if missing:
            print(f"  {b} {t}: {len(have)}/140 good, {len(missing)} missing: {sorted(missing)[:3]}...")
        else:
            print(f"  {b} {t}: COMPLETE ({len(have)})")
