#!/usr/bin/env python3
"""Parallel Tier-1 + Tier-3 evaluator for v2b corpus. 4 backends run concurrently.
   Uses Ollama for gemma4/gpt-oss/nemotron and OpenRouter for owl-alpha.
   Checkpoint/resume: preserves existing (tier, filename) results.
"""
import json, os, time, math, threading
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import urllib.request, urllib.error

WS = Path("/home/elaref/.gidaai/workspaces/default/upgrade/acts_v2_poc")
CORPUS = WS / "stage1_data/corpus_ultra"
MANIFEST = WS / "stage2_execution/results/live_sample_140_v2/manifest.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIERS = ["tier1", "tier3"]

def _load_key():
    ep = Path("/home/elaref/.hermes/.env")
    if ep.exists():
        with open(ep) as f:
            for line in f:
                if "OPENROUTER_API_KEY" in line and not line.strip().startswith("#"):
                    p = line.strip().split("=", 1)
                    if len(p) == 2 and p[0] == "OPENROUTER_API_KEY":
                        k = p[1]
                        if k: return k
    return os.environ.get("OPENROUTER_API_KEY", "")

OR_KEY = _load_key()

BACKENDS = [
    # Ollama backends
    {"name": "gemma4:31b-cloud",      "model": "gemma4:31b-cloud",       "type": "ollama",
     "shard": WS/"stage2_execution/results/gemma4_v2b_t1t3.jsonl",      "delay": 2.0},
    {"name": "gpt-oss:120b-cloud",    "model": "gpt-oss:120b-cloud",     "type": "ollama",
     "shard": WS/"stage2_execution/results/gptoss_v2b_t1t3.jsonl",      "delay": 2.0},
    {"name": "nemotron-3-super:cloud","model": "nemotron-3-super:cloud", "type": "ollama",
     "shard": WS/"stage2_execution/results/nemotron_v2b_t1t3.jsonl",    "delay": 30.0},
    # OpenRouter backend
    # OpenRouter disabled — persistent 429 rate limits exhausted key capacity
    # {"name": "openrouter/owl-alpha",  "model": "openrouter/owl-alpha",   "type": "openrouter",
    #  "shard": WS/"stage2_execution/results/owlalpha_v2b_t1t3.jsonl",    "delay": 30.0},
]

ALIASES = {
    "aes-128":"AES-128","aes128":"AES-128","aes-256":"AES-256","aes256":"AES-256",
    "3des":"3DES","tripledes":"3DES","des":"DES",
    "chacha20":"ChaCha20","chacha":"ChaCha20",
    "rsa-2048":"RSA-2048","rsa2048":"RSA-2048","rsa":"RSA-2048",
    "ml-kem-768":"ML-KEM-768","mlkem768":"ML-KEM-768","ml-kem":"ML-KEM-768","ml":"ML-KEM-768","aes":"AES-128"
}

def norm(r):
    if not r: return "UNKNOWN"
    for ln in r.split("\n"):
        ls = ln.strip()
        if any(m in ls.upper() for m in ["FINAL_ANSWER","FINAL DETERMINATION","PREDICTED_CIPHER","FINAL_PREDICTION","CLASSIFICATION","CIPHER:","STEP 5","ANSWER:"]):
            if ":" in ls: ls = ls.split(":",1)[1].strip()
            t = ls.lower().strip(" `*_-'")
            for a,c in ALIASES.items():
                if a in t: return c
    for a,c in ALIASES.items():
        if a in r.lower(): return c
    return "UNKNOWN"

def calc_entropy(d):
    if not d: return 0.0
    n=len(d); c=Counter(d)
    return -sum((x/n)*math.log2(x/n) for x in c.values())

def calc_chi2(d):
    if not d: return 0.0
    n=len(d); e=n/256.0; c=Counter(d)
    return sum(((c.get(b,0)-e)**2/e) for b in range(256))

def call_ollama(model, prompt):
    payload = json.dumps({"model":model,"prompt":prompt,"stream":False,
                          "options":{"temperature":0.2,"num_ctx":8192}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())
            return {"raw": result.get("response",""), "ec": result.get("eval_count",0) or 0,
                    "pc": result.get("prompt_eval_count",0) or 0, "ok": True}
    except Exception as e:
        return {"error": str(e), "raw": "", "ok": False}

def call_openrouter(model, prompt):
    payload = json.dumps({"model":model,"messages":[{"role":"user","content":prompt}],
                          "temperature":0.2,"max_tokens":2048}).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=payload, headers={
        "Content-Type":"application/json","Authorization":f"Bearer {OR_KEY}",
        "HTTP-Referer":"https://gidaai.local","X-Title":"ACTS_v2_Benchmark"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode())
            ch = result.get("choices",[])
            u = result.get("usage",{})
            return {"raw": ch[0].get("message",{}).get("content","") if ch else "",
                    "ec": u.get("completion_tokens",0) or 0,
                    "pc": u.get("prompt_tokens",0) or 0, "ok": True}
    except Exception as e:
        return {"error": str(e), "raw": "", "ok": False}

def call_model(be, prompt):
    if be["type"] == "openrouter":
        return call_openrouter(be["model"], prompt)
    else:
        return call_ollama(be["model"], prompt)

def load_done(shard):
    d = set()
    if not shard.exists(): return d
    with open(shard) as f:
        for ln in f:
            try:
                r = json.loads(ln)
                d.add((r["tier"], r["filename"]))
            except: pass
    return d

def save_rec(shard, rec):
    with open(shard, "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")

def build_prompts(s, data):
    """Return (tier1_prompt, tier3_prompt) for a sample."""
    fs = len(data)
    ent = calc_entropy(data)
    c2 = calc_chi2(data)
    hp = data[:32].hex()
    t1 = (f"Crypto expert. Metadata: fn={s['filename']} size={fs}B cipher={s['cipher_family']} "
          f"impl={s['implementation']} pad={s.get('padding_mode','?')} keybits={s.get('key_size_bits',0)}"
          f"\n\nCipher family name ONLY:")
    t3 = (f"Forensic cryptographer. FEATURES: size={fs}B entropy={ent:.4f} chi2={c2:.1f} hex={hp}"
          f"\n\nCipher? STEP1: entropy STEP2: structural STEP3: final name."
          f"\nPOSSIBLE: AES-128,AES-256,3DES,DES,ChaCha20,RSA-2048,ML-KEM-768")
    return t1, t3

def run_backend(be, samples, lock, summaries):
    model = be["model"]
    shard = be["shard"]
    bname = be["name"]
    delay = be["delay"]
    done = load_done(shard)
    total = 0
    print(f"[{bname}] checkpoint={len(done)} model={model}")

    for tier in TIERS:
        for s in samples:
            fn = s["filename"]
            if (tier, fn) in done:
                continue
            fp = CORPUS / fn
            if not fp.exists():
                continue
            data = fp.read_bytes()
            t1_prompt, t3_prompt = build_prompts(s, data)
            prompt = t1_prompt if tier == "tier1" else t3_prompt

            for att in range(5):
                t_start = time.time()
                res = call_model(be, prompt)
                lat = time.time() - t_start
                if not res.get("ok"):
                    err = res.get("error", "")
                    if "429" in err:
                        w = min((2**att)*15+5, 120)
                        with lock:
                            print(f"  [{bname}] 429 wait {w}s (attempt {att+1}/5) {fn}")
                        time.sleep(w)
                    elif att < 4:
                        time.sleep(5)
                    else:
                        rec = {"backend": bname, "model_id": model, "tier": tier, "filename": fn,
                               "ground_truth": s["cipher_family"], "file_size": len(data),
                               "parsed_prediction": "UNKNOWN", "correct": False,
                               "latency_s": round(lat, 3), "prompt_tokens": 0, "completion_tokens": 0,
                               "timestamp": datetime.now(timezone.utc).isoformat(), "error": err}
                        save_rec(shard, rec); total += 1
                        with lock:
                            print(f"  [{bname}] SKIP {tier}/{fn}: {err[:60]}")
                        break
                else:
                    pred = norm(res.get("raw", ""))
                    ok = (pred == s["cipher_family"])
                    rec = {"backend": bname, "model_id": model, "tier": tier, "filename": fn,
                           "ground_truth": s["cipher_family"], "file_size": len(data),
                           "parsed_prediction": pred, "correct": ok,
                           "latency_s": round(lat, 3), "prompt_tokens": res.get("pc", 0),
                           "completion_tokens": res.get("ec", 0),
                           "timestamp": datetime.now(timezone.utc).isoformat(), "error": ""}
                    save_rec(shard, rec); total += 1
                    with lock:
                        tag = "OK" if ok else "  "
                        print(f"  [{bname}] {tag} {tier} {fn}: GT={s['cipher_family']} PRED={pred} ({lat:.1f}s)")
                    break
            time.sleep(delay)

    print(f"\n[{bname}] COMPLETE: {total} calls")
    # Update summary
    recs = []
    if shard.exists():
        with open(shard) as f:
            for ln in f:
                try: recs.append(json.loads(ln))
                except: pass
    summaries[bname] = {"total": total, "records": len(recs)}

def main():
    with open(MANIFEST) as f:
        samples = json.load(f)["samples"]
    print(f"Samples: {len(samples)} | Tiers: {TIERS} | Backends: {len(BACKENDS)}")
    print(f"Key present: {'YES' if OR_KEY else 'NO (owl-alpha will fail)'}")
    print()

    lock = threading.Lock()
    summaries = {}
    threads = []
    for be in BACKENDS:
        t = threading.Thread(target=run_backend, args=(be, samples, lock, summaries), daemon=False)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\n\n" + "="*60)
    print("FINAL RESULTS — v2b Corpus Tier-1 + Tier-3")
    print("="*60)
    grand_total = 0
    grand_correct = 0
    for be in BACKENDS:
        shard = be["shard"]
        if not shard.exists():
            print(f"\n{be['name']}: NO FILE"); continue
        recs = [json.loads(ln) for ln in open(shard) if ln.strip()]
        for tier in TIERS:
            t_recs = [r for r in recs if r.get("tier") == tier]
            n = len(t_recs); c = sum(1 for r in t_recs if r.get("correct"))
            pct = f"{c/n*100:.1f}%" if n else "N/A"
            print(f"  {be['name']:30s} {tier}: {c}/{n} = {pct}")
        t1 = [r for r in recs if r.get("tier") == "tier1"]
        t3 = [r for r in recs if r.get("tier") == "tier3"]
        n1 = len(t1); c1 = sum(1 for r in t1 if r.get("correct"))
        n3 = len(t3); c3 = sum(1 for r in t3 if r.get("correct"))
        print(f"  {be['name']:30s} T1={c1}/{n1}={c1/n1*100:.1f}%  T3={c3}/{n3}={c3/n3*100:.1f}%" if n1 and n3 else "")
        grand_total += n1 + n3
        grand_correct += c1 + c3
    print(f"\n  GRAND TOTAL: {grand_correct}/{grand_total} = {grand_correct/grand_total*100:.1f}%" if grand_total else "")
    print("="*60)

if __name__ == "__main__":
    main()
