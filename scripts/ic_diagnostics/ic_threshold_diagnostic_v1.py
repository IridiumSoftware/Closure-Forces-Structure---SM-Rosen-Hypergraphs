"""
Threshold sensitivity diagnostic for Q₄₈ and Q₁₀₂ IC-independence.

Purpose: determine whether degenerate vertex counts are threshold artifacts
(near-coincidences at 0.999) or genuine algebraic degeneracies (fidelity = 1.0).

Method:
1. For each of 200 seeds, build Q₄₈ and Q₁₀₂ at thresholds [0.999, 0.99999, 1-1e-12]
2. For degenerate cases at 0.999, find the actual fidelities between merged clusters
3. Check if tightening recovers the canonical vertex count
4. Flag any merges at fidelity > 1 - 1e-12 (potential algebraic coincidences)

Mathematical conventions:
  - Fidelity: |⟨ψ_a|ψ_b⟩|² ∈ [0, 1]
  - Clustering: vertices a, b merge iff fidelity(a, b) > threshold
  - The "true" quotient is by exact gauge orbits (fidelity = 1.0 exactly)
  - Any merge at fidelity < 1.0 is a threshold artifact
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connes_q48_build_v1 import build_q48, haar_C3, fidelity
from q102_build_v1 import build_c_closed_quotient, complete_ternary


def make_ics(seed):
    rng = np.random.default_rng(seed)
    return {v: haar_C3(rng) for v in range(6)}


def find_near_merges(Q, lo_threshold, hi_threshold):
    """Find pairs of clusters in quotient Q whose fidelity is in (lo, hi].

    These are pairs that would merge at lo_threshold but not at hi_threshold.
    Returns list of fidelities.
    """
    n = Q['n_cl']
    near_fids = []
    for i in range(n):
        for j in range(i + 1, n):
            f = fidelity(Q['q_psi'][i], Q['q_psi'][j])
            if f > lo_threshold:
                near_fids.append(f)
    return near_fids


def main():
    print("=" * 70)
    print("  THRESHOLD SENSITIVITY DIAGNOSTIC")
    print("=" * 70)

    n_test = 200
    rng = np.random.default_rng(42)
    seeds = [int(rng.integers(0, 2**31)) for _ in range(n_test)]

    thresholds = [0.999, 0.99999, 1 - 1e-12]
    thresh_labels = ["0.999", "0.99999", "1-1e-12"]

    # ── Q₄₈ ──
    print(f"\n── Q₄₈: {n_test} seeds, {len(thresholds)} thresholds ──\n")

    q48_results = {t: [] for t in thresholds}
    q48_near_fids = []  # fidelities of pairs that merge at 0.999

    for i, seed in enumerate(seeds):
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{n_test}")
        psi = make_ics(seed)
        for t in thresholds:
            Q = build_q48(psi, depth=5, threshold=t)
            q48_results[t].append(Q['n_cl'])

        # For degenerate cases at 0.999, find the merged-pair fidelities
        # by building at tight threshold and looking for near-coincidences
        if q48_results[thresholds[0]][-1] != 48:
            Q_tight = build_q48(psi, depth=5, threshold=1 - 1e-12)
            near = find_near_merges(Q_tight, 0.999, 1.0)
            q48_near_fids.extend(near)

    print(f"\n  Q₄₈ success rates:")
    for t, label in zip(thresholds, thresh_labels):
        counts = q48_results[t]
        n48 = sum(1 for c in counts if c == 48)
        unique = sorted(set(counts))
        dist = {u: sum(1 for c in counts if c == u) for u in unique}
        print(f"    threshold={label}: {n48}/{n_test} ({100*n48/n_test:.1f}%)"
              f"  dist={dict(sorted(dist.items()))}")

    if q48_near_fids:
        fids = sorted(q48_near_fids, reverse=True)
        print(f"\n  Merged-pair fidelities (degenerate cases at 0.999):")
        print(f"    count: {len(fids)}")
        print(f"    max:   {fids[0]:.15f}")
        print(f"    min:   {fids[-1]:.15f}")
        print(f"    mean:  {np.mean(fids):.15f}")
        bins = [
            ("0.999–0.9999", 0.999, 0.9999),
            ("0.9999–0.99999", 0.9999, 0.99999),
            ("0.99999–0.999999", 0.99999, 0.999999),
            ("0.999999–(1-1e-10)", 0.999999, 1 - 1e-10),
            ("(1-1e-10)–(1-1e-12)", 1 - 1e-10, 1 - 1e-12),
            (">(1-1e-12)", 1 - 1e-12, 1.0 + 1e-15),
        ]
        for label, lo, hi in bins:
            n_in = sum(1 for f in fids if lo < f <= hi)
            if n_in > 0:
                print(f"    {label}: {n_in}")
        n_algebraic = sum(1 for f in fids if f > 1 - 1e-12)
        print(f"    ★ Potential algebraic (>{1-1e-12:.1e}): {n_algebraic}")

    # ── Q₁₀₂ ──
    print(f"\n── Q₁₀₂: {n_test} seeds, {len(thresholds)} thresholds ──\n")

    q102_results = {t: [] for t in thresholds}
    q102_near_fids = []

    for i, seed in enumerate(seeds):
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{n_test}")
        psi = make_ics(seed)
        for t in thresholds:
            Q = build_c_closed_quotient(complete_ternary(6), psi, depth=4, threshold=t)
            q102_results[t].append(Q['n_cl'])

        if q102_results[thresholds[0]][-1] != 102:
            Q_tight = build_c_closed_quotient(
                complete_ternary(6), psi, depth=4, threshold=1 - 1e-12)
            near = find_near_merges(Q_tight, 0.999, 1.0)
            q102_near_fids.extend(near)

    print(f"\n  Q₁₀₂ success rates:")
    for t, label in zip(thresholds, thresh_labels):
        counts = q102_results[t]
        n102 = sum(1 for c in q102_counts if c == 102) if False else \
               sum(1 for c in counts if c == 102)
        unique = sorted(set(counts))
        dist = {u: sum(1 for c in counts if c == u) for u in unique}
        print(f"    threshold={label}: {n102}/{n_test} ({100*n102/n_test:.1f}%)"
              f"  dist={dict(sorted(dist.items()))}")

    if q102_near_fids:
        fids = sorted(q102_near_fids, reverse=True)
        print(f"\n  Merged-pair fidelities (degenerate cases at 0.999):")
        print(f"    count: {len(fids)}")
        print(f"    max:   {fids[0]:.15f}")
        print(f"    min:   {fids[-1]:.15f}")
        print(f"    mean:  {np.mean(fids):.15f}")
        bins = [
            ("0.999–0.9999", 0.999, 0.9999),
            ("0.9999–0.99999", 0.9999, 0.99999),
            ("0.99999–0.999999", 0.99999, 0.999999),
            ("0.999999–(1-1e-10)", 0.999999, 1 - 1e-10),
            ("(1-1e-10)–(1-1e-12)", 1 - 1e-10, 1 - 1e-12),
            (">(1-1e-12)", 1 - 1e-12, 1.0 + 1e-15),
        ]
        for label, lo, hi in bins:
            n_in = sum(1 for f in fids if lo < f <= hi)
            if n_in > 0:
                print(f"    {label}: {n_in}")
        n_algebraic = sum(1 for f in fids if f > 1 - 1e-12)
        print(f"    ★ Potential algebraic (>{1-1e-12:.1e}): {n_algebraic}")

    # ── Summary ──
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")

    q48_tight = q48_results[1 - 1e-12]
    q102_tight = q102_results[1 - 1e-12]
    n48_tight = sum(1 for c in q48_tight if c == 48)
    n102_tight = sum(1 for c in q102_tight if c == 102)

    print(f"\n  Q₄₈  at 1-1e-12: {n48_tight}/{n_test} give 48")
    print(f"  Q₁₀₂ at 1-1e-12: {n102_tight}/{n_test} give 102")

    if n48_tight == n_test and n102_tight == n_test:
        print(f"\n  ★ ALL {n_test} seeds give canonical counts at tight threshold.")
        print(f"    CONCLUSION: degenerate cases are threshold artifacts.")
        print(f"    The quotient is algebraically unique for Haar-generic ICs.")
        print(f"    The fidelity threshold is a numerical convenience, not")
        print(f"    part of the mathematical definition.")
    elif n48_tight < n_test or n102_tight < n_test:
        q48_fail = n_test - n48_tight
        q102_fail = n_test - n102_tight
        print(f"\n  Q₄₈ failures at tight: {q48_fail}")
        print(f"  Q₁₀₂ failures at tight: {q102_fail}")
        if q48_fail == 0 and q102_fail > 0:
            print(f"  Q₄₈ resolved. Q₁₀₂ may have algebraic degeneracies.")
        else:
            print(f"  ⚠ Potential algebraic coincidences. Check fidelity distribution.")

    print()


if __name__ == "__main__":
    main()
