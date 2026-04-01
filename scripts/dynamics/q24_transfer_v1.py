#!/usr/bin/env python3
"""
q24_transfer_v1.py — Transfer operator on Q₂₄ from DPO rewriting dynamics

Session 1 of the Dynamics on Q₂₄ work program.

Each of Q₂₄'s ~330 hyperedges "fires" via DPO rewriting: compose pos1×pos2
to get a new vertex w, then produce 3 daughter hyperedges D₁=(w,c₂,c₃),
D₂=(w,c₁,c₃), D₃=(w,c₁,c₂). Because Q₂₄ is autopoietic (M(Q₂₄)/gauge = Q₂₄),
all daughters map back to existing Q₂₄ hyperedges. This defines a transfer
operator encoding how composition weight flows through the quotient.

Key questions:
  1. Does the stationary distribution of T match Born weights?
  2. Is the transfer operator ergodic?
  3. Does the spectrum separate by tier?
  4. Is the firing map topology IC-independent?

Usage:
  python q24_transfer_v1.py [--n_ic N] [--seed S] [--depth D]
"""

import numpy as np
import argparse
import time
from collections import defaultdict, Counter

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ALGEBRA (from g3_tier_coupling_v1.py)
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
    if depth % 2 == 1:
        pt1, pt2, pt3 = np.conj(psi1), np.conj(psi2), psi3.copy()
    else:
        pt1, pt2, pt3 = psi1.copy(), psi2.copy(), np.conj(psi3)
    M = np.column_stack([pt1, pt2, pt3])
    return abs(np.linalg.det(M))**2

def fidelity(a, b):
    return abs(np.vdot(a, b))**2


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₂₄ (from g3_tier_coupling_v1.py, extended to return raw edges and psi)
# ═══════════════════════════════════════════════════════════════════════════════

def build_Q24(rng, depth=5):
    """Build Q₂₄ with full provenance tracking.

    Returns:
        q_psi: dict cluster_id -> representative psi vector
        q_tier: dict cluster_id -> tier label
        unique_he: dict (c1,c2,c3) -> [(depth, bw), ...]
        vertex_to_cluster: dict vid -> cluster_id
        tier_info: dict with tier membership
        n_clusters: int
    """
    G0_topo = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]
    psi = {}
    for v in range(6):
        psi[v] = haar_C3(rng)
    next_vid = 6

    vertex_gen = {v: 0 for v in range(6)}
    edges = []
    for s1, s2, s3 in G0_topo:
        edges.append((0, s1, s2, s3))

    compose_cache = {}

    for gen in range(depth):
        parent_edges = [(i, e) for i, e in enumerate(edges) if e[0] == gen]
        for idx, (d, v1, v2, v3) in parent_edges:
            key = (v1, v2)
            if key not in compose_cache:
                psi_new = compose_colour(psi[v1], psi[v2])
                compose_cache[key] = next_vid
                psi[next_vid] = psi_new
                vertex_gen[next_vid] = gen + 1
                next_vid += 1
            w = compose_cache[key]
            edges.append((gen+1, w, v2, v3))
            edges.append((gen+1, w, v1, v3))
            edges.append((gen+1, w, v1, v2))

    # Gauge-equivalence quotient
    all_vids = sorted(psi.keys())
    n_verts = len(all_vids)
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
    if n_verts <= 2000:
        psi_arr = np.array([psi[v] for v in all_vids])
        G = psi_arr @ psi_arr.conj().T
        fid_matrix = np.abs(G)**2
        for i in range(n_verts):
            for j in range(i+1, n_verts):
                if fid_matrix[i, j] > THRESHOLD:
                    union(i, j)
    else:
        clusters_list = []
        for v in all_vids:
            idx = vid_to_idx[v]
            matched = False
            for ci, (rep_v, rep_psi) in enumerate(clusters_list):
                if fidelity(psi[v], rep_psi) > THRESHOLD:
                    union(idx, vid_to_idx[rep_v])
                    matched = True
                    break
            if not matched:
                clusters_list.append((v, psi[v]))

    cluster_map = defaultdict(list)
    for v in all_vids:
        idx = vid_to_idx[v]
        root = find(idx)
        cluster_map[root].append(v)

    cluster_roots = sorted(cluster_map.keys())
    root_to_cid = {r: i for i, r in enumerate(cluster_roots)}
    vertex_to_cluster = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        for v in vids:
            vertex_to_cluster[v] = cid

    n_clusters = len(cluster_roots)

    q_psi = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        earliest = min(vids, key=lambda v: vertex_gen[v])
        q_psi[cid] = psi[earliest]

    # Tier assignment
    original_clusters = set()
    for v in range(6):
        original_clusters.add(vertex_to_cluster[v])

    gen1_clusters = set()
    for v, g in vertex_gen.items():
        if g == 1:
            c = vertex_to_cluster[v]
            if c not in original_clusters:
                gen1_clusters.add(c)

    remaining = set(range(n_clusters)) - original_clusters - gen1_clusters

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

    # Quotient hyperedges
    unique_he = defaultdict(list)
    for depth_e, v1, v2, v3 in edges:
        c1 = vertex_to_cluster[v1]
        c2 = vertex_to_cluster[v2]
        c3 = vertex_to_cluster[v3]
        bw = born_weight(psi[v1], psi[v2], psi[v3], depth_e)
        unique_he[(c1, c2, c3)].append((depth_e, bw))

    tier_info = {
        'A': sorted(original_clusters),
        'B': sorted(gen1_clusters),
        'C_even': sorted(c_even),
        'C_odd': sorted(c_odd),
        'degree': Counter(),
        'cluster_earliest_gen': cluster_earliest_gen,
    }
    for (c1, c2, c3) in unique_he:
        tier_info['degree'][c1] += 1
        tier_info['degree'][c2] += 1
        tier_info['degree'][c3] += 1

    return q_psi, q_tier, unique_he, vertex_to_cluster, tier_info, n_clusters


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFER OPERATOR CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════════

def find_cluster(psi_new, q_psi, threshold=0.999):
    """Find which Q₂₄ cluster a new psi vector maps to."""
    best_cid = None
    best_fid = 0.0
    for cid, psi_rep in q_psi.items():
        f = fidelity(psi_new, psi_rep)
        if f > best_fid:
            best_fid = f
            best_cid = cid
    if best_fid > threshold:
        return best_cid
    return None


def build_firing_map(q_psi, unique_he):
    """For each Q₂₄ hyperedge, fire it and map daughters back to Q₂₄.

    Returns:
        firing_map: dict he_idx -> [daughter_he_idx, daughter_he_idx, daughter_he_idx]
        he_list: list of hyperedge triples (c1, c2, c3) indexed by he_idx
        he_to_idx: dict (c1,c2,c3) -> he_idx
        source_sets: dict vertex_cid -> list of (c1, c2) source pairs that compose to it
        n_miss: number of daughters that don't map back to Q₂₄ hyperedges
        miss_details: list of (parent_he, daughter_type, daughter_triple) for misses
    """
    he_list = sorted(unique_he.keys())
    he_to_idx = {he: i for i, he in enumerate(he_list)}
    n_he = len(he_list)

    firing_map = {}  # he_idx -> list of daughter he_idx (or None for miss)
    source_sets = defaultdict(list)  # vertex_cid -> [(c1, c2, parent_he), ...]
    n_miss = 0
    miss_details = []

    for i, (c1, c2, c3) in enumerate(he_list):
        # Compose pos1 x pos2
        w_psi = compose_colour(q_psi[c1], q_psi[c2])
        w_cid = find_cluster(w_psi, q_psi)

        daughters = []
        if w_cid is not None:
            # Track that (c1, c2) composes to w_cid
            source_sets[w_cid].append((c1, c2, (c1, c2, c3)))

            # Three daughters
            d1 = (w_cid, c2, c3)
            d2 = (w_cid, c1, c3)
            d3 = (w_cid, c1, c2)

            for d_type, d_triple in [('D1', d1), ('D2', d2), ('D3', d3)]:
                if d_triple in he_to_idx:
                    daughters.append(he_to_idx[d_triple])
                else:
                    daughters.append(None)
                    n_miss += 1
                    miss_details.append(((c1, c2, c3), d_type, d_triple))
        else:
            daughters = [None, None, None]
            n_miss += 3
            miss_details.append(((c1, c2, c3), 'w_miss', None))

        firing_map[i] = daughters

    return firing_map, he_list, he_to_idx, source_sets, n_miss, miss_details


def build_transfer_matrices(firing_map, he_list, he_to_idx, unique_he, q_psi, q_tier):
    """Build the hyperedge-level and vertex-level transfer matrices.

    Returns:
        T_he_uniform: n_he x n_he counting matrix (T[j,i] = times i fires into j)
        T_he_stoch: column-stochastic version of T_he_uniform
        T_v_uniform: 24x24 vertex transfer (marginalized)
        T_v_born: 24x24 Born-weighted vertex transfer
        he_born_weights: array of mean Born weight per hyperedge
    """
    n_he = len(he_list)
    n_v = len(q_psi)

    # Mean Born weight per hyperedge
    he_born_weights = np.zeros(n_he)
    for i, he in enumerate(he_list):
        bw_list = unique_he[he]
        he_born_weights[i] = np.mean([bw for (_, bw) in bw_list])

    # T_he_uniform: counting matrix
    T_he = np.zeros((n_he, n_he))
    for i, daughters in firing_map.items():
        for d_idx in daughters:
            if d_idx is not None:
                T_he[d_idx, i] += 1

    # Column-stochastic version
    col_sums = T_he.sum(axis=0)
    T_he_stoch = np.zeros_like(T_he)
    for i in range(n_he):
        if col_sums[i] > 0:
            T_he_stoch[:, i] = T_he[:, i] / col_sums[i]

    # Vertex transfer matrix (uniform): marginalize over hyperedge structure
    # T_v[u, v] = sum over all hyperedges containing v (any position) of
    #             (count of daughter hyperedges containing u) / (total daughters from v)
    T_v_uniform = np.zeros((n_v, n_v))
    vertex_daughter_count = np.zeros(n_v)

    for i, he in enumerate(he_list):
        c1, c2, c3 = he
        daughters = firing_map[i]
        for d_idx in daughters:
            if d_idx is not None:
                d_he = he_list[d_idx]
                dc1, dc2, dc3 = d_he
                # Credit each daughter vertex from each source vertex
                for src_v in [c1, c2, c3]:
                    for dst_v in [dc1, dc2, dc3]:
                        T_v_uniform[dst_v, src_v] += 1
                    vertex_daughter_count[src_v] += 3  # 3 vertices in daughter

    # Normalize to column-stochastic
    col_sums_v = T_v_uniform.sum(axis=0)
    for v in range(n_v):
        if col_sums_v[v] > 0:
            T_v_uniform[:, v] /= col_sums_v[v]

    # Born-weighted vertex transfer
    T_v_born = np.zeros((n_v, n_v))
    for i, he in enumerate(he_list):
        c1, c2, c3 = he
        parent_bw = he_born_weights[i]
        daughters = firing_map[i]
        for d_idx in daughters:
            if d_idx is not None:
                d_he = he_list[d_idx]
                dc1, dc2, dc3 = d_he
                daughter_bw = he_born_weights[d_idx]
                weight = parent_bw * daughter_bw
                for src_v in [c1, c2, c3]:
                    for dst_v in [dc1, dc2, dc3]:
                        T_v_born[dst_v, src_v] += weight

    col_sums_vb = T_v_born.sum(axis=0)
    for v in range(n_v):
        if col_sums_vb[v] > 0:
            T_v_born[:, v] /= col_sums_vb[v]

    return T_he, T_he_stoch, T_v_uniform, T_v_born, he_born_weights


# ═══════════════════════════════════════════════════════════════════════════════
# SPECTRAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_spectrum(T, name, q_tier=None):
    """Compute and report eigenvalue spectrum of a transfer matrix."""
    n = T.shape[0]
    eigenvalues = np.linalg.eigvals(T)

    # Sort by magnitude (descending)
    idx = np.argsort(-np.abs(eigenvalues))
    eigenvalues = eigenvalues[idx]

    print(f"\n{'─'*70}")
    print(f"  SPECTRUM OF {name} ({n}x{n})")
    print(f"{'─'*70}")

    # Top eigenvalues
    n_show = min(20, n)
    print(f"\n  Top {n_show} eigenvalues by magnitude:")
    for i in range(n_show):
        ev = eigenvalues[i]
        print(f"    λ_{i:>3d} = {ev.real:>10.6f} + {ev.imag:>10.6f}i  "
              f"(|λ| = {abs(ev):.6f})")

    # Spectral gap
    if len(eigenvalues) >= 2:
        gap = abs(eigenvalues[0]) - abs(eigenvalues[1])
        ratio = abs(eigenvalues[1]) / abs(eigenvalues[0]) if abs(eigenvalues[0]) > 1e-15 else 0
        print(f"\n  Spectral gap: |λ₁| - |λ₂| = {gap:.6f}")
        print(f"  Mixing rate: |λ₂|/|λ₁| = {ratio:.6f}")

    # Check column-stochasticity
    col_sums = T.sum(axis=0)
    cs_min, cs_max = col_sums.min(), col_sums.max()
    print(f"\n  Column sums: min={cs_min:.6f}, max={cs_max:.6f}")

    # Stationary distribution (left eigenvector of eigenvalue 1)
    # For column-stochastic T, the left eigenvector with eigenvalue 1 is
    # the stationary distribution: pi @ T = pi
    eigvals_l, eigvecs_l = np.linalg.eig(T.T)
    stat_idx = np.argmin(np.abs(eigvals_l - 1.0))
    pi = eigvecs_l[:, stat_idx].real
    if pi.sum() != 0:
        pi = np.abs(pi)
        pi = pi / pi.sum()
    else:
        pi = np.ones(n) / n

    print(f"\n  Stationary distribution (top 10):")
    sorted_idx = np.argsort(-pi)
    for i in range(min(10, n)):
        idx_i = sorted_idx[i]
        tier_str = f" (Tier {q_tier[idx_i]})" if q_tier and idx_i in q_tier else ""
        print(f"    π[{idx_i:>3d}]{tier_str} = {pi[idx_i]:.6f}")

    # Check irreducibility
    # A matrix is irreducible if (I + T)^(n-1) has all positive entries
    test_mat = np.eye(n) + np.abs(T)
    power = np.linalg.matrix_power(test_mat, n - 1)
    is_irreducible = np.all(power > 1e-15)
    print(f"\n  Irreducible (single communicating class): {is_irreducible}")

    # Count zero rows/columns
    zero_rows = np.sum(np.all(np.abs(T) < 1e-15, axis=1))
    zero_cols = np.sum(np.all(np.abs(T) < 1e-15, axis=0))
    print(f"  Zero rows: {zero_rows}, Zero columns: {zero_cols}")

    return eigenvalues, pi


def analyse_stationary_vs_born(pi_v, he_born_weights, he_list, q_psi, q_tier, name):
    """Compare vertex stationary distribution to Born vertex potentials."""
    n_v = len(q_psi)

    # Born vertex potential: sum of Born weights over all hyperedges touching vertex
    born_potential = np.zeros(n_v)
    for i, (c1, c2, c3) in enumerate(he_list):
        bw = he_born_weights[i]
        born_potential[c1] += bw
        born_potential[c2] += bw
        born_potential[c3] += bw

    # Normalize
    born_norm = born_potential / born_potential.sum() if born_potential.sum() > 0 else born_potential

    print(f"\n{'─'*70}")
    print(f"  STATIONARY vs BORN ({name})")
    print(f"{'─'*70}")

    # Per-vertex comparison
    print(f"\n  {'Vertex':>8} {'Tier':>6} {'π_stat':>10} {'π_Born':>10} {'Ratio':>10}")
    print(f"  {'─'*50}")
    for v in range(n_v):
        tier = q_tier.get(v, '?')
        ratio = pi_v[v] / born_norm[v] if born_norm[v] > 1e-15 else float('inf')
        print(f"  {v:>8d} {tier:>6} {pi_v[v]:>10.6f} {born_norm[v]:>10.6f} {ratio:>10.4f}")

    # Correlation
    if np.std(pi_v) > 1e-15 and np.std(born_norm) > 1e-15:
        corr = np.corrcoef(pi_v, born_norm)[0, 1]
    else:
        corr = 0.0

    # L1 distance
    l1 = np.sum(np.abs(pi_v - born_norm))

    # Per-tier comparison
    tiers = ['A', 'B', 'C_even', 'C_odd']
    print(f"\n  Per-tier stationary mass vs Born mass:")
    print(f"  {'Tier':>8} {'π_stat':>10} {'π_Born':>10} {'Ratio':>10}")
    for t in tiers:
        vids = [v for v in range(n_v) if q_tier.get(v) == t]
        pi_t = sum(pi_v[v] for v in vids)
        born_t = sum(born_norm[v] for v in vids)
        ratio = pi_t / born_t if born_t > 1e-15 else float('inf')
        print(f"  {t:>8} {pi_t:>10.6f} {born_t:>10.6f} {ratio:>10.4f}")

    print(f"\n  Pearson correlation (π_stat, π_Born): {corr:.6f}")
    print(f"  L1 distance: {l1:.6f}")
    print(f"  Match verdict: {'MATCH' if l1 < 0.05 else 'MISMATCH (L1 > 0.05)'}")

    return corr, l1, born_norm


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE SET ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_source_sets(source_sets, q_tier, n_clusters):
    """Analyse the source sets: which (c1, c2) pairs compose to each vertex."""
    print(f"\n{'─'*70}")
    print(f"  SOURCE SETS (who composes to whom)")
    print(f"{'─'*70}")

    # Deduplicate source pairs per vertex (same pair may appear from multiple parent HEs)
    unique_sources = {}
    for v in range(n_clusters):
        pairs = set()
        for (c1, c2, _parent_he) in source_sets.get(v, []):
            pairs.add((c1, c2))
        unique_sources[v] = sorted(pairs)

    # Count by tier
    tier_source_counts = defaultdict(list)
    for v in range(n_clusters):
        tier = q_tier.get(v, '?')
        tier_source_counts[tier].append(len(unique_sources[v]))

    print(f"\n  Source pair counts by tier:")
    print(f"  {'Tier':>8} {'Mean':>8} {'Min':>6} {'Max':>6} {'Counts':>20}")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        counts = tier_source_counts[t]
        if counts:
            print(f"  {t:>8} {np.mean(counts):>8.1f} {min(counts):>6d} {max(counts):>6d} {counts}")

    # Detailed listing for small sets
    print(f"\n  Detailed source sets (vertex: tier, n_pairs):")
    for v in range(n_clusters):
        tier = q_tier.get(v, '?')
        pairs = unique_sources[v]
        pair_strs = [f"({c1},{c2})" for c1, c2 in pairs]
        print(f"    v{v:>2d} ({tier:>6}): {len(pairs):>2d} pairs: {', '.join(pair_strs[:8])}"
              f"{'...' if len(pair_strs) > 8 else ''}")

    return unique_sources


# ═══════════════════════════════════════════════════════════════════════════════
# FIRING MAP TOPOLOGY CHECK
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_firing_topology(firing_map, he_list, q_tier, n_ic, rng_seed):
    """Check whether the firing map topology is IC-independent."""
    print(f"\n{'─'*70}")
    print(f"  IC-INDEPENDENCE OF FIRING MAP TOPOLOGY ({n_ic} ICs)")
    print(f"{'─'*70}")

    # The reference topology is from the first IC (already computed)
    ref_n_he = len(he_list)

    # Track: n_clusters, n_he, firing map structure
    results = []

    for ic in range(n_ic):
        rng = np.random.default_rng(rng_seed + ic + 1000)
        q_psi_i, q_tier_i, unique_he_i, _, tier_info_i, n_clusters_i = build_Q24(rng, depth=5)
        he_list_i = sorted(unique_he_i.keys())
        n_he_i = len(he_list_i)

        # Build firing map for this IC
        fm_i, _, _, _, n_miss_i, _ = build_firing_map(q_psi_i, unique_he_i)

        # Count column sums of transfer matrix (how many valid daughters per HE)
        valid_daughters = []
        for idx, daughters in fm_i.items():
            n_valid = sum(1 for d in daughters if d is not None)
            valid_daughters.append(n_valid)

        # Tier distribution of hyperedges
        tier_patterns = Counter()
        for (c1, c2, c3) in he_list_i:
            pat = (q_tier_i[c1], q_tier_i[c2], q_tier_i[c3])
            tier_patterns[pat] += 1

        results.append({
            'ic': ic,
            'n_clusters': n_clusters_i,
            'n_he': n_he_i,
            'n_miss': n_miss_i,
            'mean_valid': np.mean(valid_daughters),
            'min_valid': min(valid_daughters),
            'max_valid': max(valid_daughters),
            'n_tier_patterns': len(tier_patterns),
        })

    # Report
    n_clusters_vals = [r['n_clusters'] for r in results]
    n_he_vals = [r['n_he'] for r in results]
    n_miss_vals = [r['n_miss'] for r in results]
    mean_valid_vals = [r['mean_valid'] for r in results]

    print(f"\n  n_clusters: {min(n_clusters_vals)}–{max(n_clusters_vals)} "
          f"(all 24: {all(v == 24 for v in n_clusters_vals)})")
    print(f"  n_hyperedges: {min(n_he_vals)}–{max(n_he_vals)} "
          f"(all {ref_n_he}: {all(v == ref_n_he for v in n_he_vals)})")
    print(f"  n_miss (daughters not in Q24): {min(n_miss_vals)}–{max(n_miss_vals)}")
    print(f"  mean valid daughters/HE: {np.mean(mean_valid_vals):.3f} "
          f"(range {min(mean_valid_vals):.3f}–{max(mean_valid_vals):.3f})")

    ic_independent = all(v == 24 for v in n_clusters_vals) and \
                     all(v == ref_n_he for v in n_he_vals)
    print(f"\n  Topology IC-independent (n_clusters, n_he): {ic_independent}")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# TIER STRUCTURE IN EIGENVECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_eigenvector_tiers(T_v, q_tier, n_v, name):
    """Check whether eigenvectors of T_v separate by tier."""
    print(f"\n{'─'*70}")
    print(f"  EIGENVECTOR TIER STRUCTURE ({name})")
    print(f"{'─'*70}")

    eigenvalues, eigenvectors = np.linalg.eig(T_v)
    idx = np.argsort(-np.abs(eigenvalues))
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    tiers = ['A', 'B', 'C_even', 'C_odd']
    tier_vids = {t: [v for v in range(n_v) if q_tier.get(v) == t] for t in tiers}

    print(f"\n  Top 10 eigenvectors — tier-decomposed L2 norm:")
    print(f"  {'λ':>6} {'|λ|':>8} {'A':>8} {'B':>8} {'C_even':>8} {'C_odd':>8} {'Dominant':>10}")
    for i in range(min(10, n_v)):
        ev = eigenvectors[:, i]
        ev_norm = np.abs(ev)
        tier_norms = {}
        for t in tiers:
            tier_norms[t] = np.linalg.norm(ev_norm[tier_vids[t]])
        total = sum(tier_norms.values())
        if total > 1e-15:
            tier_frac = {t: tier_norms[t] / total for t in tiers}
        else:
            tier_frac = {t: 0 for t in tiers}

        dominant = max(tier_frac, key=tier_frac.get)
        print(f"  {eigenvalues[i].real:>6.3f} {abs(eigenvalues[i]):>8.4f} "
              f"{tier_frac['A']:>8.3f} {tier_frac['B']:>8.3f} "
              f"{tier_frac['C_even']:>8.3f} {tier_frac['C_odd']:>8.3f} "
              f"{dominant:>10}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Q₂₄ Transfer Operator')
    parser.add_argument('--n_ic', type=int, default=50, help='Number of ICs for topology check')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--depth', type=int, default=5, help='Multiway depth')
    args = parser.parse_args()

    t0 = time.time()
    rng = np.random.default_rng(args.seed)

    # ── Step 1: Build Q₂₄ ────────────────────────────────────────────────────
    print("=" * 70)
    print("  Q₂₄ TRANSFER OPERATOR — SESSION 1")
    print("=" * 70)

    q_psi, q_tier, unique_he, vertex_to_cluster, tier_info, n_clusters = build_Q24(rng, args.depth)
    he_list = sorted(unique_he.keys())
    n_he = len(he_list)

    print(f"\n  Q₂₄ built: {n_clusters} clusters, {n_he} unique hyperedges")
    for t in ['A', 'B', 'C_even', 'C_odd']:
        vids = tier_info[t]
        print(f"    Tier {t}: {len(vids)} vertices — {vids}")

    # ── Step 2: Build firing map ──────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  FIRING MAP CONSTRUCTION")
    print("=" * 70)

    firing_map, he_list, he_to_idx, source_sets, n_miss, miss_details = \
        build_firing_map(q_psi, unique_he)

    n_valid = sum(sum(1 for d in daughters if d is not None) for daughters in firing_map.values())
    n_total = 3 * n_he

    print(f"\n  Fired {n_he} hyperedges → {n_total} daughter slots")
    print(f"  Valid daughters (map to Q₂₄ HE): {n_valid} / {n_total} ({100*n_valid/n_total:.1f}%)")
    print(f"  Missing daughters: {n_miss}")

    if n_miss > 0:
        print(f"\n  MISS DETAILS (first 20):")
        for parent_he, d_type, d_triple in miss_details[:20]:
            print(f"    Parent {parent_he} → {d_type}: {d_triple}")

    # Fixed-point check
    fixed_point = (n_miss == 0)
    print(f"\n  *** FIXED-POINT CHECK: {'PASS' if fixed_point else 'FAIL'} "
          f"(all daughters in Q₂₄: {fixed_point}) ***")

    # ── Step 3: Source set analysis ───────────────────────────────────────────
    unique_sources = analyse_source_sets(source_sets, q_tier, n_clusters)

    # ── Step 4: Build transfer matrices ───────────────────────────────────────
    print(f"\n{'='*70}")
    print("  TRANSFER MATRIX CONSTRUCTION")
    print("=" * 70)

    T_he, T_he_stoch, T_v_uniform, T_v_born, he_born_weights = \
        build_transfer_matrices(firing_map, he_list, he_to_idx, unique_he, q_psi, q_tier)

    print(f"\n  T_he (hyperedge): {T_he.shape}")
    print(f"    Column sums: min={T_he.sum(axis=0).min():.1f}, max={T_he.sum(axis=0).max():.1f}")
    print(f"    Non-zero entries: {np.count_nonzero(T_he)}")
    print(f"    Sparsity: {1 - np.count_nonzero(T_he)/(n_he**2):.3f}")

    print(f"\n  T_v_uniform (vertex): {T_v_uniform.shape}")
    print(f"    Column sums: min={T_v_uniform.sum(axis=0).min():.4f}, "
          f"max={T_v_uniform.sum(axis=0).max():.4f}")

    print(f"\n  T_v_born (vertex, Born-weighted): {T_v_born.shape}")
    print(f"    Column sums: min={T_v_born.sum(axis=0).min():.4f}, "
          f"max={T_v_born.sum(axis=0).max():.4f}")

    # ── Step 5: Spectral analysis ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  SPECTRAL ANALYSIS")
    print("=" * 70)

    # Vertex-level spectra (more interpretable than 330x330)
    ev_uniform, pi_uniform = analyse_spectrum(T_v_uniform, "T_v_uniform (24x24)", q_tier)
    ev_born, pi_born = analyse_spectrum(T_v_born, "T_v_born (24x24)", q_tier)

    # Hyperedge-level spectrum (just top eigenvalues)
    ev_he, pi_he = analyse_spectrum(T_he_stoch, "T_he_stoch (column-stochastic)", None)

    # ── Step 6: Stationary vs Born ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  STATIONARY DISTRIBUTION vs BORN WEIGHTS")
    print("=" * 70)

    corr_u, l1_u, born_norm = analyse_stationary_vs_born(
        pi_uniform, he_born_weights, he_list, q_psi, q_tier, "T_v_uniform")

    corr_b, l1_b, _ = analyse_stationary_vs_born(
        pi_born, he_born_weights, he_list, q_psi, q_tier, "T_v_born")

    # ── Step 7: Eigenvector tier structure ────────────────────────────────────
    analyse_eigenvector_tiers(T_v_uniform, q_tier, n_clusters, "T_v_uniform")
    analyse_eigenvector_tiers(T_v_born, q_tier, n_clusters, "T_v_born")

    # ── Step 8: IC-independence ───────────────────────────────────────────────
    ic_results = analyse_firing_topology(firing_map, he_list, q_tier, args.n_ic, args.seed)

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  Q₂₄: {n_clusters} vertices, {n_he} hyperedges")
    print(f"  Fixed-point (all daughters in Q₂₄): {'YES' if fixed_point else 'NO'}")
    print(f"  Valid daughters: {n_valid}/{n_total} ({100*n_valid/n_total:.1f}%)")
    print(f"\n  Stationary vs Born (T_v_uniform):")
    print(f"    Correlation: {corr_u:.4f}")
    print(f"    L1 distance: {l1_u:.4f}")
    print(f"  Stationary vs Born (T_v_born):")
    print(f"    Correlation: {corr_b:.4f}")
    print(f"    L1 distance: {l1_b:.4f}")
    print(f"\n  Top eigenvalues:")
    print(f"    T_v_uniform: λ₁={ev_uniform[0].real:.4f}, λ₂={ev_uniform[1].real:.4f}, "
          f"|λ₂/λ₁|={abs(ev_uniform[1]/ev_uniform[0]):.4f}")
    print(f"    T_v_born:    λ₁={ev_born[0].real:.4f}, λ₂={ev_born[1].real:.4f}, "
          f"|λ₂/λ₁|={abs(ev_born[1]/ev_born[0]):.4f}")
    print(f"\n  IC-independence: all {args.n_ic} ICs give 24 clusters: "
          f"{all(r['n_clusters'] == 24 for r in ic_results)}")
    print(f"\n  Elapsed: {elapsed:.1f}s")


if __name__ == '__main__':
    main()
