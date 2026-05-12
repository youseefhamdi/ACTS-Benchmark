#!/usr/bin/env python3
"""Tier-6 on Expanded Corpus (700 files)"""
import json, csv, math
from pathlib import Path
from collections import Counter
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score
import numpy as np

manifest = json.load(open('stage1_data/corpus_expanded/manifest.json'))
corpus_dir = Path('stage1_data/corpus_expanded')

family_map = {"AES-128": "aes128", "AES-256": "aes256", "3DES": "3des", "DES": "des", "ChaCha20": "chacha20", "RSA-2048": "rsa2048", "ML-KEM-768": "mlkem768"}
label_map = {v: i for i, v in enumerate(family_map.values())}

def compute_entropy(data):
    n = len(data)
    if n == 0: return 0.0
    counts = Counter(data)
    return -sum((c/n)*math.log2(c/n) for c in counts.values())

def ngram_entropy(data, n=2):
    if len(data) < n: return 0.0
    grams = [tuple(data[i:i+n]) for i in range(len(data)-n+1)]
    counts = Counter(grams)
    total = len(grams)
    return -sum((c/total)*math.log2(c/total) for c in counts.values())

def block_entropy_std(data, bs=16):
    if len(data) < bs: return 0.0
    ents = []
    for i in range(0, len(data)-bs+1, bs):
        block = data[i:i+bs]
        counts = Counter(block)
        n = len(block)
        ent = -sum((c/n)*math.log2(c/n) for c in counts.values())
        ents.append(ent)
    return np.std(ents) if ents else 0.0

def compute_chi2(data):
    expected = len(data)/256.0
    counts = Counter(data)
    return sum(((counts.get(b,0)-expected)**2/expected) for b in range(256))

def serial_correlation(data):
    n = len(data)
    if n < 2: return 0.0
    s0, s1, s2 = sum(data), sum(b*b for b in data), sum(data[i]*data[i+1] for i in range(n-1))
    s3 = s0*s0/n
    denom = s1 - s3
    if denom == 0: return -1.0/(n-1)
    return (n*s2 - s0*s0) / (n*denom)

def extract_features(filepath):
    data = filepath.read_bytes()
    n = len(data)
    ent = compute_entropy(data)
    return [
        n,  # file_size (already the strongest feature!)
        n % 8, n % 16, n % 64,
        ent,
        ngram_entropy(data, 2),
        ngram_entropy(data, 3),
        block_entropy_std(data, 8),
        block_entropy_std(data, 16),
        compute_chi2(data),
        serial_correlation(data),
        max(Counter(data).values())/n if n else 0,
        sum(1 for b in data if b == 0)/n,
        sum(1 for b in data if b == 255)/n,
    ]

# Build dataset
X, y, labels = [], [], []
print("Extracting features from 700 files...")
for s in manifest:
    filepath = corpus_dir / s["filename"] / "ciphertext.bin"
    if not filepath.exists():
        filepath = corpus_dir / s["filename"]
    features = extract_features(filepath)
    X.append(features)
    true_label = family_map[s["cipher_family"]]
    y.append(label_map[true_label])
    labels.append(true_label)

X, y = np.array(X), np.array(y)

# Feature names for importance
feature_names = [
    "file_size", "mod8", "mod16", "mod64",
    "entropy", "bigram_ent", "trigram_ent",
    "block_std_8", "block_std_16", "chi2",
    "serial_corr", "max_byte_freq", "zero_ratio", "ff_ratio"
]

# 5-fold CV
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
models = {
    "RandomForest": RandomForestClassifier(n_estimators=200, random_state=42),
    "LogisticRegression": LogisticRegression(max_iter=10000, random_state=42),
    "LinearSVM": SVC(kernel='linear', probability=False, random_state=42),
}

print("\n" + "="*60)
print("TIER-6 CLASSICAL ML — EXPANDED CORPUS (700 files)")
print("="*60)

all_results = {}
for mname, model in models.items():
    accs = []
    fold_preds, fold_true = [], []
    feature_importances = None
    for train_idx, test_idx in skf.split(X, y):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        accs.append(accuracy_score(y_test, preds))
        fold_preds.extend(preds)
        fold_true.extend(y_test)
        if hasattr(model, 'feature_importances_'):
            if feature_importances is None:
                feature_importances = model.feature_importances_
            else:
                feature_importances += model.feature_importances_
    
    mean_acc = np.mean(accs)
    all_results[mname] = {"mean_cv_accuracy": float(mean_acc), "fold_accuracies": [float(a) for a in accs]}
    print(f"\n{mname}: {mean_acc:.1%} (per-fold: {[f'{a:.1%}' for a in accs]})")
    
    if feature_importances is not None and mname == "RandomForest":
        feature_importances /= 5
        print("\n  Feature Importance (Random Forest):")
        for name, imp in sorted(zip(feature_names, feature_importances), key=lambda x: -x[1])[:8]:
            print(f"    {name}: {imp:.4f}")
    
    # Per-class accuracy for Random Forest
    if mname == "RandomForest":
        class_correct = Counter()
        class_total = Counter()
        idx2label = {v: k for k, v in label_map.items()}
        for p, t in zip(fold_preds, fold_true):
            class_total[idx2label[t]] += 1
            if p == t:
                class_correct[idx2label[t]] += 1
        print("\n  Per-class accuracy:")
        for fam in ["rsa2048", "mlkem768", "aes128", "aes256", "3des", "des", "chacha20"]:
            c, t = class_correct[fam], class_total[fam]
            print(f"    {fam}: {c}/{t} = {c/t:.0%}" if t > 0 else f"    {fam}: N/A")

json.dump(all_results, open('stage2_execution/results/tier6_expanded_results.json', 'w'), indent=2)
print("\n" + "="*60)
print("Saved: stage2_execution/results/tier6_expanded_results.json")
print("="*60)
