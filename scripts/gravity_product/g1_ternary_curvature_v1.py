#!/usr/bin/env python3
"""
g1_ternary_curvature_v1.py — G1: Ternary-Aware Curvature on Q₂₄

The simple-graph Ollivier-Ricci (Session 4) gives κ ≈ +0.1. Prior work
reported κ ≈ −10. The discrepancy is in the curvature definition.

This session defines a TERNARY walk measure on Q₂₄ that respects the
3→1 composition structure, then computes Ollivier-Ricci on this measure.

The key test: does Born-weighted ternary curvature correlate with
Born weight itself? If κ_ternary ∝ μ_Born, that's a discrete
Einstein equation (curvature = stress-energy).

Diagnostics:
  A. Define the ternary walk: from vertex v, which vertices are
     reachable by one composition step (v as pos1 or pos2)?
  B. Compute ternary Ollivier-Ricci on Q₂₄
  C. Born-weighted ternary walk and curvature
  D. Discrete Einstein test: κ vs Born weight
  E. Tier decomposition
  F. Compare with simple-graph ORC

Usage:
  python3 g1_ternary_curvature_v1.py [--seed S]
"""

import numpy as np
import argparse
import time
from collections import defaultdict, Counter
from scipy.optimize import linprog

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
    return normalize(rng.standard_normal(3) + 1j * rng.standard_normal(3))

def fidelity(a, b):
    return abs(np.vdot(a, b))**2

def born_weight(psi1, psi2, psi3, depth):
    if depth % 2 == 1:
        pt1, pt2, pt3 = np.conj(psi1), np.conj(psi2), psi3.copy()
    else:
        pt1, pt2, pt3 = psi1.copy(), psi2.copy(), np.conj(psi3)
    M = np.column_stack([pt1, pt2, pt3])
    return abs(np.linalg.det(M))**2

G0_TOPO = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₂₄ WITH FULL HYPEREDGE AND BORN DATA
# ═══════════════════════════════════════════════════════════════════════════════

def build_Q24_full(rng, depth=5):
    psi = {v: haar_C3(rng) for v in range(6)}
    next_vid = 6
    vertex_depth = {v: 0 for v in range(6)}
    edges = [(0, s1, s2, s3) for s1, s2, s3 in G0_TOPO]
    compose_cache = {}

    for d in range(depth):
        for _, v1, v2, v3 in [e for e in edges if e[0] == d]:
            key = (v1, v2)
            if key not in compose_cache:
                psi[next_vid] = compose_colour(psi[v1], psi[v2])
                compose_cache[key] = next_vid
                vertex_depth[next_vid] = d + 1
                next_vid += 1
            w = compose_cache[key]
            edges.append((d+1, w, v2, v3))
            edges.append((d+1, w, v1, v3))
            edges.append((d+1, w, v1, v2))

    # Quotient
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
        if px != py: parent_uf[px] = py

    THRESHOLD = 0.999
    psi_arr = np.array([psi[v] for v in all_vids])
    G = psi_arr @ psi_arr.conj().T
    fid_matrix = np.abs(G)**2
    for i in range(n_verts):
        for j in range(i+1, n_verts):
            if fid_matrix[i, j] > THRESHOLD: union(i, j)

    cluster_map = defaultdict(list)
    for v in all_vids:
        cluster_map[find(vid_to_idx[v])].append(v)
    cluster_roots = sorted(cluster_map.keys())
    root_to_cid = {r: i for i, r in enumerate(cluster_roots)}
    vtx_to_cid = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        for v in vids: vtx_to_cid[v] = cid
    n_cl = len(cluster_roots)

    q_psi = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        earliest = min(vids, key=lambda v: vertex_depth[v])
        q_psi[cid] = psi[earliest]

    # Tiers
    orig = set(vtx_to_cid[v] for v in range(6))
    gen1 = set()
    for v, d in vertex_depth.items():
        if d == 1:
            c = vtx_to_cid[v]
            if c not in orig: gen1.add(c)
    remaining = set(range(n_cl)) - orig - gen1
    cl_earliest = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        cl_earliest[cid] = min(vertex_depth[v] for v in vids)
    q_tier = {}
    for c in orig: q_tier[c] = 'A'
    for c in gen1: q_tier[c] = 'B'
    for c in remaining:
        q_tier[c] = 'C_even' if cl_earliest[c] % 2 == 0 else 'C_odd'

    # Hyperedges with Born weights (quotient level)
    unique_he = defaultdict(list)
    for depth_e, v1, v2, v3 in edges:
        c1, c2, c3 = vtx_to_cid[v1], vtx_to_cid[v2], vtx_to_cid[v3]
        bw = born_weight(psi[v1], psi[v2], psi[v3], depth_e)
        unique_he[(c1, c2, c3)].append((depth_e, bw))

    he_born = {he: np.mean([bw for _, bw in unique_he[he]]) for he in unique_he}

    # Firing map: which cluster does compose(c1, c2) produce?
    firing = {}
    for (c1, c2, c3) in unique_he:
        if (c1, c2) not in firing:
            w_psi = compose_colour(q_psi[c1], q_psi[c2])
            if np.linalg.norm(w_psi) > 1e-10:
                best_cid, best_fid = None, 0
                for cid in range(n_cl):
                    f = fidelity(w_psi, q_psi[cid])
                    if f > best_fid: best_fid, best_cid = f, cid
                if best_fid > 0.999:
                    firing[(c1, c2)] = best_cid

    # Simple adjacency
    adj = np.zeros((n_cl, n_cl))
    for (c1, c2, c3) in unique_he:
        adj[c1,c2]=1;adj[c2,c1]=1;adj[c1,c3]=1
        adj[c3,c1]=1;adj[c2,c3]=1;adj[c3,c2]=1
    np.fill_diagonal(adj, 0)

    return n_cl, q_psi, q_tier, unique_he, he_born, firing, adj


# ═══════════════════════════════════════════════════════════════════════════════
# TERNARY WALK MEASURE
# ═══════════════════════════════════════════════════════════════════════════════

def ternary_walk_measure(v, unique_he, he_born, firing, n_cl, born_weighted=False):
    """From vertex v, the ternary walk measure μ_v gives probability of
    reaching each other vertex via one composition step.

    v can appear as:
    - pos1 in edge (v, c2, c3) → compose(v, c2) = w
    - pos2 in edge (c1, v, c3) → compose(c1, v) = w

    Each such step reaches vertex w with weight 1 (or Born weight if weighted).
    """
    mu = np.zeros(n_cl)

    for (c1, c2, c3), bw in he_born.items():
        weight = bw if born_weighted else 1.0

        if c1 == v and (c1, c2) in firing:
            w = firing[(c1, c2)]
            mu[w] += weight
        if c2 == v and (c1, c2) in firing:
            w = firing[(c1, c2)]
            mu[w] += weight

    total = np.sum(mu)
    if total > 1e-15:
        mu /= total
    return mu


def compute_W1(mu_x, mu_y, dist):
    """Earth mover's distance between two distributions."""
    n = len(mu_x)
    supp_x = np.where(mu_x > 1e-15)[0]
    supp_y = np.where(mu_y > 1e-15)[0]

    if len(supp_x) == 0 or len(supp_y) == 0:
        return 0.0

    nx, ny = len(supp_x), len(supp_y)
    c = np.zeros(nx * ny)
    for i, u in enumerate(supp_x):
        for j, v in enumerate(supp_y):
            c[i * ny + j] = dist[u, v]

    A_eq = np.zeros((nx + ny, nx * ny))
    b_eq = np.zeros(nx + ny)
    for i in range(nx):
        for j in range(ny):
            A_eq[i, i * ny + j] = 1.0
        b_eq[i] = mu_x[supp_x[i]]
    for j in range(ny):
        for i in range(nx):
            A_eq[nx + j, i * ny + j] = 1.0
        b_eq[nx + j] = mu_y[supp_y[j]]

    result = linprog(c, A_eq=A_eq, b_eq=b_eq,
                     bounds=[(0, None)] * (nx * ny), method='highs')
    return result.fun if result.success else 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# OLLIVIER-RICCI ON TERNARY WALK
# ═══════════════════════════════════════════════════════════════════════════════

def compute_orc(n_cl, adj, unique_he, he_born, firing, born_weighted=False):
    """Ollivier-Ricci using the ternary walk measure."""
    from collections import deque

    # BFS shortest paths
    dist = np.full((n_cl, n_cl), np.inf)
    np.fill_diagonal(dist, 0)
    for s in range(n_cl):
        q = deque([s])
        while q:
            v = q.popleft()
            for u in range(n_cl):
                if adj[v, u] > 0 and dist[s, u] > dist[s, v] + 1:
                    dist[s, u] = dist[s, v] + 1
                    q.append(u)

    curvatures = {}
    for i in range(n_cl):
        for j in range(i+1, n_cl):
            if adj[i, j] > 0:
                mu_i = ternary_walk_measure(i, unique_he, he_born, firing,
                                            n_cl, born_weighted)
                mu_j = ternary_walk_measure(j, unique_he, he_born, firing,
                                            n_cl, born_weighted)
                W1 = compute_W1(mu_i, mu_j, dist)
                kappa = 1.0 - W1  # d(i,j) = 1
                curvatures[(i, j)] = kappa

    return curvatures


def simple_graph_orc(n_cl, adj):
    """Standard Ollivier-Ricci on simple graph (uniform random walk)."""
    from collections import deque

    dist = np.full((n_cl, n_cl), np.inf)
    np.fill_diagonal(dist, 0)
    for s in range(n_cl):
        q = deque([s])
        while q:
            v = q.popleft()
            for u in range(n_cl):
                if adj[v, u] > 0 and dist[s, u] > dist[s, v] + 1:
                    dist[s, u] = dist[s, v] + 1
                    q.append(u)

    curvatures = {}
    deg = np.sum(adj, axis=1)
    for i in range(n_cl):
        for j in range(i+1, n_cl):
            if adj[i, j] > 0:
                mu_i = adj[i] / deg[i] if deg[i] > 0 else np.zeros(n_cl)
                mu_j = adj[j] / deg[j] if deg[j] > 0 else np.zeros(n_cl)
                W1 = compute_W1(mu_i, mu_j, dist)
                kappa = 1.0 - W1
                curvatures[(i, j)] = kappa

    return curvatures


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

def run_diagnostics(seed, n_ic=5):
    print(f"\n{'='*70}")
    print(f"  G1: Ternary-Aware Curvature on Q₂₄")
    print(f"  {n_ic} ICs, seed {seed}")
    print(f"{'='*70}")

    rng_master = np.random.default_rng(seed)

    all_simple = []
    all_ternary = []
    all_born = []
    all_einstein_corr = []

    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        n_cl, q_psi, q_tier, unique_he, he_born, firing, adj = \
            build_Q24_full(rng, depth=5)

        # A: Simple-graph ORC
        curv_simple = simple_graph_orc(n_cl, adj)
        ks_simple = list(curv_simple.values())
        all_simple.append(np.mean(ks_simple))

        # B: Ternary ORC (unweighted)
        curv_ternary = compute_orc(n_cl, adj, unique_he, he_born, firing,
                                   born_weighted=False)
        ks_ternary = list(curv_ternary.values())
        all_ternary.append(np.mean(ks_ternary))

        # C: Ternary ORC (Born-weighted)
        curv_born = compute_orc(n_cl, adj, unique_he, he_born, firing,
                                born_weighted=True)
        ks_born = list(curv_born.values())
        all_born.append(np.mean(ks_born))

        # D: Einstein test — correlation between Born weight per edge
        # and ternary curvature per edge
        edge_borns = []
        edge_curv_t = []
        edge_curv_b = []
        for (i, j), kappa in curv_ternary.items():
            # Born weight at this edge = sum of Born weights of HEs containing both i,j
            bw_ij = 0
            for (c1, c2, c3), bw in he_born.items():
                if (i in (c1,c2,c3)) and (j in (c1,c2,c3)):
                    bw_ij += bw
            edge_borns.append(bw_ij)
            edge_curv_t.append(kappa)
            edge_curv_b.append(curv_born.get((i,j), 0))

        edge_borns = np.array(edge_borns)
        edge_curv_t = np.array(edge_curv_t)
        edge_curv_b = np.array(edge_curv_b)

        if np.std(edge_borns) > 1e-10 and np.std(edge_curv_t) > 1e-10:
            r_einstein_t = np.corrcoef(edge_borns, edge_curv_t)[0, 1]
        else:
            r_einstein_t = 0.0

        if np.std(edge_borns) > 1e-10 and np.std(edge_curv_b) > 1e-10:
            r_einstein_b = np.corrcoef(edge_borns, edge_curv_b)[0, 1]
        else:
            r_einstein_b = 0.0

        all_einstein_corr.append((r_einstein_t, r_einstein_b))

        if ic == 0:
            print(f"\n  IC #{ic} (Q₂₄: {n_cl} clusters):")
            print(f"\n  A. Simple-graph ORC:")
            print(f"    ⟨κ⟩ = {np.mean(ks_simple):.4f}, range [{np.min(ks_simple):.4f}, {np.max(ks_simple):.4f}]")
            print(f"    Positive: {np.sum(np.array(ks_simple)>0)}/{len(ks_simple)}")

            print(f"\n  B. Ternary ORC (unweighted):")
            print(f"    ⟨κ⟩ = {np.mean(ks_ternary):.4f}, range [{np.min(ks_ternary):.4f}, {np.max(ks_ternary):.4f}]")
            print(f"    Positive: {np.sum(np.array(ks_ternary)>0)}/{len(ks_ternary)}")

            print(f"\n  C. Ternary ORC (Born-weighted):")
            print(f"    ⟨κ⟩ = {np.mean(ks_born):.4f}, range [{np.min(ks_born):.4f}, {np.max(ks_born):.4f}]")
            print(f"    Positive: {np.sum(np.array(ks_born)>0)}/{len(ks_born)}")

            print(f"\n  D. Discrete Einstein test (κ vs Born weight per edge):")
            print(f"    Ternary unweighted: r = {r_einstein_t:.4f}")
            print(f"    Ternary Born-weighted: r = {r_einstein_b:.4f}")

            # E: Tier decomposition
            print(f"\n  E. Tier decomposition of ternary curvature:")
            tier_curv = defaultdict(list)
            for (i, j), kappa in curv_ternary.items():
                ti, tj = q_tier[i], q_tier[j]
                pair = tuple(sorted([ti, tj]))
                tier_curv[pair].append(kappa)

            for pair in sorted(tier_curv.keys()):
                vals = tier_curv[pair]
                print(f"    {pair}: ⟨κ⟩ = {np.mean(vals):+.4f} ± {np.std(vals):.4f} "
                      f"(n={len(vals)})")

    # Summary
    print(f"\n{'─'*70}")
    print(f"  Summary across {n_ic} ICs:")
    print(f"    Simple-graph ⟨κ⟩:    {np.mean(all_simple):.4f} ± {np.std(all_simple):.4f}")
    print(f"    Ternary ⟨κ⟩:         {np.mean(all_ternary):.4f} ± {np.std(all_ternary):.4f}")
    print(f"    Born-weighted ⟨κ⟩:   {np.mean(all_born):.4f} ± {np.std(all_born):.4f}")

    r_t = [r[0] for r in all_einstein_corr]
    r_b = [r[1] for r in all_einstein_corr]
    print(f"\n    Einstein corr (ternary):      {np.mean(r_t):.4f} ± {np.std(r_t):.4f}")
    print(f"    Einstein corr (Born-weighted): {np.mean(r_b):.4f} ± {np.std(r_b):.4f}")

    # Verdict
    if abs(np.mean(r_t)) > 0.3 or abs(np.mean(r_b)) > 0.3:
        print(f"\n  VERDICT: Born weight DOES correlate with ternary curvature")
        print(f"    → Candidate for discrete Einstein equation")
    else:
        print(f"\n  VERDICT: Born weight does NOT correlate with ternary curvature")
        print(f"    → No discrete Einstein equation from this definition")

    # Sign comparison
    if np.mean(all_ternary) * np.mean(all_simple) < 0:
        print(f"\n  NOTE: Ternary and simple-graph curvatures have OPPOSITE SIGNS")
        print(f"    Simple: {np.mean(all_simple):+.4f}, Ternary: {np.mean(all_ternary):+.4f}")
    else:
        print(f"\n  NOTE: Ternary and simple-graph curvatures have SAME SIGN")


def main():
    parser = argparse.ArgumentParser(description="G1: Ternary Curvature")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n_ic", type=int, default=5)
    args = parser.parse_args()

    t0 = time.time()
    run_diagnostics(args.seed, args.n_ic)
    print(f"\n{'='*70}")
    print(f"  Total time: {time.time()-t0:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
