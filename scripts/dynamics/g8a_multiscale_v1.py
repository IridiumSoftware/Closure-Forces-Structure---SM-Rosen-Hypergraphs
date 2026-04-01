#!/usr/bin/env python3
"""
g8a_multiscale_v1.py — Mass gap across Q_n: multi-scale comparison

Computes the transfer operator and mass gap for quotient graphs at
different initial topologies (graph densities):

  Q₂₄: from G₀ (6 cyclic edges, sparse)
  Q_n:  from K₆³ subsets at intermediate densities
  Q₅₁: from K₆³ (120 ordered triples, complete)

If the mass gap varies with density, that variation IS the running
of the coupling (G6a connection). If it's stable, the mass gap is
a resolution-independent invariant.

Mathematical conventions:
  Same as g8a_mass_gap_v1.py — see that file header.
  K₆³ = complete_ternary(6) = all 120 ordered triples of distinct
  elements from {0,1,2,3,4,5}.
  G₀ = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)] (cyclic hexagon).

Usage: python g8a_multiscale_v1.py [--n_ic N] [--seed S]
"""

import numpy as np
from collections import defaultdict, deque
import itertools

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ALGEBRA (same as g8a_mass_gap_v1.py)
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

def fidelity(a, b):
    return abs(np.vdot(a, b))**2


# ═══════════════════════════════════════════════════════════════════════════════
# TOPOLOGIES
# ═══════════════════════════════════════════════════════════════════════════════

def G0_cyclic():
    """G₀: cyclic hexagon, 6 edges."""
    return [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

def complete_ternary(n):
    """K_n³: all ordered triples of distinct elements from {0,...,n-1}."""
    return [(i,j,k) for i in range(n) for j in range(n) if j!=i
            for k in range(n) if k!=i and k!=j]

def adjacent_ternary():
    """Adjacent triples: (i, i+1 mod 6, i+2 mod 6) and all permutations.
    Intermediate density between G₀ (6 edges) and K₆³ (120 edges)."""
    edges = set()
    for i in range(6):
        triple = (i, (i+1)%6, (i+2)%6)
        for p in itertools.permutations(triple):
            edges.add(p)
    return list(edges)

def stride2_ternary():
    """Stride-2 triples: (i, i+2 mod 6, i+4 mod 6) and all permutations.
    These are the non-adjacent triples that generate Q₅₁'s extra 27 vertices."""
    edges = set()
    for i in range(6):
        triple = (i, (i+2)%6, (i+4)%6)
        for p in itertools.permutations(triple):
            edges.add(p)
    return list(edges)

def combined_adjacent_stride2():
    """Union of adjacent and stride-2 triples."""
    return list(set(adjacent_ternary()) | set(stride2_ternary()))


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD QUOTIENT (generalized for any topology)
# ═══════════════════════════════════════════════════════════════════════════════

def build_quotient(seed_edges, rng, depth=5, n_verts=6):
    """Build gauge-equivalence quotient for arbitrary seed topology."""
    psi = {}
    for v in range(n_verts):
        psi[v] = haar_C3(rng)

    next_vid = n_verts
    vertex_gen = {v: 0 for v in range(n_verts)}
    edges = [(0, s1, s2, s3) for s1, s2, s3 in seed_edges]
    compose_cache = {}

    for gen in range(depth):
        parent_edges = [(i, e) for i, e in enumerate(edges) if e[0] == gen]
        for idx, (d, v1, v2, v3) in parent_edges:
            key = (v1, v2)
            if key not in compose_cache:
                psi_new = compose_colour(psi[v1], psi[v2])
                if np.linalg.norm(psi_new) < 1e-10:
                    continue
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
    n_raw = len(all_vids)

    clusters = []
    vid_to_cid = {}
    THRESHOLD = 0.999

    for v in all_vids:
        matched = False
        for ci, (rep_v, rep_psi) in enumerate(clusters):
            if fidelity(psi[v], rep_psi) > THRESHOLD:
                vid_to_cid[v] = ci
                matched = True
                break
        if not matched:
            vid_to_cid[v] = len(clusters)
            clusters.append((v, psi[v]))

    n_cl = len(clusters)
    q_psi = {i: clusters[i][1] for i in range(n_cl)}

    # Tier assignment
    orig_cids = set(vid_to_cid[v] for v in range(n_verts))
    gen1_cids = set()
    for v in all_vids:
        if vertex_gen.get(v, 0) == 1:
            c = vid_to_cid[v]
            if c not in orig_cids:
                gen1_cids.add(c)

    q_tier = {}
    for c in range(n_cl):
        if c in orig_cids:
            q_tier[c] = 'A'
        elif c in gen1_cids:
            q_tier[c] = 'B'
        else:
            q_tier[c] = 'C'

    # Hyperedges
    unique_he = defaultdict(list)
    for (d, v1, v2, v3) in edges:
        if v1 in vid_to_cid and v2 in vid_to_cid and v3 in vid_to_cid:
            c1, c2, c3 = vid_to_cid[v1], vid_to_cid[v2], vid_to_cid[v3]
            unique_he[(c1, c2, c3)].append(d)

    return q_psi, q_tier, dict(unique_he), n_cl


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFER OPERATOR (same logic as g8a_mass_gap_v1.py)
# ═══════════════════════════════════════════════════════════════════════════════

def find_cluster_map(psi_new, q_psi, threshold=0.999):
    best_cid, best_fid = None, 0.0
    for cid, psi_rep in q_psi.items():
        f = fidelity(psi_new, psi_rep)
        if f > best_fid:
            best_fid = f
            best_cid = cid
    return best_cid if best_fid > threshold else None


def build_transfer(q_psi, q_tier, unique_he, n_v):
    """Build vertex-level transfer operator."""
    he_list = sorted(unique_he.keys())
    he_to_idx = {he: i for i, he in enumerate(he_list)}

    # Firing map
    firing_map = {}
    n_miss = 0
    for i, (c1, c2, c3) in enumerate(he_list):
        w_psi = compose_colour(q_psi[c1], q_psi[c2])
        w_cid = find_cluster_map(w_psi, q_psi)
        daughters = []
        if w_cid is not None:
            for d_triple in [(w_cid, c2, c3), (w_cid, c1, c3), (w_cid, c1, c2)]:
                if d_triple in he_to_idx:
                    daughters.append(he_to_idx[d_triple])
                else:
                    daughters.append(None)
                    n_miss += 1
        else:
            daughters = [None, None, None]
            n_miss += 3
        firing_map[i] = daughters

    # Vertex transfer matrix
    T_v = np.zeros((n_v, n_v))
    for i, he in enumerate(he_list):
        c1, c2, c3 = he
        for d_idx in firing_map[i]:
            if d_idx is not None:
                d_he = he_list[d_idx]
                for src_v in [c1, c2, c3]:
                    for dst_v in d_he:
                        T_v[dst_v, src_v] += 1

    # Column-stochastic
    col_sums = T_v.sum(axis=0)
    for v in range(n_v):
        if col_sums[v] > 0:
            T_v[:, v] /= col_sums[v]

    closure_rate = 1.0 - n_miss / (3 * len(he_list)) if he_list else 0
    return T_v, len(he_list), n_miss, closure_rate


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_quotient(name, seed_edges, rng, depth=5, n_verts=6):
    """Build quotient, transfer operator, and extract mass gap."""
    q_psi, q_tier, unique_he, n_v = build_quotient(seed_edges, rng, depth, n_verts)

    T_v, n_he, n_miss, closure_rate = build_transfer(q_psi, q_tier, unique_he, n_v)

    # Eigenvalues
    eigvals = np.linalg.eigvals(T_v)
    idx = np.argsort(-np.abs(eigvals))
    eigvals = eigvals[idx]

    lam0 = abs(eigvals[0])
    lam1 = abs(eigvals[1]) if len(eigvals) > 1 else 0

    spectral_gap = lam0 - lam1
    mass_gap = -np.log(lam1 / lam0) if lam1 > 0 and lam0 > 0 else float('inf')
    corr_length = 1.0 / mass_gap if mass_gap > 0 else float('inf')

    # Stationary distribution (right eigenvector of λ=1)
    v_R = np.linalg.eig(T_v)[1][:, idx[0]].real
    v_R = v_R / v_R.sum()

    # Tier weights
    tiers = {'A': [], 'B': [], 'C': []}
    for c in range(n_v):
        tiers[q_tier[c]].append(c)
    tier_weights = {t: sum(v_R[c] for c in cids) for t, cids in tiers.items()}

    # Irreducibility check
    test = np.eye(n_v) + np.abs(T_v)
    power = np.linalg.matrix_power(test, min(n_v - 1, 100))
    is_irred = np.all(power > 1e-15)

    # Graph diameter
    adj = defaultdict(set)
    for (c1, c2, c3) in unique_he.keys():
        adj[c1].add(c2); adj[c1].add(c3)
        adj[c2].add(c1); adj[c2].add(c3)
        adj[c3].add(c1); adj[c3].add(c2)

    diameter = 0
    for src in range(n_v):
        dist = {src: 0}
        queue = deque([src])
        while queue:
            v = queue.popleft()
            for u in adj[v]:
                if u not in dist:
                    dist[u] = dist[v] + 1
                    queue.append(u)
        if dist:
            diameter = max(diameter, max(dist.values()))

    return {
        'name': name,
        'n_v': n_v,
        'n_he': n_he,
        'n_seed': len(seed_edges),
        'n_miss': n_miss,
        'closure_rate': closure_rate,
        'spectral_gap': spectral_gap,
        'mass_gap': mass_gap,
        'corr_length': corr_length,
        'lam0': lam0,
        'lam1': lam1,
        'lam2': abs(eigvals[2]) if len(eigvals) > 2 else 0,
        'eigvals': eigvals,
        'is_irreducible': is_irred,
        'diameter': diameter,
        'tier_counts': {t: len(cids) for t, cids in tiers.items()},
        'tier_weights': tier_weights,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_ic', type=int, default=5)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--depth', type=int, default=4)
    args = parser.parse_args()

    print("═"*75)
    print("  G8a MULTI-SCALE MASS GAP — Transfer Operator Across Q_n")
    print("═"*75)
    print(f"  ICs: {args.n_ic}  |  Seed: {args.seed}  |  Depth: {args.depth}")

    # Define topologies to test
    topologies = [
        ("G₀ (cyclic, 6 edges)", G0_cyclic()),
        ("Adjacent (36 edges)", adjacent_ternary()),
        ("Adj+Stride2 (48 edges)", combined_adjacent_stride2()),
        ("K₆³ (complete, 120 edges)", complete_ternary(6)),
    ]

    # Collect results across ICs
    all_results = {name: [] for name, _ in topologies}

    for ic in range(args.n_ic):
        rng = np.random.default_rng(args.seed + ic)
        # Same ICs for all topologies (fair comparison)
        psi_init = [haar_C3(rng) for _ in range(6)]

        for topo_name, seed_edges in topologies:
            # Reset RNG state for consistent clustering (use same ICs)
            rng_build = np.random.default_rng(args.seed + ic)
            result = analyse_quotient(topo_name, seed_edges, rng_build, args.depth)
            all_results[topo_name].append(result)

    # Print results
    print(f"\n{'─'*75}")
    print(f"  {'Topology':<30s}  {'|Q|':>5s}  {'|HE|':>6s}  {'close':>6s}  "
          f"{'|λ₁|':>8s}  {'gap':>8s}  {'m':>8s}  {'ξ':>8s}  {'diam':>5s}")
    print(f"{'─'*75}")

    for topo_name, _ in topologies:
        results = all_results[topo_name]
        # Check IC-independence
        n_vs = [r['n_v'] for r in results]
        gaps = [r['spectral_gap'] for r in results]
        masses = [r['mass_gap'] for r in results]
        lam1s = [r['lam1'] for r in results]

        n_v_unique = len(set(n_vs))
        gap_cv = np.std(gaps)/np.mean(gaps) if np.mean(gaps) > 0 else 0
        mass_cv = np.std(masses)/np.mean(masses) if np.mean(masses) > 0 else 0

        r = results[0]  # representative
        ic_tag = "✓" if gap_cv < 0.01 else f"CV={gap_cv:.3f}"

        print(f"  {topo_name:<30s}  {r['n_v']:>5d}  {r['n_he']:>6d}  "
              f"{r['closure_rate']:>5.1%}  {np.mean(lam1s):>8.4f}  "
              f"{np.mean(gaps):>8.4f}  {np.mean(masses):>8.4f}  "
              f"{np.mean([r2['corr_length'] for r2 in results]):>8.2f}  "
              f"{r['diameter']:>5d}  {ic_tag}")

    # Detailed comparison
    print(f"\n{'═'*75}")
    print(f"  DETAILED COMPARISON (IC 0)")
    print(f"{'═'*75}")

    for topo_name, _ in topologies:
        r = all_results[topo_name][0]
        print(f"\n  {r['name']}")
        print(f"    Vertices: {r['n_v']}  |  Hyperedges: {r['n_he']}  |  "
              f"Seed edges: {r['n_seed']}  |  Closure: {r['closure_rate']:.1%}")
        print(f"    Irreducible: {r['is_irreducible']}  |  Diameter: {r['diameter']}")
        print(f"    Tiers: A={r['tier_counts']['A']}, B={r['tier_counts']['B']}, "
              f"C={r['tier_counts']['C']}")
        print(f"    Stationary weights: A={r['tier_weights']['A']:.3f}, "
              f"B={r['tier_weights']['B']:.3f}, C={r['tier_weights']['C']:.3f}")
        print(f"    Top eigenvalues:")
        for i in range(min(8, len(r['eigvals']))):
            ev = r['eigvals'][i]
            print(f"      λ_{i} = {ev.real:+.6f} {ev.imag:+.6f}i  (|λ|={abs(ev):.6f})")
        print(f"    Spectral gap: {r['spectral_gap']:.6f}")
        print(f"    Mass gap m:   {r['mass_gap']:.6f}")
        print(f"    Corr length:  {r['corr_length']:.3f}")

    # IC-independence summary
    print(f"\n{'═'*75}")
    print(f"  IC-INDEPENDENCE")
    print(f"{'═'*75}")
    for topo_name, _ in topologies:
        results = all_results[topo_name]
        n_vs = [r['n_v'] for r in results]
        gaps = np.array([r['spectral_gap'] for r in results])
        masses = np.array([r['mass_gap'] for r in results])
        gap_cv = np.std(gaps)/np.mean(gaps) if np.mean(gaps) > 0 else 0
        mass_cv = np.std(masses)/np.mean(masses) if np.mean(masses) > 0 else 0
        n_v_set = sorted(set(n_vs))
        print(f"  {topo_name:<30s}  |Q| = {n_v_set}  "
              f"gap CV = {gap_cv:.6f}  mass CV = {mass_cv:.6f}")

    # Multi-scale summary
    print(f"\n{'═'*75}")
    print(f"  MULTI-SCALE MASS GAP SUMMARY")
    print(f"{'═'*75}")
    print(f"\n  {'Topology':<30s}  {'density':>8s}  {'m':>8s}  {'Δm/m vs G₀':>12s}")

    m_g0 = np.mean([r['mass_gap'] for r in all_results[topologies[0][0]]])
    for topo_name, edges in topologies:
        results = all_results[topo_name]
        m = np.mean([r['mass_gap'] for r in results])
        density = len(edges) / 120.0  # fraction of K₆³
        delta = (m - m_g0) / m_g0 * 100 if m_g0 > 0 else 0
        print(f"  {topo_name:<30s}  {density:>7.1%}  {m:>8.4f}  {delta:>+11.1f}%")

    print(f"\n  If Δm/m is small: mass gap is scale-invariant (resolution-independent)")
    print(f"  If Δm/m varies:  the variation is the discrete running of the coupling")


if __name__ == '__main__':
    main()
