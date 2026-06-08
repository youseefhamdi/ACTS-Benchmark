#!/usr/bin/env python3
"""
Targeted v2 backfill: run ONLY missing (backend, tier, filename) cells.
Reads existing v2_final data to determine what's missing, then runs those cells.
"""
import json, os, sys, math, time, re
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import urllib.request, urllib.error

WORKSPACE = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS_DIR = WORKSPACE / "stage2_execution/results/live_sample_140_v2"
MANIFEST_PATH = WORKSPACE / "stage2_execution/results/live_sample_140_v2/manifest.json"
RESULTS_DIR = WORKSPACE / "stage2_execution/results"
LOG = WORKSPACE / "r3_progress.md"

OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def _load_or_key():
    env_path = Path("/home/elaref/.hermes/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts)==2 and parts[0]=="OPENROUTER_API_KEY": return parts[1]
    return os.environ.get("OPENROUTER_API_KEY","")

OR_KEY = _load_or_key()

BACKENDS = {
    "gemma4:31b-cloud":       {"type":"ollama","model_id":"gemma4:31b-cloud","delay":2.0,"max_tokens":300},
    "gpt-oss:120b-cloud":     {"type":"ollama","model_id":"gpt-oss:120b-cloud","delay":2.0,"max_tokens":300},
    "nemotron-3-super:cloud": {"type":"ollama","model_id":"nemotron-3-super:cloud","delay":3.0,"max_tokens":500},
    "openrouter/owl-alpha":   {"type":"openrouter","model_id":"openrouter/owl-alpha","delay":5.0,"max_tokens":300},
    "google/gemma-4-31b-it:free":{"type":"openrouter","model_id":"google/gemma-4-31b-it:free","delay":5.0,"max_tokens":300},
    "minimax-m3:cloud":       {"type":"ollama","model_id":"minimax-m3:cloud","delay":5.0,"max_tokens":4000},
}
THINKING_MODELS = {"minimax-m3:cloud"}

def entropy(data):
    if not data: return 0.0
    c=Counter(data);n=len(data)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

def chi2(data):
    if not data: return 0.0
    c=Counter(data);n=len(data);e=n/256.0
    return sum((c.get(i,0)-e)**2/e for i in range(256))

def hex_p(data,n): return data[:n].hex()

def normalize(raw, thinking=""):
    text=(raw if raw else thinking).upper().strip()
    for pat in ["AES-256","AES-128","ML-KEM-768","RSA-2048","CHACHA20","3DES","DES"]:
        if pat in text:
            m={"AES-256":"AES-256","AES-128":"AES-128","ML-KEM-768":"ML-KEM-768",
               "RSA-2048":"RSA-2048","CHACHA20":"ChaCha20","3DES":"3DES","DES":"DES"}
            return m.get(pat,pat)
    if "CHACHA" in text: return "ChaCha20"
    if "RSA" in text: return "RSA-2048"
    if "ML-KEM" in text: return "ML-KEM-768"
    if "AES" in text and "256" in text: return "AES-256"
    if "AES" in text and "128" in text: return "AES-128"
    if "TRIPLE" in text: return "3DES"
    if "DES" in text: return "DES"
    return "UNKNOWN"

def call_ollama(mid, prompt, max_tokens=300, timeout=180):
    payload=json.dumps({"model":mid,"prompt":prompt,"stream":False,"options":{"temperature":0.0,"num_predict":max_tokens}}).encode()
    req=urllib.request.Request(OLLAMA_URL,data=payload,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            d=json.loads(resp.read())
            return {"raw":d.get("response",""),"thinking":d.get("thinking",""),"error":""}
    except Exception as e: return {"raw":"","thinking":"","error":str(e)}

def call_or(mid, prompt, max_tokens=300, timeout=180):
    payload=json.dumps({"model":mid,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens,"temperature":0.0}).encode()
    req=urllib.request.Request(OPENROUTER_URL,data=payload,headers={"Content-Type":"application/json","Authorization":f"Bearer {OR_KEY}"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as resp:
            d=json.loads(resp.read())
            raw=d.get("choices",[{}])[0].get("message",{}).get("content","")
            reas=d.get("choices",[{}])[0].get("message",{}).get("reasoning","")
            return {"raw":raw,"thinking":reas,"error":""}
    except urllib.error.HTTPError as e:
        body=e.read().decode() if e.fp else ""
        return {"raw":"","thinking":"","error":f"HTTP {e.code}: {body[:200]}"}
    except Exception as e: return {"raw":"","thinking":"","error":str(e)}

def call_llm(b, prompt, timeout=180):
    cfg=BACKENDS[b]
    mt=cfg["max_tokens"]
    if cfg["type"]=="ollama": return call_ollama(cfg["model_id"],prompt,max_tokens=mt,timeout=timeout)
    else: return call_or(cfg["model_id"],prompt,max_tokens=mt,timeout=timeout)

# ── Prompt builders ──
def build_t1(sample, fs):
    return (f"You are a cryptographic analysis expert.\n\nGiven the following KNOWN metadata:\n"
            f"- Cipher family: {sample['cipher_family']}\n- Mode: {sample.get('mode','unknown')}\n"
            f"- Implementation: {sample['implementation']}\n\n"
            f"Confirm the cipher family name from this list: "
            f"AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t2(sample, fs):
    return (f"You are a cryptographic forensics expert.\n\n"
            f"A ciphertext file is named: \"{sample['filename']}\"\n"
            f"File size: {fs} bytes\n\n"
            f"Based on the filename and typical naming conventions, what cipher family was likely used?\n\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t3(fs, ent, ch2, hp, variant="stats_only"):
    base=(f"You are a cryptographic forensics expert.\n\n"
          f"Analyze the following ciphertext sample and identify the cipher family.\n\n"
          f"Ciphertext Statistics:\n- File size: {fs} bytes\n- Shannon entropy: {ent:.4f} bits/byte\n"
          f"- Chi-square statistic: {ch2:.2f}\n- Hex prefix (first 32 bytes): {hp}\n")
    if variant=="tier3_raw": base+="\nAdditional raw hex preview (first 256 bytes):\n[RAW_HEX]\n"
    base+=("\nCipher family options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
           "Rules:\n1. Provide ONLY the cipher name from the list above\n"
           "2. No explanation needed\n3. If uncertain, provide your best guess\n\n"
           "Your answer (cipher name only):")
    return base

def build_t4a(fs, ent, ch2, hp, ba):
    return (f"You are a cryptographic forensics expert with access to computed features.\n\n"
            f"Ciphertext Features:\n- File size: {fs} bytes\n- Shannon entropy: {ent:.4f} bits/byte\n"
            f"- Chi-square statistic: {ch2:.2f}\n"
            f"- Block alignment: {'16-byte aligned' if ba else 'not 16-byte aligned'}\n"
            f"- Byte frequency: {'uniform' if ent>7.9 else 'non-uniform'}\n"
            f"- Hex prefix (first 32 bytes): {hp}\n\n"
            f"Based on these computed features, identify the cipher family.\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"Your answer (cipher name only):")

def build_t5(fs, ent, ch2):
    return (f"You are a cryptographic forensics expert.\n\n"
            f"Analyze the following ciphertext sample step by step.\n\n"
            f"Ciphertext Statistics:\n- File size: {fs} bytes\n"
            f"- Shannon entropy: {ent:.4f} bits/byte\n- Chi-square statistic: {ch2:.2f}\n\n"
            f"Think through the cryptanalytic reasoning:\n"
            f"1. What does the file size suggest about block vs stream cipher?\n"
            f"2. What does the entropy suggest about cipher strength?\n"
            f"3. What does the chi-square suggest about byte distribution?\n"
            f"4. Which cipher family best matches these characteristics?\n\n"
            f"Options: AES-128, AES-256, DES, 3DES, ChaCha20, RSA-2048, ML-KEM-768\n\n"
            f"After your reasoning, provide ONLY the cipher family name on the last line.\n"
            f"Your answer (cipher name only):")

# ── Checkpoint ──
def load_completed():
    done=set()
    for path in [RESULTS_DIR/"live_matrix_full_v2_final.jsonl",RESULTS_DIR/"tier4a_full_v2_final.jsonl",RESULTS_DIR/"tier5_live_full_v2_final.jsonl"]:
        if not path.exists(): continue
        with open(path) as f:
            for line in f:
                try:
                    r=json.loads(line)
                    if not r.get("error") and r.get("parsed_prediction","UNKNOWN")!="UNKNOWN":
                        v=r.get("variant") or "standard"
                        done.add((r["backend"],r["tier"],r["filename"],v))
                except: pass
    return done

def append_result(path, record):
    with open(path,"a") as f: f.write(json.dumps(record,default=str)+"\n")

def main():
    backends_arg = sys.argv[1:] if len(sys.argv)>1 else list(BACKENDS.keys())
    
    with open(MANIFEST_PATH) as f: manifest=json.load(f)
    samples=manifest["samples"]
    sample_map={s["filename"]:s for s in samples}
    all_filenames=set(sample_map.keys())
    
    completed=load_completed()
    print(f"Loaded {len(completed)} completed cells")
    
    # Determine missing cells
    missing_cells=[]  # (backend, tier, variant, filename)
    for b in backends_arg:
        for tier in ["tier1","tier2","tier3_raw","tier4a","tier5"]:
            actual_tier="tier3" if tier=="tier3_raw" else tier
            for fn in all_filenames:
                v="tier3_raw" if tier=="tier3_raw" else "standard"
                key=(b,actual_tier,fn,v)
                if key not in completed:
                    missing_cells.append((b,tier,fn))
    
    print(f"Missing cells to run: {len(missing_cells)}")
    
    total_calls=0
    total_errors=0
    t_start=time.time()
    
    for bi,(b,tier,fn) in enumerate(missing_cells):
        sample=sample_map[fn]
        fp=CORPUS_DIR/fn
        if not fp.exists(): continue
        data=fp.read_bytes()
        fs=len(data)
        ent=entropy(data)
        ch2_stat=chi2(data)
        hp=hex_p(data,32)
        ba=(fs%16==0)
        
        variant="standard"
        actual_tier=tier
        if tier=="tier3_raw":
            variant="tier3_raw"
            actual_tier="tier3"
            raw_hex=data[:256].hex()
            prompt=build_t3(fs,ent,ch2_stat,hp,"tier3_raw").replace("[RAW_HEX]",raw_hex)
        elif tier=="tier1": prompt=build_t1(sample,fs)
        elif tier=="tier2": prompt=build_t2(sample,fs)
        elif tier=="tier3": prompt=build_t3(fs,ent,ch2_stat,hp,"stats_only")
        elif tier=="tier4a": prompt=build_t4a(fs,ent,ch2_stat,hp,ba)
        elif tier=="tier5": prompt=build_t5(fs,ent,ch2_stat)
        else: continue
        
        # Retry with backoff
        max_retries=5
        result=None
        latency=0.0
        for attempt in range(max_retries):
            t_call=time.time()
            result=call_llm(b,prompt,timeout=180)
            latency=time.time()-t_call
            if result.get("error"):
                err=result["error"]
                if "429" in err:
                    wait=min((2**attempt)*5+1,60)
                    print(f"  ⏳ 429, retry in {wait}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    continue
                elif attempt<max_retries-1:
                    time.sleep(3)
                    continue
            if result.get("parsed","UNKNOWN")!="UNKNOWN" or not result.get("error"):
                break
        
        if result is None: result={"raw":"","thinking":"","error":"No result"}
        parsed=normalize(result["raw"],result["thinking"])
        gt=sample["cipher_family"]
        correct=(parsed==gt) if parsed!="UNKNOWN" else False
        has_error=bool(result.get("error")) or parsed=="UNKNOWN"
        
        record={
            "backend":b,"model_id":BACKENDS[b]["model_id"],
            "tier":actual_tier,"variant":variant,"filename":fn,
            "ground_truth":gt,"implementation":sample["implementation"],
            "file_size":fs,"parsed_prediction":parsed,"correct":correct,
            "latency_s":round(latency,3),"timestamp":datetime.now(timezone.utc).isoformat(),
            "error":result.get("error",""),
        }
        
        # Write to appropriate file
        if actual_tier in ["tier1","tier2","tier3"]:
            jsonl_path=RESULTS_DIR/"live_matrix_full_v2_final.jsonl"
        elif actual_tier=="tier4a":
            jsonl_path=RESULTS_DIR/"tier4a_full_v2_final.jsonl"
        elif actual_tier=="tier5":
            jsonl_path=RESULTS_DIR/"tier5_live_full_v2_final.jsonl"
        else: continue
        
        append_result(jsonl_path,record)
        
        if not has_error:
            completed.add((b,actual_tier,fn,variant))
            total_calls+=1
        else:
            total_errors+=1
        
        sym="✅" if correct else ("❌" if not has_error else "⚠️")
        print(f"  {sym} {b[:30]:30s} {actual_tier:8s} {fn[:25]:25s} GT={gt:10s} PRED={parsed:12s} ({latency:.1f}s)")
        
        delay=BACKENDS[b]["delay"]
        time.sleep(delay)
        
        # Progress report every 50 calls
        if (bi+1)%50==0:
            elapsed=time.time()-t_start
            print(f"\n--- Progress: {bi+1}/{len(missing_cells)} cells, {total_calls} good, {total_errors} errors, {elapsed:.0f}s ---\n")
    
    elapsed=time.time()-t_start
    print(f"\n{'='*70}")
    print(f"DONE: {total_calls} new good records in {elapsed:.0f}s | {total_errors} errors")

if __name__=="__main__":
    main()
