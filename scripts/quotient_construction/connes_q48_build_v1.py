#!/usr/bin/env python3
"""
connes_q48_build_v1.py — Build Q₄₈ = (M(G₀) ∪ C(M(G₀))) / gauge

Construction:
  1. Build M(G₀) to depth 5 with Haar-random C³ decorations
  2. Apply charge conjugation C: ψ → ψ* to every vertex → C(M(G₀))
  3. Take the union of all vertices (original + conjugate)
  4. Compute gauge-equivalence quotient (|���ψ|ψ'⟩|² > threshold)

Diagnostics:
  A. Vertex count: is |Q₄₈| = 48, or more/less?
  B. C-involution: does C act as a clean fixed-point-free involution on Q₄₈?
  C. Tier structure: how does the 6+6+12 of Q₂₄ extend?
  D. Autopoiesis: is Q₄₈ a fixed point under M → quotient?
  E. Rosen closure: is every vertex source and target of some hyperedge?
  F. Overlap with Q₂₄: exactly 24 vertices from Q₂₄ survive?
  G. IC-independence

Usage:
  python3 connes_q48_build_v1.py [--seed S] [--n_ic N]
"""

import numpy as np
import argparse
from collections import defaultdict

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

G0_TOPO = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD M(G₀) WITH ALL VERTICES
# ═══════════════════════════════════════════════════════════════════════════════

def build_multiway(edges, psi_init, depth=5):
    """Build the multiway graph M(G₀). Return all vertices with decorations."""
    psi = dict(psi_init)
    next_vid = max(psi_init.keys()) + 1
    all_edges = [(0, s1, s2, s3) for s1, s2, s3 in edges]
    compose_cache = {}
    vertex_depth = {v: 0 for v in psi_init}

    for d in range(depth):
        for _, v1, v2, v3 in [e for e in all_edges if e[0] == d]:
            key = (v1, v2)
            if key not in compose_cache:
                w_psi = compose_colour(psi[v1], psi[v2])
                if np.linalg.norm(w_psi) < 1e-10:
                    continue
                psi[next_vid] = w_psi
                compose_cache[key] = next_vid
                vertex_depth[next_vid] = d + 1
                next_vid += 1
            w = compose_cache[key]
            all_edges.append((d+1, w, v2, v3))
            all_edges.append((d+1, w, v1, v3))
            all_edges.append((d+1, w, v1, v2))

    return psi, vertex_depth, all_edges


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₄₈ = (M(G₀) ∪ C(M(G₀))) / GAUGE
# ═══════════════════════════════════════════════════════════════════════════════

def build_q48(psi_init, depth=5, threshold=0.999):
    """Build Q₄₈ from M(G₀) ∪ C(M(G₀))."""

    # Step 1: Build M(G₀)
    psi_orig, depth_orig, edges_orig = build_multiway(G0_TOPO, psi_init, depth)

    # Step 2: Apply C to all decorations: ψ → ψ*
    # Create conjugate vertices with offset IDs
    offset = max(psi_orig.keys()) + 1
    psi_conj = {}
    depth_conj = {}
    for vid, psi_v in psi_orig.items():
        psi_conj[vid + offset] = np.conj(psi_v)
        depth_conj[vid + offset] = depth_orig[vid]

    # Step 3: Build conjugate multiway graph edges
    # C(compose(a,b)) = compose(C(a), C(b))? Let's check:
    # compose(a,b) = normalize(conj(a × b))
    # C(compose(a,b)) = conj(normalize(conj(a × b))) = normalize(a × b)
    # compose(C(a), C(b)) = normalize(conj(conj(a) × conj(b))) = normalize(conj(a* × b*))
    # a* × b* = conj(a × b)* ... no, let me compute directly.
    # (a*)_i = conj(a_i). (a* × b*)_k = ε_{ijk} conj(a_i) conj(b_j) = conj(ε_{ijk} a_i b_j) = conj((a×b)_k)
    # So a* × b* = conj(a × b) = (a × b)*
    # compose(a*, b*) = normalize(conj(a* × b*)) = normalize(conj((a×b)*)) = normalize(a × b)
    # C(compose(a,b)) = conj(compose(a,b)) = conj(normalize(conj(a×b)))
    #                 = normalize(conj(conj(a×b))*) ... hmm, normalize is real-linear
    # Actually: normalize(v)* = normalize(v*) since ||v|| = ||v*||.
    # C(compose(a,b)) = normalize(conj(a×b))* = normalize((conj(a×b))*)
    # compose(C(a),C(b)) = normalize(conj(a* × b*)) = normalize(conj((a×b)*)) = normalize((a×b))
    # These are NOT equal in general. C does not commute with compose.
    #
    # So we need to build the conjugate multiway graph by composing the CONJUGATED vectors.

    # Build M(C(G₀)) from scratch with conjugated initial conditions
    # Use standard vertex IDs 0-5, then offset everything afterward
    psi_init_conj_std = {v: np.conj(psi_init[v]) for v in psi_init}
    psi_conj_std, depth_conj_std, edges_conj_std = build_multiway(
        G0_TOPO, psi_init_conj_std, depth
    )
    # Offset all conjugate vertex IDs to avoid collision
    psi_conj2 = {v + offset: psi_conj_std[v] for v in psi_conj_std}
    depth_conj2 = {v + offset: depth_conj_std[v] for v in depth_conj_std}
    edges_conj = [(d, v1+offset, v2+offset, v3+offset) for d, v1, v2, v3 in edges_conj_std]

    # Step 4: Union of all vertices
    psi_all = {}
    depth_all = {}
    source = {}  # track origin: 'orig' or 'conj'

    for vid, psi_v in psi_orig.items():
        psi_all[vid] = psi_v
        depth_all[vid] = depth_orig[vid]
        source[vid] = 'orig'

    for vid, psi_v in psi_conj2.items():
        psi_all[vid] = psi_v
        depth_all[vid] = depth_conj2[vid]
        source[vid] = 'conj'

    # Step 5: Gauge-equivalence clustering
    all_vids = sorted(psi_all.keys())
    clusters = []
    vid_to_cid = {}

    for v in all_vids:
        matched = False
        for ci, (_, rp, _) in enumerate(clusters):
            if fidelity(psi_all[v], rp) > threshold:
                vid_to_cid[v] = ci
                matched = True
                break
        if not matched:
            vid_to_cid[v] = len(clusters)
            clusters.append((v, psi_all[v], source[v]))

    n_cl = len(clusters)
    q_psi = {i: clusters[i][1] for i in range(n_cl)}
    q_source = {i: clusters[i][2] for i in range(n_cl)}

    # Track which clusters came from orig vs conj vs both
    cl_sources = defaultdict(set)
    for v in all_vids:
        ci = vid_to_cid[v]
        cl_sources[ci].add(source[v])

    cl_origin = {}
    for ci in range(n_cl):
        srcs = cl_sources[ci]
        if srcs == {'orig'}:
            cl_origin[ci] = 'orig_only'
        elif srcs == {'conj'}:
            cl_origin[ci] = 'conj_only'
        else:
            cl_origin[ci] = 'both'

    # Tier assignment (based on earliest depth)
    cl_earliest = {}
    for ci in range(n_cl):
        members = [v for v in all_vids if vid_to_cid.get(v) == ci]
        cl_earliest[ci] = min(depth_all.get(v, 99) for v in members)

    orig_cids = set(vid_to_cid[v] for v in range(6))
    gen1_cids = set()
    for v, d in depth_all.items():
        if d == 1:
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

    # Hyperedges from both graphs
    q_he = set()
    for _, v1, v2, v3 in edges_orig + edges_conj:
        if v1 in vid_to_cid and v2 in vid_to_cid and v3 in vid_to_cid:
            c1, c2, c3 = vid_to_cid[v1], vid_to_cid[v2], vid_to_cid[v3]
            q_he.add((c1, c2, c3))

    # Composition targets
    comp_targets = {}
    for edges_list in [edges_orig, edges_conj]:
        compose_cache_q = {}
        for _, v1, v2, v3 in edges_list:
            if v1 in vid_to_cid and v2 in vid_to_cid:
                c1, c2 = vid_to_cid[v1], vid_to_cid[v2]
                if (c1, c2) not in comp_targets:
                    # Find what c1,c2 compose to
                    w = compose_colour(q_psi[c1], q_psi[c2])
                    best_c = -1
                    best_f = 0
                    for ci in range(n_cl):
                        f = fidelity(w, q_psi[ci])
                        if f > best_f:
                            best_f = f
                            best_c = ci
                    if best_f > threshold:
                        comp_targets[(c1, c2)] = best_c

    return {
        'n_cl': n_cl,
        'q_psi': q_psi,
        'q_tier': q_tier,
        'q_he': q_he,
        'comp_targets': comp_targets,
        'cl_origin': cl_origin,
        'cl_earliest': cl_earliest,
        'q_source': q_source,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ALSO BUILD STANDARD Q₂₄ FOR COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

def build_q24(psi_init, depth=5, threshold=0.999):
    psi, vdepth, edges = build_multiway(G0_TOPO, psi_init, depth)
    all_vids = sorted(psi.keys())
    clusters = []; vid_to_cid = {}
    for v in all_vids:
        matched = False
        for ci, (_, rp) in enumerate(clusters):
            if fidelity(psi[v], rp) > threshold:
                vid_to_cid[v] = ci; matched = True; break
        if not matched:
            vid_to_cid[v] = len(clusters)
            clusters.append((v, psi[v]))
    n_cl = len(clusters)
    q_psi = {i: clusters[i][1] for i in range(n_cl)}
    return n_cl, q_psi


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

def run_diagnostics(Q48, psi_init, seed):
    n_cl = Q48['n_cl']
    q_psi = Q48['q_psi']
    q_tier = Q48['q_tier']
    cl_origin = Q48['cl_origin']

    print(f"\n{'='*60}")
    print(f"  Q₄₈ DIAGNOSTICS")
    print(f"{'='*60}")

    # A. Vertex count
    print(f"\n  A. Vertex count: {n_cl}")
    orig_only = sum(1 for v in cl_origin.values() if v == 'orig_only')
    conj_only = sum(1 for v in cl_origin.values() if v == 'conj_only')
    both = sum(1 for v in cl_origin.values() if v == 'both')
    print(f"     From original M(G₀) only: {orig_only}")
    print(f"     From conjugate C(M(G₀)) only: {conj_only}")
    print(f"     Overlap (in both): {both}")
    print(f"     orig_only + conj_only + both = {orig_only + conj_only + both}")

    # B. C-involution: does C map Q₄₈ to itself cleanly?
    print(f"\n  B. C-involution on Q₄₈:")
    c_map = {}
    c_fidelities = {}
    for c in range(n_cl):
        psi_c = np.conj(q_psi[c])
        best_fid = 0
        best_target = -1
        for c2 in range(n_cl):
            f = fidelity(psi_c, q_psi[c2])
            if f > best_fid:
                best_fid = f
                best_target = c2
        c_map[c] = best_target
        c_fidelities[c] = best_fid

    min_fid = min(c_fidelities.values())
    max_fid = max(c_fidelities.values())
    clean_maps = sum(1 for f in c_fidelities.values() if f > 0.999)
    is_involution = all(c_map.get(c_map[c], -1) == c for c in range(n_cl))
    fixed_pts = sum(1 for c in range(n_cl) if c_map[c] == c)

    print(f"     Min fidelity of C-image match: {min_fid:.6f}")
    print(f"     Max fidelity: {max_fid:.6f}")
    print(f"     Clean maps (fid > 0.999): {clean_maps}/{n_cl}")
    print(f"     C² = id (involution): {is_involution}")
    print(f"     Fixed points (self-conjugate): {fixed_pts}")
    cross_pairs = set()
    for c in range(n_cl):
        if c_map[c] != c:
            cross_pairs.add(tuple(sorted([c, c_map[c]])))
    print(f"     Cross-pairs: {len(cross_pairs)}")
    print(f"     Total accounted: {fixed_pts + 2*len(cross_pairs)} (should be {n_cl})")

    # Tier mapping under C
    tier_map = defaultdict(int)
    for c in range(n_cl):
        src = q_tier[c]
        tgt = q_tier[c_map[c]]
        tier_map[(src, tgt)] += 1
    print(f"\n     Tier mapping under C:")
    for (s, t), cnt in sorted(tier_map.items()):
        print(f"       {s} → {t}: {cnt}")

    # C. Tier structure
    print(f"\n  C. Tier structure:")
    tier_counts = defaultdict(int)
    for c, t in q_tier.items():
        tier_counts[t] += 1
    for t in sorted(tier_counts):
        # Count by origin
        orig_in_tier = sum(1 for c in range(n_cl) if q_tier[c] == t and cl_origin[c] == 'orig_only')
        conj_in_tier = sum(1 for c in range(n_cl) if q_tier[c] == t and cl_origin[c] == 'conj_only')
        both_in_tier = sum(1 for c in range(n_cl) if q_tier[c] == t and cl_origin[c] == 'both')
        print(f"     Tier {t}: {tier_counts[t]} (orig: {orig_in_tier}, conj: {conj_in_tier}, both: {both_in_tier})")

    # D. Hyperedges and compositions
    print(f"\n  D. Hyperedges: {len(Q48['q_he'])}")
    print(f"     Compositions: {len(Q48['comp_targets'])}")

    # E. Rosen closure check
    sources = set()
    targets = set()
    for (c1, c2, c3) in Q48['q_he']:
        sources.update([c1, c2, c3])
        # In convention (c1,c2,c3): c1 = composed/F-role = "target" of composition
        targets.add(c1)
    all_verts = set(range(n_cl))
    is_source = sources == all_verts
    is_target = targets == all_verts
    print(f"\n  E. Rosen closure:")
    print(f"     All vertices are sources: {is_source} ({len(sources)}/{n_cl})")
    print(f"     All vertices are targets (pos1): {is_target} ({len(targets)}/{n_cl})")

    # F. Overlap with Q₂₄
    print(f"\n  F. Overlap with standard Q₂₄:")
    n24, q24_psi = build_q24(psi_init, depth=5)
    print(f"     Q₂₄ has {n24} clusters")
    # Match Q₂₄ clusters to Q₄₈ clusters
    matched = 0
    for c24 in range(n24):
        for c48 in range(n_cl):
            if fidelity(q24_psi[c24], q_psi[c48]) > 0.999:
                matched += 1
                break
    print(f"     Q₂₄ clusters found in Q₄₈: {matched}/{n24}")

    # ℤ₂ chirality structure on Q₄₈
    print(f"\n  G. Chirality (ℤ₂) on Q₄₈:")
    # Option 1: origin-based grading (orig = +1, conj = -1, both = 0)
    orig_count = sum(1 for v in cl_origin.values() if v == 'orig_only')
    conj_count = sum(1 for v in cl_origin.values() if v == 'conj_only')
    both_count = sum(1 for v in cl_origin.values() if v == 'both')
    print(f"     Origin grading: orig={orig_count}, conj={conj_count}, both={both_count}")
    if both_count == 0 and orig_count == conj_count:
        print(f"     ✓ Clean particle/antiparticle split: {orig_count} + {conj_count}")
    elif both_count > 0:
        print(f"     Overlap vertices break clean split")

    # Option 2: C-map grading (C maps c → c', so {c, c'} is a pair)
    # The grading would be: pick one from each pair as "particle", other as "antiparticle"
    if is_involution and fixed_pts == 0:
        print(f"     ✓ C is a fixed-point-free involution → clean L/R doubling")
    elif is_involution:
        print(f"     C is involution with {fixed_pts} fixed points")

    return c_map, c_fidelities


def ic_independence(n_ic, seed):
    """Check IC-independence of Q₄₈ vertex count and structure."""
    print(f"\n{'='*60}")
    print(f"  IC-INDEPENDENCE ({n_ic} ICs)")
    print(f"{'='*60}")

    rng_master = np.random.default_rng(seed + 5000)
    results = []

    for ic in range(n_ic):
        s = rng_master.integers(0, 2**31)
        rng = np.random.default_rng(s)
        psi_init = {v: haar_C3(rng) for v in range(6)}
        Q = build_q48(psi_init, depth=5)

        orig = sum(1 for v in Q['cl_origin'].values() if v == 'orig_only')
        conj = sum(1 for v in Q['cl_origin'].values() if v == 'conj_only')
        both = sum(1 for v in Q['cl_origin'].values() if v == 'both')

        # C-involution quality
        min_fid = 1.0
        for c in range(Q['n_cl']):
            psi_c = np.conj(Q['q_psi'][c])
            best = max(fidelity(psi_c, Q['q_psi'][c2]) for c2 in range(Q['n_cl']))
            min_fid = min(min_fid, best)

        results.append({
            'n_cl': Q['n_cl'], 'orig': orig, 'conj': conj, 'both': both,
            'min_fid': min_fid,
        })

    print(f"  n_cl:    {[r['n_cl'] for r in results]}")
    print(f"  orig:    {[r['orig'] for r in results]}")
    print(f"  conj:    {[r['conj'] for r in results]}")
    print(f"  both:    {[r['both'] for r in results]}")
    mf = [round(r['min_fid'], 4) for r in results]
    print(f"  min_fid: {mf}")

    n_cls = [r['n_cl'] for r in results]
    print(f"\n  IC-independent n_cl: {'YES' if len(set(n_cls)) == 1 else 'NO'} "
          f"(unique: {sorted(set(n_cls))})")

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_ic', type=int, default=10)
    args = parser.parse_args()

    print("="*60)
    print("  Q₄₈ = (M(G₀) ∪ C(M(G₀))) / gauge")
    print("="*60)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("\n  Building Q₄₈...")
    Q48 = build_q48(psi_init, depth=5)
    print(f"  → {Q48['n_cl']} clusters")

    c_map, c_fid = run_diagnostics(Q48, psi_init, args.seed)

    ic_results = ic_independence(args.n_ic, args.seed)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  |Q₄₈| = {Q48['n_cl']}")
    orig = sum(1 for v in Q48['cl_origin'].values() if v == 'orig_only')
    conj = sum(1 for v in Q48['cl_origin'].values() if v == 'conj_only')
    both = sum(1 for v in Q48['cl_origin'].values() if v == 'both')
    print(f"  Origin split: {orig} orig + {conj} conj + {both} overlap")
    print(f"  C-involution min fidelity: {min(c_fid.values()):.6f}")
    print(f"  Is 48 = 24 + 24? {'YES' if Q48['n_cl'] == 48 else 'NO'}")


if __name__ == '__main__':
    main()
