#!/usr/bin/env python3
"""
g3_born_vacuum_v1.py — G3 Born-maximising sub-hypergraph on Q₂₄

Does the Born measure select a consistent "vacuum" on Q₂₄?

Key questions:
  1. Which hyperedges carry the most Born weight?
  2. Does the top-k sub-hypergraph consistently select the same vertices?
  3. Do shared-vertex correlations break within-tier Z₆?
  4. Is there a Born-maximising "vacuum" configuration?

Usage:
  python3 g3_born_vacuum_v1.py [--n_ic N] [--seed S] [--depth D]
"""

import numpy as np
import time
import argparse
from collections import defaultdict, Counter
from itertools import combinations

# Import core algebra from the tier-coupling script
from g3_tier_coupling_v1 import (
    cross_C3, normalize, compose_colour, haar_C3, born_weight,
    fidelity, build_Q24
)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: BORN LANDSCAPE ON Q₂₄
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_born_landscape(q_psi, q_tier, unique_he, tier_info, n_cl, ic_label=""):
    """Map the Born-weight landscape on Q₂₄ hyperedges."""
    print(f"\n{'─'*70}")
    print(f"  BORN LANDSCAPE ON Q₂₄ {ic_label}")
    print(f"{'─'*70}")

    # Compute mean Born weight per quotient hyperedge
    he_borns = {}  # (c1,c2,c3) → mean_bw
    he_cvs = {}    # (c1,c2,c3) → CV across instances
    for (c1, c2, c3), instances in unique_he.items():
        bws = [bw for d, bw in instances]
        mean_bw = np.mean(bws)
        cv = np.std(bws) / mean_bw * 100 if mean_bw > 1e-15 else 0
        he_borns[(c1, c2, c3)] = mean_bw
        he_cvs[(c1, c2, c3)] = cv

    bw_vals = np.array(list(he_borns.values()))
    cv_vals = np.array(list(he_cvs.values()))

    print(f"\n  {len(he_borns)} unique hyperedges")
    print(f"  Born weight: mean={np.mean(bw_vals):.4f}, "
          f"std={np.std(bw_vals):.4f}, "
          f"min={np.min(bw_vals):.4f}, max={np.max(bw_vals):.4f}")
    print(f"  CV across instances: mean={np.mean(cv_vals):.1f}%, "
          f"max={np.max(cv_vals):.1f}%")

    # Distribution: percentiles
    print(f"\n  Born weight percentiles:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"    {p}th: {np.percentile(bw_vals, p):.4f}")

    # Top 20 hyperedges
    sorted_he = sorted(he_borns.items(), key=lambda x: -x[1])
    print(f"\n  Top 20 hyperedges by Born weight:")
    print(f"  {'Rank':>4} | {'(pos1,pos2,pos3)':<20} | {'Tiers':<25} | {'μ':>8} | {'CV%':>5}")
    print(f"  {'─'*70}")
    for i, ((c1, c2, c3), bw) in enumerate(sorted_he[:20]):
        tiers = f"({q_tier[c1]},{q_tier[c2]},{q_tier[c3]})"
        cv = he_cvs[(c1, c2, c3)]
        print(f"  {i+1:>4} | ({c1:>2},{c2:>2},{c3:>2}){'':>11} | {tiers:<25} | {bw:>8.4f} | {cv:>4.1f}")

    # Bottom 20
    print(f"\n  Bottom 10 hyperedges:")
    for i, ((c1, c2, c3), bw) in enumerate(sorted_he[-10:]):
        tiers = f"({q_tier[c1]},{q_tier[c2]},{q_tier[c3]})"
        print(f"  {len(sorted_he)-9+i:>4} | ({c1:>2},{c2:>2},{c3:>2}){'':>11} | {tiers:<25} | {bw:>8.4f}")

    return he_borns, he_cvs, sorted_he


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: BORN-MAXIMISING SUB-HYPERGRAPH
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_max_subhypergraph(q_tier, unique_he, he_borns, tier_info, n_cl):
    """Find the Born-maximising sub-hypergraph at various thresholds."""
    print(f"\n{'─'*70}")
    print(f"  BORN-MAXIMISING SUB-HYPERGRAPH")
    print(f"{'─'*70}")

    sorted_he = sorted(he_borns.items(), key=lambda x: -x[1])
    total_born = sum(he_borns.values())

    # At various top-k thresholds, which vertices are covered?
    print(f"\n  Cumulative Born weight and vertex coverage:")
    print(f"  {'top-k':>6} | {'cum μ':>8} | {'frac':>6} | {'verts':>6} | "
          f"{'A':>3} | {'B':>3} | {'C':>3} | {'vertex IDs covered'}")
    print(f"  {'─'*80}")

    for k in [5, 10, 20, 30, 50, 75, 100, 150, 200, 306]:
        k_actual = min(k, len(sorted_he))
        top_k = sorted_he[:k_actual]
        cum_born = sum(bw for _, bw in top_k)
        verts = set()
        for (c1, c2, c3), _ in top_k:
            verts.update([c1, c2, c3])
        n_a = sum(1 for v in verts if q_tier[v] == 'A')
        n_b = sum(1 for v in verts if q_tier[v] == 'B')
        n_c = sum(1 for v in verts if q_tier[v] == 'C_even')
        vids = sorted(verts)[:8]
        vid_str = ','.join(str(v) for v in vids) + ('...' if len(verts) > 8 else '')
        print(f"  {k_actual:>6} | {cum_born:>8.2f} | {cum_born/total_born:>5.1%} | "
              f"{len(verts):>6} | {n_a:>3} | {n_b:>3} | {n_c:>3} | {vid_str}")

    # Tier distribution in top-k sub-hypergraphs
    print(f"\n  Tier pattern distribution in top-50 vs all:")
    all_patterns = Counter()
    top50_patterns = Counter()
    for (c1, c2, c3), bw in sorted_he:
        pat = (q_tier[c1], q_tier[c2], q_tier[c3])
        all_patterns[pat] += 1
    for (c1, c2, c3), bw in sorted_he[:50]:
        pat = (q_tier[c1], q_tier[c2], q_tier[c3])
        top50_patterns[pat] += 1

    print(f"  {'Pattern':<30} | {'top-50':>7} | {'all':>7} | {'enrichment':>11}")
    print(f"  {'─'*65}")
    for pat in sorted(all_patterns.keys(), key=lambda p: -top50_patterns.get(p, 0)):
        n_top = top50_patterns.get(pat, 0)
        n_all = all_patterns[pat]
        expected = 50 * n_all / len(sorted_he)
        enrichment = n_top / expected if expected > 0 else float('inf')
        label = f"({pat[0]},{pat[1]},{pat[2]})"
        if n_top > 0 or n_all > 10:
            print(f"  {label:<30} | {n_top:>7} | {n_all:>7} | {enrichment:>10.2f}x")

    return top50_patterns


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: SHARED-VERTEX BORN POTENTIAL
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_vertex_potential(q_tier, unique_he, he_borns, tier_info, n_cl):
    """Compute Born "potential" at each vertex — sum of Born weights over
    all hyperedges containing that vertex. Test if this breaks Z₆ within tiers."""
    print(f"\n{'─'*70}")
    print(f"  SHARED-VERTEX BORN POTENTIAL")
    print(f"{'─'*70}")

    # Sum of Born weights at each vertex
    vertex_born_sum = defaultdict(float)
    # Number of hyperedges at each vertex
    vertex_he_count = defaultdict(int)
    # Product of Born weights (geometric mean proxy)
    vertex_born_prod = defaultdict(lambda: 1.0)
    # Max Born weight at each vertex
    vertex_born_max = defaultdict(float)
    # Positional Born: sum separately by which position the vertex occupies
    vertex_pos_born = defaultdict(lambda: defaultdict(float))

    for (c1, c2, c3), bw in he_borns.items():
        for pos_idx, c in enumerate([c1, c2, c3]):
            vertex_born_sum[c] += bw
            vertex_he_count[c] += 1
            vertex_born_prod[c] *= bw
            vertex_born_max[c] = max(vertex_born_max[c], bw)
            pos_name = ['pos1', 'pos2', 'pos3'][pos_idx]
            vertex_pos_born[c][pos_name] += bw

    # Vertex potential by tier
    print(f"\n  Vertex Born potential (sum of Born weights over all hyperedges):")
    print(f"  {'ID':>3} | {'Tier':<8} | {'Σ(μ)':>8} | {'N_he':>5} | "
          f"{'⟨μ⟩':>8} | {'max(μ)':>8} | {'pos1_μ':>8} | {'pos2_μ':>8} | {'pos3_μ':>8}")
    print(f"  {'─'*85}")

    for c in range(n_cl):
        tier = q_tier[c]
        s = vertex_born_sum[c]
        n = vertex_he_count[c]
        avg = s / n if n > 0 else 0
        mx = vertex_born_max[c]
        p1 = vertex_pos_born[c]['pos1']
        p2 = vertex_pos_born[c]['pos2']
        p3 = vertex_pos_born[c]['pos3']
        print(f"  {c:>3} | {tier:<8} | {s:>8.3f} | {n:>5} | "
              f"{avg:>8.4f} | {mx:>8.4f} | {p1:>8.3f} | {p2:>8.3f} | {p3:>8.3f}")

    # Z₆ breaking: within-tier variation of vertex potential
    print(f"\n  Within-tier Z₆ breaking (vertex potential):")
    print(f"  {'Tier':<8} | {'N':>3} | {'⟨Σμ⟩':>8} | {'σ':>8} | {'CV%':>6} | "
          f"{'min':>8} | {'max':>8} | {'max/min':>8}")
    print(f"  {'─'*70}")

    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        potentials = [vertex_born_sum[c] for c in members]
        if not potentials:
            continue
        mean_p = np.mean(potentials)
        std_p = np.std(potentials)
        cv = std_p / mean_p * 100 if mean_p > 0 else 0
        min_p = min(potentials)
        max_p = max(potentials)
        ratio = max_p / min_p if min_p > 0 else float('inf')
        print(f"  {tier_name:<8} | {len(members):>3} | {mean_p:>8.3f} | {std_p:>8.3f} | "
              f"{cv:>5.1f} | {min_p:>8.3f} | {max_p:>8.3f} | {ratio:>8.2f}")

    # Position-decomposed potential
    print(f"\n  Position-decomposed vertex potential (which position contributes most):")
    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        print(f"\n    {tier_name}:")
        for c in sorted(members):
            total = vertex_born_sum[c]
            p1 = vertex_pos_born[c]['pos1']
            p2 = vertex_pos_born[c]['pos2']
            p3 = vertex_pos_born[c]['pos3']
            print(f"      v{c:>2}: total={total:.3f}  "
                  f"pos1={p1:.3f} ({p1/total*100:.0f}%)  "
                  f"pos2={p2:.3f} ({p2/total*100:.0f}%)  "
                  f"pos3={p3:.3f} ({p3/total*100:.0f}%)")

    return vertex_born_sum, vertex_pos_born


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: MULTI-EDGE BORN CORRELATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_born_correlations(q_tier, unique_he, he_borns, tier_info, n_cl):
    """Analyse correlations between Born weights of hyperedges sharing vertices."""
    print(f"\n{'─'*70}")
    print(f"  MULTI-EDGE BORN CORRELATIONS")
    print(f"{'─'*70}")

    # For each vertex, collect all hyperedge Born weights
    vertex_he_map = defaultdict(list)  # vertex → [(he_key, bw), ...]
    for (c1, c2, c3), bw in he_borns.items():
        vertex_he_map[c1].append(((c1, c2, c3), bw))
        vertex_he_map[c2].append(((c1, c2, c3), bw))
        vertex_he_map[c3].append(((c1, c2, c3), bw))

    # For each pair of hyperedges sharing a vertex, compute correlation
    # (do they tend to both be high or both be low?)
    shared_pairs = []
    for v, he_list in vertex_he_map.items():
        bws = [bw for _, bw in he_list]
        for i in range(len(bws)):
            for j in range(i+1, len(bws)):
                shared_pairs.append((bws[i], bws[j]))

    if shared_pairs:
        x = np.array([p[0] for p in shared_pairs])
        y = np.array([p[1] for p in shared_pairs])
        corr = np.corrcoef(x, y)[0, 1]
        print(f"\n  Born weight correlation between hyperedges sharing a vertex:")
        print(f"    N pairs: {len(shared_pairs)}")
        print(f"    Pearson r: {corr:.4f}")
        print(f"    Interpretation: {'positive (cooperative)' if corr > 0.05 else 'negative (competitive)' if corr < -0.05 else 'near-zero (independent)'}")

    # Tier-resolved correlations
    print(f"\n  Born correlation by shared-vertex tier:")
    for tier_name in ['A', 'B', 'C_even']:
        members = set(tier_info[tier_name])
        tier_pairs = []
        for v in members:
            bws = [bw for _, bw in vertex_he_map.get(v, [])]
            for i in range(len(bws)):
                for j in range(i+1, len(bws)):
                    tier_pairs.append((bws[i], bws[j]))
        if len(tier_pairs) > 10:
            x = np.array([p[0] for p in tier_pairs])
            y = np.array([p[1] for p in tier_pairs])
            corr = np.corrcoef(x, y)[0, 1]
            print(f"    {tier_name:<8}: r = {corr:+.4f}  (N = {len(tier_pairs)})")

    # "Vertex coherence": for each vertex, does it tend to appear in
    # uniformly high or uniformly low Born-weight hyperedges?
    print(f"\n  Vertex coherence (CV of Born weights at each vertex):")
    print(f"  {'Tier':<8} | {'⟨CV%⟩':>8} | {'min CV':>8} | {'max CV':>8}")
    print(f"  {'─'*40}")
    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        cvs = []
        for c in members:
            bws = [bw for _, bw in vertex_he_map.get(c, [])]
            if len(bws) > 1:
                cv = np.std(bws) / np.mean(bws) * 100
                cvs.append(cv)
        if cvs:
            print(f"  {tier_name:<8} | {np.mean(cvs):>7.1f} | {min(cvs):>7.1f} | {max(cvs):>7.1f}")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: ENSEMBLE — VACUUM CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_vacuum_consistency(n_ic, seed, depth):
    """Across ICs, does the Born-maximising sub-hypergraph select the same
    structural features (tier patterns, vertex subsets)?"""
    print(f"\n{'─'*70}")
    print(f"  VACUUM CONSISTENCY ACROSS {n_ic} ICs")
    print(f"{'─'*70}")

    rng_master = np.random.default_rng(seed)

    # Track per-IC: within-tier CV of vertex potential
    tier_cvs = {t: [] for t in ['A', 'B', 'C_even']}
    # Track: which tier pattern is the #1 hyperedge?
    top1_patterns = Counter()
    top5_patterns = Counter()
    # Track: vertex potential ranking within tiers
    # For Tier B (the doublet sector), does the same vertex always rank #1?
    tier_b_rankings = []  # list of (sorted vertex IDs by potential)
    # Track: overall vertex potential variation
    tier_potential_ratios = {t: [] for t in ['A', 'B', 'C_even']}

    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)

        # Born weights
        he_borns = {}
        for (c1, c2, c3), instances in unique_he.items():
            he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])

        # Top hyperedge tier pattern
        sorted_he = sorted(he_borns.items(), key=lambda x: -x[1])
        (c1, c2, c3), _ = sorted_he[0]
        top1_patterns[(q_tier[c1], q_tier[c2], q_tier[c3])] += 1
        for (c1, c2, c3), _ in sorted_he[:5]:
            top5_patterns[(q_tier[c1], q_tier[c2], q_tier[c3])] += 1

        # Vertex potential
        vertex_born = defaultdict(float)
        for (c1, c2, c3), bw in he_borns.items():
            vertex_born[c1] += bw
            vertex_born[c2] += bw
            vertex_born[c3] += bw

        # Within-tier CV
        for tier_name in ['A', 'B', 'C_even']:
            members = tier_info[tier_name]
            pots = [vertex_born[c] for c in members]
            if len(pots) > 1 and np.mean(pots) > 0:
                cv = np.std(pots) / np.mean(pots) * 100
                tier_cvs[tier_name].append(cv)
                ratio = max(pots) / min(pots) if min(pots) > 0 else float('inf')
                tier_potential_ratios[tier_name].append(ratio)

        # Tier B ranking
        b_members = tier_info['B']
        b_pots = [(vertex_born[c], c) for c in b_members]
        b_pots.sort(reverse=True)
        tier_b_rankings.append([c for _, c in b_pots])

    # Summary
    print(f"\n  Within-tier CV of vertex potential across {n_ic} ICs:")
    print(f"  {'Tier':<8} | {'⟨CV%⟩':>8} | {'σ(CV%)':>8} | {'min':>8} | {'max':>8} | "
          f"{'⟨max/min⟩':>10}")
    print(f"  {'─'*60}")
    for t in ['A', 'B', 'C_even']:
        cvs = tier_cvs[t]
        ratios = tier_potential_ratios[t]
        if cvs:
            print(f"  {t:<8} | {np.mean(cvs):>7.1f} | {np.std(cvs):>7.1f} | "
                  f"{min(cvs):>7.1f} | {max(cvs):>7.1f} | "
                  f"{np.mean(ratios):>9.2f}")

    print(f"\n  Top-1 hyperedge tier pattern distribution:")
    for pat, count in sorted(top1_patterns.items(), key=lambda x: -x[1]):
        label = f"({pat[0]},{pat[1]},{pat[2]})"
        print(f"    {label}: {count}/{n_ic} ({count/n_ic:.0%})")

    print(f"\n  Top-5 hyperedge tier patterns (total = {5*n_ic}):")
    for pat, count in sorted(top5_patterns.items(), key=lambda x: -x[1]):
        label = f"({pat[0]},{pat[1]},{pat[2]})"
        print(f"    {label}: {count}/{5*n_ic} ({count/(5*n_ic):.0%})")

    # Tier B ranking consistency
    print(f"\n  Tier B vertex ranking consistency:")
    print(f"  (Do the same vertices consistently rank highest in potential?)")
    # Since vertex IDs change across ICs (different clusterings), track by
    # position within the tier (0-5) rather than absolute ID
    # Actually, the cluster IDs are determined by the quotient construction,
    # which is decoration-independent in structure but IC-dependent in which
    # physical vertex maps where. The RANKING within the tier is what matters.

    # Check: is the top-ranked Tier B vertex always the same relative position?
    # Better: just report the spread of potentials within Tier B
    print(f"    (Covered by within-tier CV above: Tier B CV = "
          f"{np.mean(tier_cvs['B']):.1f}% ± {np.std(tier_cvs['B']):.1f}%)")

    # Final summary metric: "vacuum selection strength"
    # = ratio of max to mean potential within Tier B
    # If this is >>1 consistently, the Born measure selects a vertex
    print(f"\n  Vacuum selection strength (max/mean potential within Tier B):")
    max_mean_ratios = []
    rng_master2 = np.random.default_rng(seed)
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master2.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)
        he_borns = {}
        for (c1, c2, c3), instances in unique_he.items():
            he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])
        vertex_born = defaultdict(float)
        for (c1, c2, c3), bw in he_borns.items():
            vertex_born[c1] += bw
            vertex_born[c2] += bw
            vertex_born[c3] += bw
        b_pots = [vertex_born[c] for c in tier_info['B']]
        ratio = max(b_pots) / np.mean(b_pots) if np.mean(b_pots) > 0 else 0
        max_mean_ratios.append(ratio)

    print(f"    ⟨max/mean⟩ = {np.mean(max_mean_ratios):.3f} ± {np.std(max_mean_ratios):.3f}")
    print(f"    (1.0 = perfect Z₆ symmetry, >>1 = strong vacuum selection)")


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 6: BORN-WEIGHTED ADJACENCY AND SPECTRAL STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_born_spectral(q_tier, unique_he, he_borns, tier_info, n_cl):
    """Build Born-weighted adjacency matrix and check spectral structure."""
    print(f"\n{'─'*70}")
    print(f"  BORN-WEIGHTED ADJACENCY SPECTRUM")
    print(f"{'─'*70}")

    # Build Born-weighted adjacency: A_ij = sum of Born weights over
    # hyperedges containing both i and j
    A = np.zeros((n_cl, n_cl))
    for (c1, c2, c3), bw in he_borns.items():
        for i, j in [(c1, c2), (c1, c3), (c2, c3)]:
            A[i, j] += bw
            A[j, i] += bw

    # Eigenvalues
    evals = np.linalg.eigvalsh(A)
    evals = np.sort(evals)[::-1]

    print(f"\n  Top 10 eigenvalues: {', '.join(f'{e:.3f}' for e in evals[:10])}")
    print(f"  Spectral gap: λ₀ - λ₁ = {evals[0] - evals[1]:.3f}")

    # Eigenvector of top eigenvalue: does it align with tier structure?
    evals_full, evecs = np.linalg.eigh(A)
    idx = np.argsort(evals_full)[::-1]
    v0 = evecs[:, idx[0]]
    v1 = evecs[:, idx[1]]

    print(f"\n  Leading eigenvector components by tier:")
    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        comps = [abs(v0[c]) for c in members]
        print(f"    {tier_name:<8}: mean |v₀| = {np.mean(comps):.4f}, "
              f"std = {np.std(comps):.4f}")

    print(f"\n  Second eigenvector (symmetry-breaking direction):")
    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        comps = [v1[c] for c in members]
        print(f"    {tier_name:<8}: components = [{', '.join(f'{c:.3f}' for c in comps)}]")

    # Check if v1 breaks Z₆ within any tier
    print(f"\n  Does the second eigenvector break Z₆ within tiers?")
    for tier_name in ['A', 'B', 'C_even']:
        members = tier_info[tier_name]
        comps = [v1[c] for c in members]
        cv = np.std(comps) / (abs(np.mean(comps)) + 1e-15) * 100
        # Check if components split into two groups (sign change)
        pos = sum(1 for c in comps if c > 0.01)
        neg = sum(1 for c in comps if c < -0.01)
        near_zero = len(comps) - pos - neg
        print(f"    {tier_name:<8}: {pos} positive, {neg} negative, {near_zero} near-zero  "
              f"(CV = {cv:.0f}%)")

    return A, evals


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="G3: Born-maximising sub-hypergraph on Q₂₄")
    parser.add_argument("--n_ic", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  G3 Born-Maximising Sub-Hypergraph on Q₂₄")
    print(f"  {args.n_ic} ICs, depth {args.depth}, seed {args.seed}")
    print(f"{'='*70}")
    t0 = time.time()

    # Build single IC for detailed analysis
    rng = np.random.default_rng(args.seed)
    q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, args.depth)

    # Born weights
    he_borns = {}
    for (c1, c2, c3), instances in unique_he.items():
        he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])

    # Analysis 1: Born landscape
    he_borns_out, he_cvs, sorted_he = analyse_born_landscape(
        q_psi, q_tier, unique_he, tier_info, n_cl, "(IC #0)")

    # Analysis 2: Born-maximising sub-hypergraph
    top50 = analyse_max_subhypergraph(q_tier, unique_he, he_borns, tier_info, n_cl)

    # Analysis 3: Shared-vertex Born potential
    vertex_born, vertex_pos_born = analyse_vertex_potential(
        q_tier, unique_he, he_borns, tier_info, n_cl)

    # Analysis 4: Multi-edge correlations
    analyse_born_correlations(q_tier, unique_he, he_borns, tier_info, n_cl)

    # Analysis 5: Ensemble vacuum consistency
    analyse_vacuum_consistency(args.n_ic, args.seed, args.depth)

    # Analysis 6: Born-weighted spectral structure
    analyse_born_spectral(q_tier, unique_he, he_borns, tier_info, n_cl)

    print(f"\n{'='*70}")
    print(f"  Total time: {time.time()-t0:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
