#!/usr/bin/env python3
"""Worker: gemma4:31b-cloud on v2b corpus. 5 tiers x 140 files. Checkpoint/resume."""
import json, os, time, math
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import urllib.request, urllib.error

WS = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS = WS / "stage1_data/corpus_ultra"
MANIFEST = WS / "stage2_execution/results/live_sample_140_v2/manifest.json"
SHARD = WS / "stage2_execution/results/gemma4_v2b_final.jsonl"
MODEL = "gemma4:31b-cloud"
OLLAMA = "http://localhost:11434/api/generate"
BE = "gemma4:31b-cloud"

ALIASES = {"aes-128":"AES-128","aes128":"AES-128","aes-256":"AES-256","aes256":"AES-256",
    "3des":"3DES","tripledes":"3DES","des":"DES","chacha20":"ChaCha20","chacha":"ChaCha20",
    "rsa-2048":"RSA-2048","rsa2048":"RSA-2048","rsa":"RSA-2048",
    "ml-kem-768":"ML-KEM-768","mlkem768":"ML-KEM-768","ml-kem":"ML-KEM-768","ml":"ML-KEM-768","aes":"AES-128"}

def norm(r):
    if not r: return "UNKNOWN"
    for ln in r.split("\n"):
        ls=ln.strip()
        if any(m in ls.upper() for m in ["FINAL_ANSWER","FINAL DETERMINATION","PREDICTED_CIPHER","FINAL_PREDICTION","CLASSIFICATION","CIPHER:","STEP 5","ANSWER:"]):
            if ":" in ls: ls=ls.split(":",1)[1].strip()
            t=ls.lower().strip(" `*_-'")
            for a,c in ALIASES.items():
                if a in t: return c
    for a,c in ALIASES.items():
        if a in r.lower(): return c
    return "UNKNOWN"

def H(d):
    if not d: return 0.0
    n=len(d);c=Counter(d)
    return -sum((x/n)*math.log2(x/n) for x in c.values())

def C2(d):
    if not d: return 0.0
    n=len(d);e=n/256.0;c=Counter(d)
    return sum(((c.get(b,0)-e)**2/e) for b in range(256))

def call(prompt):
    p=json.dumps({"model":MODEL,"prompt":prompt,"stream":False,"options":{"temperature":0.2,"num_ctx":8192}}).encode()
    req=urllib.request.Request(OLLAMA,data=p,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=180) as r:
            d=json.loads(r.read().decode())
            return {"raw":d.get("response",""),"ec":d.get("eval_count",0) or 0,"pc":d.get("prompt_eval_count",0) or 0,"ed":d.get("eval_duration",0),"ok":True}
    except Exception as e:
        return {"error":str(e),"raw":"","ok":False}

def load_done():
    d=set()
    if not SHARD.exists(): return d
    with open(SHARD) as f:
        for l in f:
            try: r=json.loads(l); d.add((r["tier"],r["filename"]))
            except: pass
    return d

def save(rec):
    with open(SHARD,"a") as f: f.write(json.dumps(rec,default=str)+"\n")

with open(MANIFEST) as f: samples=json.load(f)["samples"]
D=load_done(); total=0; t0=time.time()
print(f"[gemma4] checkpoint={len(D)}")

for tier in ["tier1","tier2","tier3","tier4a","tier5"]:
    for s in samples:
        fn=s["filename"]
        if (tier,fn) in D: continue
        fp=CORPUS/fn
        if not fp.exists(): continue
        data=fp.read_bytes(); fs=len(data); ent=H(data); c2=C2(data); hp=data[:32].hex()
        tb=", ".join(f"0x{b:02x}({n})" for b,n in Counter(data).most_common(5))
        ba="; ".join(f"{'div' if fs%bs==0 else f'NOT div {bs} r{fs%bs}'}" for bs in [8,16,32,64])
        if tier=="tier1":
            prompt=f"Crypto expert. Metadata: fn={fn} size={fs}B cipher={s['cipher_family']} impl={s['implementation']} pad={s.get('padding_mode','?')} keybits={s.get('key_size_bits',0)}\n\nCipher family name ONLY:"
        elif tier=="tier2":
            prompt=f"Crypto expert. FILENAME: {fn} SIZE: {fs} bytes\n\nCipher family? POSSIBLE: AES-128,AES-256,3DES,DES,ChaCha20,RSA-2048,ML-KEM-768\n\nONLY name:"
        elif tier=="tier3":
            prompt=f"Forensic cryptographer. FEATURES: size={fs}B entropy={ent:.4f} chi2={c2:.1f} hex={hp}\n\nCipher? STEP1: entropy STEP2: structural STEP3: final name.\nPOSSIBLE: AES-128,AES-256,3DES,DES,ChaCha20,RSA-2048,ML-KEM-768"
        elif tier=="tier4a":
            prompt=f"Forensic cryptographer. FEATURES: size={fs}B entropy={ent:.4f} chi2={c2:.1f} topbytes={tb} hex={hp} blocks={ba}\n\nCipher family name ONLY:"
        elif tier=="tier5":
            prompt=f"Forensic cryptographer. FEATURES: size={fs}B entropy={ent:.4f} chi2={c2:.1f} topbytes={tb} hex={hp} blocks={ba}\n\nPOSSIBLE: AES-128,AES-256,3DES,DES,ChaCha20,RSA-2048,ML-KEM-768\n\nSTEP1: ENTROPY:\n[analyze]\nSTEP2: STRUCTURAL:\n[analyze]\nSTEP3: STATISTICAL:\n[analyze]\nSTEP4: ELIMINATION:\n[which+why]\nSTEP5: FINAL:\n[ONE name]\nCONFIDENCE: [0-100%]\nBEGIN:"
        else: continue

        for att in range(5):
            t1=time.time(); res=call(prompt); lat=time.time()-t1
            if not res.get("ok"):
                err=res.get("error","")
                if "429" in err:
                    w=min((2**att)*20+5,300)
                    print(f"  429 wait {w}s (attempt {att+1}/5)")
                    time.sleep(w)
                elif att<4: time.sleep(10)
                else:
                    rec={"backend":BE,"model_id":MODEL,"tier":tier,"variant":None,"filename":fn,
                         "ground_truth":s["cipher_family"],"implementation":s["implementation"],"file_size":fs,
                         "parsed_prediction":"UNKNOWN","correct":False,"latency_s":round(lat,3),"latency_api_s":0,
                         "prompt_tokens":0,"completion_tokens":0,
                         "timestamp":datetime.now(timezone.utc).isoformat(),"error":err}
                    save(rec); D.add((tier,fn)); total+=1
                    print(f"  SKIP {tier} {fn}: {err[:60]}")
                    break
            else:
                pred=norm(res.get("raw","")); ok=(pred==s["cipher_family"])
                ed=res.get("ed",0) or 0; la=ed/1e9 if ed>1e9 else lat
                rec={"backend":BE,"model_id":MODEL,"tier":tier,"variant":None,"filename":fn,
                     "ground_truth":s["cipher_family"],"implementation":s["implementation"],"file_size":fs,
                     "parsed_prediction":pred,"correct":ok,"latency_s":round(lat,3),"latency_api_s":round(la,3),
                     "prompt_tokens":res.get("pc",0),"completion_tokens":res.get("ec",0),
                     "timestamp":datetime.now(timezone.utc).isoformat(),"error":""}
                save(rec); D.add((tier,fn)); total+=1
                print(f"  {'OK' if ok else '  '} {tier} {fn}: GT={s['cipher_family']} PRED={pred} ({lat:.1f}s)")
                break
        time.sleep(3)

print(f"\n[gemma4] DONE {total} calls {time.time()-t0:.0f}s")
