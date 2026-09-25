from __future__ import annotations
import math
from typing import Iterable

def _relevance(retrieved: list[str], relevant: set[str]) -> list[int]:
    return [1 if x in relevant else 0 for x in retrieved]

def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant: return 1.0 if not retrieved else 0.0
    return sum(_relevance(retrieved[:k], relevant)) / len(relevant)

def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0: return 0.0
    return sum(_relevance(retrieved[:k], relevant)) / k

def hit_rate_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(x in relevant for x in retrieved[:k]) else 0.0

def mrr(retrieved: list[str], relevant: set[str]) -> float:
    for i, item in enumerate(retrieved, 1):
        if item in relevant: return 1.0 / i
    return 0.0

def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    gains = _relevance(retrieved[:k], relevant)
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    ideal_n = min(k, len(relevant))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_n))
    return dcg / idcg if idcg else 1.0

def retrieval_metrics(rankings: Iterable[list[str]], relevant: Iterable[set[str]], k: int = 5) -> dict[str, float]:
    pairs=list(zip(rankings, relevant))
    if not pairs: return {f"recall@{k}":0.0,f"precision@{k}":0.0,f"hit_rate@{k}":0.0,"mrr":0.0,f"ndcg@{k}":0.0}
    return {
        f"recall@{k}": round(sum(recall_at_k(r,g,k) for r,g in pairs)/len(pairs),4),
        f"precision@{k}": round(sum(precision_at_k(r,g,k) for r,g in pairs)/len(pairs),4),
        f"hit_rate@{k}": round(sum(hit_rate_at_k(r,g,k) for r,g in pairs)/len(pairs),4),
        "mrr": round(sum(mrr(r,g) for r,g in pairs)/len(pairs),4),
        f"ndcg@{k}": round(sum(ndcg_at_k(r,g,k) for r,g in pairs)/len(pairs),4),
    }

def regression_delta(current: dict[str,float], baseline: dict[str,float], *, threshold: float = 0.05) -> dict:
    deltas={}
    regressions=[]
    for key, old in baseline.items():
        if key not in current: continue
        delta=round(float(current[key])-float(old),4)
        deltas[key]=delta
        if delta <= -abs(threshold): regressions.append({"metric":key,"baseline":old,"current":current[key],"delta":delta})
    return {"deltas":deltas,"regressions":regressions,"has_regression":bool(regressions)}
