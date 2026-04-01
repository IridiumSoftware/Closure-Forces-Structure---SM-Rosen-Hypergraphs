#!/usr/bin/env python3
"""
g4_three_routes_v1.py — Three routes to finite dimension

Route A: Gauge-equivalence identification (coarser merges)
Route B: Coarse-graining / ancestry-based RG
Route C: Larger initial graphs beyond G₀

Usage:
  python g4_three_routes_v1.py [--depth D] [--seed S]
"""

import numpy as np
import time
from collections import defaultdict
from itertools import combinations

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


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH BUILDER (reused across routes)
# ═══════════════════════════════════════════════════════════════════════════════

def build_multiway(rng, topology, n_verts, max_depth):
    """Build multiway graph from initial topology.
    Returns psi dict, edge list, and compose cache."""
    psi = {}
    for v in range(n_verts):
        psi[v] = haar_C3(rng)
    next_vid = n_verts

    edges = []  # (depth, v1, v2, v3, parent_idx, ancestor_g0_edge)
    compose_cache = {}  # (v1, v2) → w_vid

    for i, (s1, s2, s3) in enumerate(topology):
        edges.append((0, s1, s2, s3, -1, i))

    for gen in range(max_depth):
        parent_edges = [(idx, e) for idx, e in enumerate(edges) if e[0] == gen]
        for idx, (depth, v1, v2, v3, pidx, ancestor) in parent_edges:
            key = (v1, v2)
            if key not in compose_cache:
                psi_new = compose_colour(psi[v1], psi[v2])
                compose_cache[key] = next_vid
                psi[next_vid] = psi_new
                next_vid += 1
            w = compose_cache[key]

            edges.append((gen+1, w, v2, v3, idx, ancestor))  # D1
            edges.append((gen+1, w, v1, v3, idx, ancestor))  # D2
            edges.append((gen+1, w, v1, v2, idx, ancestor))  # D3

    return psi, edges, compose_cache, next_vid


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE A: GAUGE-EQUIVALENCE IDENTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def route_a_gauge_equivalence(rng, max_depth, n_ic=20):
    """Identify vertices whose ψ are gauge-equivalent (|⟨ψ_a|ψ_b⟩|² ≈ 1).
    Count additional merges beyond topological ones."""

    print(f"\n{'='*70}")
    print(f"  ROUTE A: Gauge-Equivalence Identification")
    print(f"  {n_ic} ICs, depth {max_depth}")
    print(f"{'='*70}")

    G0_topo = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

    all_results = []
    for ic in range(n_ic):
        rng_i = np.random.default_rng(rng.integers(0, 2**31))
        psi, edges, cache, n_verts = build_multiway(rng_i, G0_topo, 6, max_depth)

        # For each generation, count vertices and gauge-equivalent clusters
        for gen in range(max_depth + 1):
            # Vertices composed at this generation
            if gen == 0:
                vids = list(range(6))
            else:
                edges_at_gen = [e for e in edges if e[0] == gen]
                vids = list(set(e[1] for e in edges_at_gen))  # pos1 = composed vertex

            n_verts_gen = len(vids)
            if n_verts_gen <= 1:
                all_results.append((gen, n_verts_gen, n_verts_gen, 0))
                continue

            # Compute pairwise |⟨ψ_a|ψ_b⟩|² for all composed vertices
            psi_vecs = [psi[v] for v in vids]
            # Cluster by gauge-equivalence: |⟨ψ_a|ψ_b⟩|² > threshold
            # SU(3) gauge equivalence means ψ_b = U ψ_a for some U ∈ SU(3)
            # This implies |⟨ψ_a|ψ_b⟩| = 1 (they're on the same orbit)
            # But unit vectors related by SU(3) satisfy |⟨ψ_a|ψ_b⟩|² = 1
            # iff ψ_b = e^{iθ} ψ_a (overall phase — U(1) orbit of SU(3) action)
            # Actually, for ψ ∈ CP², gauge equivalence is ψ_b = e^{iθ}ψ_a
            # So |⟨ψ_a|ψ_b⟩|² = 1 iff they're the same point in CP²

            # Use threshold for near-equivalence
            THRESHOLD = 0.999  # |⟨ψ_a|ψ_b⟩|² > 0.999

            # Union-find clustering
            parent = list(range(n_verts_gen))
            def find(x):
                while parent[x] != x:
                    parent[x] = parent[parent[x]]
                    x = parent[x]
                return x
            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py

            n_gauge_merges = 0
            for i in range(n_verts_gen):
                for j in range(i+1, n_verts_gen):
                    ip = abs(np.vdot(psi_vecs[i], psi_vecs[j]))**2
                    if ip > THRESHOLD:
                        if find(i) != find(j):
                            union(i, j)
                            n_gauge_merges += 1

            clusters = len(set(find(i) for i in range(n_verts_gen)))
            all_results.append((gen, n_verts_gen, clusters, n_gauge_merges))

    # Aggregate by generation
    by_gen = defaultdict(list)
    for gen, nv, nc, nm in all_results:
        by_gen[gen].append((nv, nc, nm))

    print(f"\n  {'Gen':>4} | {'N_verts':>8} | {'N_clusters':>10} | {'gauge_merges':>13} | "
          f"{'reduction_%':>12}")
    print(f"  {'-'*60}")
    for gen in range(max_depth + 1):
        if gen in by_gen:
            data = by_gen[gen]
            nv_mean = np.mean([d[0] for d in data])
            nc_mean = np.mean([d[1] for d in data])
            nm_mean = np.mean([d[2] for d in data])
            red = (1 - nc_mean/nv_mean)*100 if nv_mean > 0 else 0
            print(f"  {gen:>4} | {nv_mean:>8.0f} | {nc_mean:>10.1f} | "
                  f"{nm_mean:>13.1f} | {red:>11.1f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE B: COARSE-GRAINING / ANCESTRY-BASED RG
# ═══════════════════════════════════════════════════════════════════════════════

def route_b_coarsegraining(rng, max_depth):
    """Track ancestry: which gen-0 edge does each gen-g edge descend from?
    Count how many distinct ancestries remain vs generation.
    Also: block-spin by shared-vertex neighborhoods."""

    print(f"\n{'='*70}")
    print(f"  ROUTE B: Coarse-Graining / Ancestry-Based RG")
    print(f"{'='*70}")

    G0_topo = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]
    rng_i = np.random.default_rng(rng.integers(0, 2**31))
    psi, edges, cache, n_verts = build_multiway(rng_i, G0_topo, 6, max_depth)

    # Ancestry tracking: each gen-0 edge has a unique ancestor ID (0-5)
    # Each daughter inherits its parent's ancestor ID

    print(f"\n  {'Gen':>4} | {'N_edges':>8} | {'N_ancestors':>11} | "
          f"{'edges/ancestor':>14} | {'N_vertices':>10} | {'verts/ancestor':>14}")
    print(f"  {'-'*70}")

    for gen in range(max_depth + 1):
        edges_at_gen = [e for e in edges if e[0] == gen]
        ancestors = set(e[5] for e in edges_at_gen)
        n_edges = len(edges_at_gen)
        n_ancestors = len(ancestors)
        epa = n_edges / n_ancestors if n_ancestors > 0 else 0

        # Vertices used by edges at this generation
        verts_at_gen = set()
        for e in edges_at_gen:
            verts_at_gen.update(e[1:4])  # v1, v2, v3
        n_verts_gen = len(verts_at_gen)
        vpa = n_verts_gen / n_ancestors if n_ancestors > 0 else 0

        print(f"  {gen:>4} | {n_edges:>8} | {n_ancestors:>11} | "
              f"{epa:>14.1f} | {n_verts_gen:>10} | {vpa:>14.1f}")

    # Shared-vertex neighborhoods: for each vertex at gen g, how many
    # different ancestors contribute edges using that vertex?
    print(f"\n  Shared-vertex mixing (how many ancestors share each vertex):")
    print(f"  {'Gen':>4} | {'N_shared':>9} | {'mean_mix':>9} | {'max_mix':>8}")
    print(f"  {'-'*40}")

    for gen in range(max_depth + 1):
        edges_at_gen = [e for e in edges if e[0] == gen]
        # For each vertex, track which ancestors use it
        vertex_ancestors = defaultdict(set)
        for e in edges_at_gen:
            for v in [e[1], e[2], e[3]]:
                vertex_ancestors[v].add(e[5])

        shared = {v: anc for v, anc in vertex_ancestors.items() if len(anc) > 1}
        n_shared = len(shared)
        if shared:
            mix_values = [len(anc) for anc in shared.values()]
            mean_mix = np.mean(mix_values)
            max_mix = max(mix_values)
        else:
            mean_mix = 0
            max_mix = 0
        print(f"  {gen:>4} | {n_shared:>9} | {mean_mix:>9.1f} | {max_mix:>8}")


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTE C: LARGER INITIAL GRAPHS
# ═══════════════════════════════════════════════════════════════════════════════

def route_c_larger_graphs(rng, max_depth):
    """Test merge rates on larger Rosen-closed graphs.
    G₀ has 6v/6e. Try doubled (12v/12e) and tripled (18v/18e) cyclic graphs."""

    print(f"\n{'='*70}")
    print(f"  ROUTE C: Larger Initial Graphs")
    print(f"{'='*70}")

    # G₀: 6 vertices, cyclic shift
    G0 = [(i, (i+1)%6, (i+2)%6) for i in range(6)]

    # G₁₂: 12 vertices, cyclic shift (same structure, more vertices)
    G12 = [(i, (i+1)%12, (i+2)%12) for i in range(12)]

    # G₁₈: 18 vertices, cyclic shift
    G18 = [(i, (i+1)%18, (i+2)%18) for i in range(18)]

    # G₆_dense: 6 vertices, all possible ternary edges (more edges per vertex)
    # Rosen-closed: every vertex must be a target. With 6 vertices, we need
    # at least 6 edges (one targeting each). Add more for denser sharing.
    # Use two overlapping cyclic patterns:
    G6_dense = [
        (0,1,2), (1,2,3), (2,3,4), (3,4,5), (4,5,0), (5,0,1),  # forward cycle
        (0,2,4), (1,3,5), (2,4,0), (3,5,1), (4,0,2), (5,1,3),  # skip-1 cycle
    ]

    # G₆_full: 6 vertices, stride-1 + stride-2 (fully connected sharing)
    G6_stride2 = [
        (0,1,2), (1,2,3), (2,3,4), (3,4,5), (4,5,0), (5,0,1),  # stride 1
        (0,2,4), (2,4,0), (4,0,2),  # stride 2 (covers v0,v2,v4)
        (1,3,5), (3,5,1), (5,1,3),  # stride 2 (covers v1,v3,v5)
    ]

    graphs = [
        ("G₀ (6v, 6e, cyclic)", G0, 6),
        ("G₁₂ (12v, 12e, cyclic)", G12, 12),
        ("G₁₈ (18v, 18e, cyclic)", G18, 18),
        ("G₆_dense (6v, 12e, 2 cycles)", G6_dense, 6),
        ("G₆_stride2 (6v, 12e, stride)", G6_stride2, 6),
    ]

    for name, topo, n_verts in graphs:
        print(f"\n  --- {name} ---")
        rng_i = np.random.default_rng(rng.integers(0, 2**31))
        psi, edges, cache, total_verts = build_multiway(rng_i, topo, n_verts, max_depth)

        print(f"  {'Gen':>4} | {'N_edges':>8} | {'N_composed':>10} | "
              f"{'b_vertex':>10} | {'merge_%':>8}")
        print(f"  {'-'*50}")

        prev_composed = n_verts
        for gen in range(max_depth + 1):
            edges_at_gen = [e for e in edges if e[0] == gen]
            n_edges = len(edges_at_gen)

            # Count unique composed vertices at this generation
            if gen == 0:
                composed = set(range(n_verts))
            else:
                composed = set(e[1] for e in edges_at_gen)

            n_composed = len(composed)
            n_expected = len(edges_at_gen) // 3 if gen > 0 else n_verts
            # Number of edges that share a composed vertex with another edge
            n_merges = n_expected - n_composed if gen > 0 else 0
            merge_pct = n_merges / n_expected * 100 if n_expected > 0 else 0
            b_v = n_composed / prev_composed if prev_composed > 0 and gen > 0 else 0

            print(f"  {gen:>4} | {n_edges:>8} | {n_composed:>10} | "
                  f"{b_v:>10.4f} | {merge_pct:>7.1f}%")

            prev_composed = n_composed


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="G4: three routes to finite dimension")
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    print(f"{'='*70}")
    print(f"  G4 Three Routes: depth {args.depth}, seed {args.seed}")
    print(f"{'='*70}")

    t0 = time.time()
    route_a_gauge_equivalence(np.random.default_rng(rng.integers(0, 2**31)),
                               min(args.depth, 4), n_ic=20)
    route_b_coarsegraining(np.random.default_rng(rng.integers(0, 2**31)),
                            args.depth)
    route_c_larger_graphs(np.random.default_rng(rng.integers(0, 2**31)),
                           min(args.depth, 4))

    print(f"\n{'='*70}")
    print(f"  Total time: {time.time()-t0:.1f}s")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
