#!/usr/bin/env python3
"""
g3_tier_coupling_v1.py — G3 symmetry breaking from quotient topology

Builds Q₂₄, labels vertices by tier, classifies all hyperedges by
tier pattern at each position, and tests whether the tier structure
maps onto the electroweak coupling types (3,1)/(3,2)/(3̄,1).

Key question: does the 4-tier structure (A/B/C_even/C_odd) of Q₂₄
align with the coupling-type asymmetry at positions 1/2/3, creating
a structural basis for SU(2)×U(1) → U(1)_EM breaking?

Usage:
  python g3_tier_coupling_v1.py [--n_ic N] [--seed S] [--depth D]
"""

import numpy as np
import time
import argparse
from collections import defaultdict, Counter

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ALGEBRA
# ═══════════════════════════════════════════════════════════════════════════════

def cross_C3(a, b):
    return np.array([
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    ], dtype=np.complex128)

def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-15 else np.zeros_like(v)

def compose_colour(psi1, psi2):
    return normalize(np.conj(cross_C3(psi1, psi2)))

def haar_C3(rng):
    v = rng.standard_normal(3) + 1j * rng.standard_normal(3)
    return normalize(v)

def born_weight(psi1, psi2, psi3, depth):
    """Born weight μ_cov = |det[ψ̃₁|ψ̃₂|ψ̃₃]|².
    At odd depth, conjugate pos1 and pos2; at even depth, conjugate pos3."""
    if depth % 2 == 1:
        pt1, pt2, pt3 = np.conj(psi1), np.conj(psi2), psi3.copy()
    else:
        pt1, pt2, pt3 = psi1.copy(), psi2.copy(), np.conj(psi3)
    M = np.column_stack([pt1, pt2, pt3])
    return abs(np.linalg.det(M))**2

def fidelity(a, b):
    """Gauge-equivalence test: |⟨a|b⟩|² in CP²."""
    return abs(np.vdot(a, b))**2


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₂₄
# ═══════════════════════════════════════════════════════════════════════════════

def build_Q24(rng, depth=5):
    """Build the multiway graph M(G₀) to given depth, then take the
    gauge-equivalence quotient to get Q₂₄.

    Returns:
        q_psi: dict cluster_id → representative ψ vector
        q_tier: dict cluster_id → tier label ('A','B','C_even','C_odd')
        q_hyperedges: list of (cluster_pos1, cluster_pos2, cluster_pos3, depth, born_wt)
        vertex_map: dict vid → cluster_id
        tier_info: dict with tier membership details
    """
    # --- Build G₀ ---
    G0_topo = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]
    psi = {}
    for v in range(6):
        psi[v] = haar_C3(rng)
    next_vid = 6

    # Track vertex provenance for tier assignment
    # vertex_gen[vid] = generation when vertex was first created
    # vertex_parents[vid] = (parent_v1, parent_v2) or None for originals
    vertex_gen = {v: 0 for v in range(6)}
    vertex_parents = {v: None for v in range(6)}

    # Store edges as (depth, v1, v2, v3)
    edges = []
    for s1, s2, s3 in G0_topo:
        edges.append((0, s1, s2, s3))

    compose_cache = {}  # (v1, v2) → w_vid

    for gen in range(depth):
        parent_edges = [(i, e) for i, e in enumerate(edges) if e[0] == gen]
        for idx, (d, v1, v2, v3) in parent_edges:
            key = (v1, v2)
            if key not in compose_cache:
                psi_new = compose_colour(psi[v1], psi[v2])
                compose_cache[key] = next_vid
                psi[next_vid] = psi_new
                vertex_gen[next_vid] = gen + 1
                vertex_parents[next_vid] = (v1, v2)
                next_vid += 1
            w = compose_cache[key]

            edges.append((gen+1, w, v2, v3))  # D1
            edges.append((gen+1, w, v1, v3))  # D2
            edges.append((gen+1, w, v1, v2))  # D3

    # --- Gauge-equivalence quotient ---
    # Cluster vertices by |⟨ψ_a|ψ_b⟩|² ≈ 1
    all_vids = sorted(psi.keys())
    n_verts = len(all_vids)

    # Union-find
    parent_uf = list(range(n_verts))
    vid_to_idx = {v: i for i, v in enumerate(all_vids)}

    def find(x):
        while parent_uf[x] != parent_uf[parent_uf[x]]:
            parent_uf[x] = parent_uf[parent_uf[x]]
        while parent_uf[x] != x:
            parent_uf[x] = parent_uf[parent_uf[x]]
            x = parent_uf[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent_uf[px] = py

    THRESHOLD = 0.999
    # For efficiency, only compare vertices that could be equivalent
    # (same cluster of similar ψ). But for Q₂₄ (small), brute force is fine
    # up to ~1000 vertices. For larger depths, sample.
    if n_verts <= 2000:
        psi_arr = np.array([psi[v] for v in all_vids])
        # Compute all pairwise fidelities via matrix multiply
        G = psi_arr @ psi_arr.conj().T
        fid_matrix = np.abs(G)**2
        for i in range(n_verts):
            for j in range(i+1, n_verts):
                if fid_matrix[i, j] > THRESHOLD:
                    union(i, j)
    else:
        # For large vertex sets, use representative-based clustering
        clusters = []
        vid_cluster = {}
        for v in all_vids:
            idx = vid_to_idx[v]
            matched = False
            for ci, (rep_v, rep_psi) in enumerate(clusters):
                if fidelity(psi[v], rep_psi) > THRESHOLD:
                    union(idx, vid_to_idx[rep_v])
                    matched = True
                    break
            if not matched:
                clusters.append((v, psi[v]))

    # Build cluster map
    cluster_map = defaultdict(list)  # root_idx → [vid, ...]
    for v in all_vids:
        idx = vid_to_idx[v]
        root = find(idx)
        cluster_map[root].append(v)

    # Assign cluster IDs 0..N-1
    cluster_roots = sorted(cluster_map.keys())
    root_to_cid = {r: i for i, r in enumerate(cluster_roots)}
    vertex_to_cluster = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        for v in vids:
            vertex_to_cluster[v] = cid

    n_clusters = len(cluster_roots)

    # Representative ψ for each cluster (earliest vertex)
    q_psi = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        earliest = min(vids, key=lambda v: vertex_gen[v])
        q_psi[cid] = psi[earliest]

    # --- Tier assignment ---
    # Tier A: original G₀ vertices (gen 0)
    # Tier B: first compositions (gen 1) — compose(pos1, pos2) of G₀ edges
    # Tier C: second+ compositions
    # Split C into C_even/C_odd by gen parity of earliest representative

    # First, find the cluster of each original vertex
    original_clusters = set()
    for v in range(6):
        original_clusters.add(vertex_to_cluster[v])

    # Gen-1 composed vertices
    gen1_clusters = set()
    for v, g in vertex_gen.items():
        if g == 1:
            c = vertex_to_cluster[v]
            if c not in original_clusters:
                gen1_clusters.add(c)

    # Remaining clusters
    remaining = set(range(n_clusters)) - original_clusters - gen1_clusters

    # For remaining, find earliest generation
    cluster_earliest_gen = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        earliest_gen = min(vertex_gen[v] for v in vids)
        cluster_earliest_gen[cid] = earliest_gen

    c_even = set()
    c_odd = set()
    for c in remaining:
        eg = cluster_earliest_gen[c]
        if eg % 2 == 0:
            c_even.add(c)
        else:
            c_odd.add(c)

    q_tier = {}
    for c in original_clusters:
        q_tier[c] = 'A'
    for c in gen1_clusters:
        q_tier[c] = 'B'
    for c in c_even:
        q_tier[c] = 'C_even'
    for c in c_odd:
        q_tier[c] = 'C_odd'

    # --- Quotient hyperedges ---
    # Each edge (depth, v1, v2, v3) maps to (cluster(v1), cluster(v2), cluster(v3))
    # Also compute Born weight
    q_hyperedges = []
    seen_hyperedges = set()

    for depth_e, v1, v2, v3 in edges:
        c1 = vertex_to_cluster[v1]
        c2 = vertex_to_cluster[v2]
        c3 = vertex_to_cluster[v3]
        bw = born_weight(psi[v1], psi[v2], psi[v3], depth_e)
        q_hyperedges.append((c1, c2, c3, depth_e, bw))

    # Unique hyperedges (by cluster triple)
    unique_he = defaultdict(list)  # (c1,c2,c3) → [(depth, bw), ...]
    for c1, c2, c3, d, bw in q_hyperedges:
        unique_he[(c1, c2, c3)].append((d, bw))

    # --- Degree sequence ---
    degree = Counter()
    for (c1, c2, c3) in unique_he:
        degree[c1] += 1
        degree[c2] += 1
        degree[c3] += 1

    tier_info = {
        'A': sorted(original_clusters),
        'B': sorted(gen1_clusters),
        'C_even': sorted(c_even),
        'C_odd': sorted(c_odd),
        'degree': degree,
        'cluster_earliest_gen': cluster_earliest_gen,
    }

    return q_psi, q_tier, unique_he, vertex_to_cluster, tier_info, n_clusters


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: TIER DISTRIBUTION ACROSS POSITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_tier_positions(q_tier, unique_he):
    """For each position (pos1, pos2, pos3), count how often each tier appears."""
    print(f"\n{'─'*70}")
    print(f"  TIER DISTRIBUTION ACROSS HYPEREDGE POSITIONS")
    print(f"{'─'*70}")

    tiers = ['A', 'B', 'C_even', 'C_odd']
    pos_tier_count = {pos: Counter() for pos in ['pos1', 'pos2', 'pos3']}

    for (c1, c2, c3) in unique_he:
        pos_tier_count['pos1'][q_tier[c1]] += 1
        pos_tier_count['pos2'][q_tier[c2]] += 1
        pos_tier_count['pos3'][q_tier[c3]] += 1

    n_he = len(unique_he)
    print(f"\n  {n_he} unique hyperedges (ordered triples)")
    print(f"\n  {'Tier':<10} | {'pos1 (3,1)':<14} | {'pos2 (3,2)':<14} | {'pos3 (3̄,1)':<14} | {'Total':<8}")
    print(f"  {'─'*68}")
    for t in tiers:
        c1 = pos_tier_count['pos1'].get(t, 0)
        c2 = pos_tier_count['pos2'].get(t, 0)
        c3 = pos_tier_count['pos3'].get(t, 0)
        total = c1 + c2 + c3
        print(f"  {t:<10} | {c1:>5} ({c1/n_he*100:>5.1f}%) | "
              f"{c2:>5} ({c2/n_he*100:>5.1f}%) | "
              f"{c3:>5} ({c3/n_he*100:>5.1f}%) | {total:>6}")

    # Asymmetry index: for each tier, how asymmetric is the distribution across positions?
    print(f"\n  Position asymmetry per tier:")
    print(f"  {'Tier':<10} | {'χ² (vs uniform)':<16} | {'dominant pos':<14} | {'interpretation'}")
    print(f"  {'─'*70}")
    coupling_names = {'pos1': '(3,1) u_R', 'pos2': '(3,2) Q_L', 'pos3': '(3̄,1) ū_R'}
    for t in tiers:
        counts = [pos_tier_count[p].get(t, 0) for p in ['pos1', 'pos2', 'pos3']]
        total = sum(counts)
        if total == 0:
            continue
        expected = total / 3
        chi2 = sum((c - expected)**2 / expected for c in counts)
        dominant_idx = np.argmax(counts)
        dominant_pos = ['pos1', 'pos2', 'pos3'][dominant_idx]
        frac = counts[dominant_idx] / total
        print(f"  {t:<10} | {chi2:>14.2f}   | {dominant_pos} ({frac:.1%})  | "
              f"↔ {coupling_names[dominant_pos]}")

    return pos_tier_count


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: TIER-PATTERN CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_tier_patterns(q_tier, unique_he):
    """Classify hyperedges by their (tier_pos1, tier_pos2, tier_pos3) pattern."""
    print(f"\n{'─'*70}")
    print(f"  HYPEREDGE TIER PATTERNS")
    print(f"{'─'*70}")

    pattern_count = Counter()
    pattern_examples = defaultdict(list)

    for (c1, c2, c3) in unique_he:
        pat = (q_tier[c1], q_tier[c2], q_tier[c3])
        pattern_count[pat] += 1
        if len(pattern_examples[pat]) < 3:
            pattern_examples[pat].append((c1, c2, c3))

    n_he = len(unique_he)
    print(f"\n  {len(pattern_count)} distinct tier patterns across {n_he} hyperedges")
    print(f"\n  {'Pattern (pos1,pos2,pos3)':<35} | {'Count':>6} | {'Fraction':>8}")
    print(f"  {'─'*55}")
    for pat, count in sorted(pattern_count.items(), key=lambda x: -x[1]):
        label = f"({pat[0]}, {pat[1]}, {pat[2]})"
        print(f"  {label:<35} | {count:>6} | {count/n_he:>7.1%}")

    # Check: are there "pure" tier patterns (all same tier)?
    print(f"\n  Same-tier patterns:")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        pat = (t, t, t)
        c = pattern_count.get(pat, 0)
        print(f"    ({t},{t},{t}): {c}")

    # Check: position-swapped asymmetry
    print(f"\n  Position-swap asymmetry (pos1↔pos2 = P₁₂ parity):")
    for pat, count in sorted(pattern_count.items(), key=lambda x: -x[1]):
        swapped = (pat[1], pat[0], pat[2])
        if swapped != pat and swapped in pattern_count:
            sw_count = pattern_count[swapped]
            label = f"({pat[0]},{pat[1]},{pat[2]})"
            sw_label = f"({swapped[0]},{swapped[1]},{swapped[2]})"
            if count >= sw_count:  # only print once
                print(f"    {label}: {count}  vs  {sw_label}: {sw_count}  "
                      f"(ratio {count/sw_count:.2f})")

    return pattern_count


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 3: BORN WEIGHTS BY TIER PATTERN
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_born_by_pattern(q_tier, unique_he):
    """Compute Born weight statistics per tier pattern."""
    print(f"\n{'─'*70}")
    print(f"  BORN WEIGHTS BY TIER PATTERN")
    print(f"{'─'*70}")

    pattern_borns = defaultdict(list)

    for (c1, c2, c3), instances in unique_he.items():
        pat = (q_tier[c1], q_tier[c2], q_tier[c3])
        # Use mean Born weight across instances (should be ~constant for quotient)
        bws = [bw for (d, bw) in instances]
        mean_bw = np.mean(bws)
        cv = np.std(bws) / mean_bw * 100 if mean_bw > 1e-15 else 0
        pattern_borns[pat].append((mean_bw, cv))

    print(f"\n  {'Pattern':<35} | {'N':>4} | {'⟨μ⟩':>8} | {'σ(μ)':>8} | "
          f"{'total μ':>8} | {'frac':>6}")
    print(f"  {'─'*80}")

    total_born = sum(np.mean([bw for bw, _ in bws])
                     for bws in pattern_borns.values()
                     for bw, _ in [bws[0]] if False) # placeholder
    # Recompute properly
    total_born = 0
    pat_total = {}
    for pat, bw_list in pattern_borns.items():
        t = sum(bw for bw, cv in bw_list)
        pat_total[pat] = t
        total_born += t

    for pat, bw_list in sorted(pattern_borns.items(),
                                key=lambda x: -pat_total[x[0]]):
        bws = [bw for bw, cv in bw_list]
        n = len(bws)
        mean_bw = np.mean(bws)
        std_bw = np.std(bws)
        total = pat_total[pat]
        frac = total / total_born if total_born > 0 else 0
        label = f"({pat[0]}, {pat[1]}, {pat[2]})"
        print(f"  {label:<35} | {n:>4} | {mean_bw:>8.4f} | {std_bw:>8.4f} | "
              f"{total:>8.3f} | {frac:>5.1%}")

    # Born weight by tier at each position
    print(f"\n  Born weight concentration by tier at each position:")
    for pos_name, pos_idx in [('pos1', 0), ('pos2', 1), ('pos3', 2)]:
        tier_born = defaultdict(float)
        for (c1, c2, c3), instances in unique_he.items():
            tiers = [q_tier[c1], q_tier[c2], q_tier[c3]]
            mean_bw = np.mean([bw for d, bw in instances])
            tier_born[tiers[pos_idx]] += mean_bw
        total = sum(tier_born.values())
        print(f"\n    {pos_name}:")
        for t in ['A', 'B', 'C_even', 'C_odd']:
            b = tier_born.get(t, 0)
            print(f"      {t:<10}: {b:>8.3f} ({b/total*100:>5.1f}%)")

    return pattern_borns


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 4: Z₆ BREAKING BY BORN WITHIN TIERS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_z6_breaking(q_psi, q_tier, unique_he, tier_info, n_clusters):
    """Check if the Born measure breaks the Z₆ symmetry within each tier."""
    print(f"\n{'─'*70}")
    print(f"  Z₆ SYMMETRY BREAKING WITHIN TIERS")
    print(f"{'─'*70}")

    # Compute total Born weight per vertex (sum over all hyperedges containing it)
    vertex_born = defaultdict(float)
    for (c1, c2, c3), instances in unique_he.items():
        mean_bw = np.mean([bw for d, bw in instances])
        vertex_born[c1] += mean_bw
        vertex_born[c2] += mean_bw
        vertex_born[c3] += mean_bw

    # Within each tier, check variation
    print(f"\n  {'Tier':<10} | {'N':>3} | {'⟨Born⟩':>8} | {'σ':>8} | {'CV%':>6} | "
          f"{'min':>8} | {'max':>8} | {'max/min':>8}")
    print(f"  {'─'*75}")

    for tier_name in ['A', 'B', 'C_even', 'C_odd']:
        members = tier_info[tier_name]
        borns = [vertex_born[c] for c in members]
        if not borns:
            continue
        mean_b = np.mean(borns)
        std_b = np.std(borns)
        cv = std_b / mean_b * 100 if mean_b > 0 else 0
        min_b = min(borns)
        max_b = max(borns)
        ratio = max_b / min_b if min_b > 0 else float('inf')
        print(f"  {tier_name:<10} | {len(members):>3} | {mean_b:>8.3f} | {std_b:>8.3f} | "
              f"{cv:>5.1f} | {min_b:>8.3f} | {max_b:>8.3f} | {ratio:>8.2f}")

    # Degree sequence by tier
    print(f"\n  Degree sequence by tier:")
    degree = tier_info['degree']
    for tier_name in ['A', 'B', 'C_even', 'C_odd']:
        members = tier_info[tier_name]
        degs = sorted([degree[c] for c in members], reverse=True)
        print(f"    {tier_name:<10}: {degs}")

    return vertex_born


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS 5: ELECTROWEAK MAPPING TEST
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_ew_mapping(q_tier, unique_he, pos_tier_count, pattern_count, n_clusters):
    """Test whether tier structure maps onto electroweak breaking."""
    print(f"\n{'─'*70}")
    print(f"  ELECTROWEAK MAPPING ASSESSMENT")
    print(f"{'─'*70}")

    # SM coupling types from Prop_6_10 / Cor_6_15:
    #   pos1 = (3,1) → u_R (right-handed up quark, weak singlet)
    #   pos2 = (3,2) → Q_L (left-handed quark doublet)
    #   pos3 = (3̄,1) → ū_R (right-handed anti-up, weak singlet)
    #
    # In the SM, SU(2)×U(1)→U(1)_EM breaking distinguishes:
    #   - weak doublet (3,2): BROKEN sector (couples to W±, Z)
    #   - weak singlet (3,1), (3̄,1): UNBROKEN sector (no W±/Z coupling)
    #
    # Question: is there a tier that preferentially occupies pos2 (the doublet)?
    # If so, that tier is the "broken" sector.

    n_he = len(unique_he)
    print(f"\n  SM coupling assignments:")
    print(f"    pos1 = (3,1) → u_R (weak singlet)")
    print(f"    pos2 = (3,2) → Q_L (weak doublet)")
    print(f"    pos3 = (3̄,1) → ū_R (weak singlet)")

    print(f"\n  Tier affinity for the weak-doublet position (pos2):")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        c_pos2 = pos_tier_count['pos2'].get(t, 0)
        c_total = sum(pos_tier_count[p].get(t, 0) for p in ['pos1', 'pos2', 'pos3'])
        frac = c_pos2 / c_total if c_total > 0 else 0
        # Under no affinity (uniform across 3 positions), fraction = 1/3
        excess = frac - 1/3
        print(f"    {t:<10}: {c_pos2}/{c_total} = {frac:.3f}  "
              f"(excess over 1/3: {excess:+.3f})")

    # Test: do any tiers appear ONLY at specific positions?
    print(f"\n  Position exclusivity:")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        absent_from = []
        for p in ['pos1', 'pos2', 'pos3']:
            if pos_tier_count[p].get(t, 0) == 0:
                absent_from.append(p)
        if absent_from:
            print(f"    {t:<10}: ABSENT from {', '.join(absent_from)}")
        else:
            print(f"    {t:<10}: present at all positions")

    # Test: P₁₂ symmetry (pos1↔pos2 swap)
    # In the SM, P₁₂ exchanges (3,1)↔(3,2), i.e., u_R ↔ Q_L.
    # This is MAXIMALLY violated (Thm_7_14: structural P violation).
    # On Q₂₄, does P₁₂ permute tiers?
    print(f"\n  P₁₂ action on tier patterns:")
    p12_same = 0
    p12_diff = 0
    for pat, count in pattern_count.items():
        swapped = (pat[1], pat[0], pat[2])
        if swapped == pat:
            p12_same += count
        else:
            p12_diff += count
    print(f"    P₁₂-symmetric patterns: {p12_same} hyperedges")
    print(f"    P₁₂-asymmetric patterns: {p12_diff} hyperedges")
    print(f"    P violation fraction: {p12_diff/(p12_same+p12_diff):.1%}")

    # Inter-tier connectivity: which tiers are connected?
    print(f"\n  Inter-tier connectivity (number of hyperedges connecting tier pairs):")
    tier_pair_count = Counter()
    for (c1, c2, c3) in unique_he:
        tiers_in_edge = tuple(sorted([q_tier[c1], q_tier[c2], q_tier[c3]]))
        tier_pair_count[tiers_in_edge] += 1

    for combo, count in sorted(tier_pair_count.items(), key=lambda x: -x[1]):
        print(f"    {combo}: {count}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENSEMBLE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def run_ensemble(n_ic, seed, depth):
    """Run multiple ICs to check decoration-independence and Born variation."""
    print(f"\n{'='*70}")
    print(f"  ENSEMBLE ANALYSIS: {n_ic} ICs, depth {depth}, seed {seed}")
    print(f"{'='*70}")

    rng_master = np.random.default_rng(seed)

    all_n_clusters = []
    all_tier_sizes = []
    all_n_he = []

    # Accumulate per-IC results for detailed analysis on first IC
    first_ic_data = None

    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)

        all_n_clusters.append(n_cl)
        tier_sizes = {t: len(tier_info[t]) for t in ['A', 'B', 'C_even', 'C_odd']}
        all_tier_sizes.append(tier_sizes)
        all_n_he.append(len(unique_he))

        if ic == 0:
            first_ic_data = (q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl)

    # Summary
    print(f"\n  Quotient size: {np.mean(all_n_clusters):.1f} ± {np.std(all_n_clusters):.1f} "
          f"(range {min(all_n_clusters)}–{max(all_n_clusters)})")
    print(f"  Hyperedges: {np.mean(all_n_he):.1f} ± {np.std(all_n_he):.1f}")

    print(f"\n  Tier sizes across {n_ic} ICs:")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        sizes = [ts[t] for ts in all_tier_sizes]
        print(f"    {t:<10}: {np.mean(sizes):.1f} ± {np.std(sizes):.1f}  "
              f"(range {min(sizes)}–{max(sizes)})")

    return first_ic_data


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="G3: tier-coupling analysis on Q₂₄")
    parser.add_argument("--n_ic", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--depth", type=int, default=5)
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  G3 Tier-Coupling Analysis on Q₂₄")
    print(f"  {args.n_ic} ICs, depth {args.depth}, seed {args.seed}")
    print(f"{'='*70}")
    t0 = time.time()

    # Step 1: Ensemble check (decoration-independence)
    first_ic = run_ensemble(args.n_ic, args.seed, args.depth)
    q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = first_ic

    print(f"\n{'='*70}")
    print(f"  DETAILED ANALYSIS (IC #0)")
    print(f"{'='*70}")
    print(f"\n  Q₂₄: {n_cl} clusters, {len(unique_he)} unique hyperedges")
    print(f"  Tier sizes: A={len(tier_info['A'])}, B={len(tier_info['B'])}, "
          f"C_even={len(tier_info['C_even'])}, C_odd={len(tier_info['C_odd'])}")

    # Analysis 1: Tier distribution across positions
    pos_tier_count = analyse_tier_positions(q_tier, unique_he)

    # Analysis 2: Tier patterns
    pattern_count = analyse_tier_patterns(q_tier, unique_he)

    # Analysis 3: Born weights by pattern
    pattern_borns = analyse_born_by_pattern(q_tier, unique_he)

    # Analysis 4: Z₆ breaking
    vertex_born = analyse_z6_breaking(q_psi, q_tier, unique_he, tier_info, n_cl)

    # Analysis 5: Electroweak mapping
    analyse_ew_mapping(q_tier, unique_he, pos_tier_count, pattern_count, n_cl)

    print(f"\n{'='*70}")
    print(f"  Total time: {time.time()-t0:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
