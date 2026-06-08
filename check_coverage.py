import json, subprocess
from pathlib import Path

base = Path('/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc/stage2_execution/results')
manifest_path = base / 'live_sample_140_v2/manifest.json'
with open(manifest_path) as f:
    manifest = json.load(f)
all_files = set(s['filename'] for s in manifest['samples'])

BACKENDS = ['gemma4:31b-cloud','gpt-oss:120b-cloud','nemotron-3-super:cloud',
            'minimax-m3:cloud','openrouter/owl-alpha']
TIERS = ['tier1','tier2','tier3','tier4a','tier5']

existing = {}
for p in ['live_matrix_full_v2_final.jsonl','tier4a_full_v2_final.jsonl',
          'tier5_live_full_v2_final.jsonl','minimax_m3_all_v2_final.jsonl',
          'owl_alpha_t4a_t5_v2_final.jsonl']:
    fp = base / p
    if not fp.exists(): continue
    with open(fp) as f:
        for line in f:
            try:
                r = json.loads(line)
                if not r.get('error') and r.get('parsed_prediction','UNKNOWN')!='UNKNOWN':
                    key = (r['backend'], r['tier'])
                    if key not in existing: existing[key] = set()
                    existing[key].add(r['filename'])
            except: pass

print('=== Coverage Grid ===')
print(f'{"Backend":<40s} {"tier1":>8s} {"tier2":>8s} {"tier3":>8s} {"tier4a":>8s} {"tier5":>8s}')
print('-' * 80)
incomplete = []
for b in BACKENDS:
    row = f'{b:<40s}'
    for t in TIERS:
        have = existing.get((b,t), set())
        n = len(have)
        if n == 140: row += f' {"OK":>8s}'
        elif n > 0: row += f' {str(n)+"/140":>8s}'; incomplete.append((b,t,n,140-n))
        else: row += f' {"0":>8s}'; incomplete.append((b,t,0,140))
    print(row)

print(f'\nIncomplete: {len(incomplete)} cells')
for b,t,n,miss in sorted(incomplete, key=lambda x: -x[3]):
    print(f'  {b:40s} {t}: {n}/140 good, {miss} missing')

print('\nProcesses:')
for pid,name in [(12821,'minimax-m3'),(13618,'owl-alpha T4A+T5')]:
    r = subprocess.run(['ps','-p',str(pid),'-o','pid,etime','--no-headers'], capture_output=True, text=True)
    print(f'  PID {pid} ({name}): {r.stdout.strip() or "DEAD"}')
