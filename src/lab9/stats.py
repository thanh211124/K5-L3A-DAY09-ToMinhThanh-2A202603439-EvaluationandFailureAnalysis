"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    cm = {POS: 0, "FP": 0, "FN": 0, "TN": 0}
    for h, j in zip(human, judge):
        if j == POS and h == POS:
            cm[POS] += 1
        elif j == POS:
            cm["FP"] += 1
        elif h == POS:
            cm["FN"] += 1
        else:
            cm["TN"] += 1
    return {"tp": cm[POS], "fp": cm["FP"], "fn": cm["FN"], "tn": cm["TN"]}


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    p = cm["tp"] / (cm["tp"] + cm["fp"]) if cm["tp"] + cm["fp"] else 0.0
    r = cm["tp"] / (cm["tp"] + cm["fn"]) if cm["tp"] + cm["fn"] else 0.0
    return p, r


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    n = len(human)
    if n == 0 or len(judge) != n:
        raise ValueError("sequences must be non-empty and same length")
    p_o = sum(1 for h, j in zip(human, judge) if h == j) / n
    mh = {v: 0 for v in set(human)}
    mj = {v: 0 for v in set(judge)}
    for h, j in zip(human, judge):
        mh[h] += 1
        mj[j] += 1
    p_e = sum(c / n * mj.get(v, 0) / n for v, c in mh.items())
    if p_e == 1:
        raise ValueError("kappa undefined: judge and human agree on a single constant value")
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1
    est = (observed_rate + specificity - 1) / denom
    return min(1.0, max(0.0, est))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    import numpy as np
    from scipy.stats import bootstrap

    av, bv = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if av.shape != bv.shape:
        raise ValueError("a and b must have the same shape")
    diff = av - bv
    if (diff == 0).all():
        return (0.0, 0.0, 0.0)
    res = bootstrap((av, bv), lambda x, y: np.mean(x - y), method="percentile", paired=True,
                    n_resamples=n_resamples, confidence_level=confidence,
                    vectorized=False, rng=np.random.default_rng(rng))
    lo, hi = res.confidence_interval.low, res.confidence_interval.high
    return (float(diff.mean()), float(lo), float(hi))


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    if k > n:
        raise ValueError("k > n")
    from math import comb
    return 1.0 - comb(n - c, k) / comb(n, k) if n - c >= k else 1.0


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    if k > n:
        raise ValueError("k > n")
    from math import comb
    return comb(c, k) / comb(n, k) if c >= k else 0.0
