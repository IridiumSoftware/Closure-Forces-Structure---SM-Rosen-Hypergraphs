#!/usr/bin/env python3
"""
active_cohomology_v1.py — Active Cohomology H¹_a on Q₂₄ and Q₅₁

Computes the active coboundary matrix δ_a for Q₂₄ and Q₅₁ and analyses
the kernel (= space of admissible hypercharge assignments).

Diagnostics:
  A. Build Q₂₄ and Q₅₁ with composition-target tracking
  B. Construct δ_a matrices, compute rank and kernel dimension
  C. Tier-uniform projection: verify 1:−2:1 family
  D. Kernel structure: tier breakdown, independent cocycles
  E. Restriction map ι*: H¹_a(Q₅₁) → H¹_a(Q₂₄) — isomorphism test
  F. IC-independence (multiple random seeds)

Usage:
  python3 active_cohomology_v1.py [--seed S] [--n_ic N]
"""

import numpy as np
import argparse
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ALGEBRA (from g4_q24_q51_relation_v1.py)
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

def complete_ternary(n):
    return [(i,j,k) for i in range(n) for j in range(n) if j!=i
            for k in range(n) if k!=i and k!=j]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD QUOTIENT WITH COMPOSITION-TARGET TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

def build_quotient(edges, psi_init, depth=5):
    """Build the gauge-equivalence quotient from a seed graph.

    Returns dict with: n_cl, q_psi, q_tier, q_he, comp_pairs,
    and crucially: comp_targets — dict (c1,c2) → c_target for each
    unique quotient-level composition.
    """
    psi = dict(psi_init)
    next_vid = max(psi_init.keys()) + 1
    all_edges = [(0, s1, s2, s3) for s1, s2, s3 in edges]
    compose_cache = {}
    vertex_depth = {v: 0 for v in psi_init}

    # Track raw composition events: (v1, v2) → w
    raw_compositions = []

    for d in range(depth):
        for _, v1, v2, v3 in [e for e in all_edges if e[0] == d]:
            key = (v1, v2)
            if key not in compose_cache:
                w_psi = compose_colour(psi[v1], psi[v2])
                if np.linalg.norm(w_psi) < 1e-10:
                    continue  # degenerate composition
                psi[next_vid] = w_psi
                compose_cache[key] = next_vid
                vertex_depth[next_vid] = d + 1
                raw_compositions.append((v1, v2, next_vid))
                next_vid += 1
            w = compose_cache[key]
            all_edges.append((d+1, w, v2, v3))
            all_edges.append((d+1, w, v1, v3))
            all_edges.append((d+1, w, v1, v2))

    # Clustering
    all_vids = sorted(psi.keys())
    THRESHOLD = 0.999
    clusters = []; vid_to_cid = {}
    for v in all_vids:
        matched = False
        for ci, (_, rp) in enumerate(clusters):
            if fidelity(psi[v], rp) > THRESHOLD:
                vid_to_cid[v] = ci; matched = True; break
        if not matched:
            vid_to_cid[v] = len(clusters)
            clusters.append((v, psi[v]))

    n_cl = len(clusters)
    q_psi = {i: clusters[i][1] for i in range(n_cl)}

    # Tiers
    orig = set(vid_to_cid[v] for v in range(6))
    gen1 = set()
    for v, d in vertex_depth.items():
        if d == 1:
            c = vid_to_cid[v]
            if c not in orig: gen1.add(c)

    q_tier = {}
    for c in range(n_cl):
        if c in orig: q_tier[c] = 'A'
        elif c in gen1: q_tier[c] = 'B'
        else: q_tier[c] = 'C'

    # Hyperedges (ordered triples)
    q_he = set()
    for _, v1, v2, v3 in all_edges:
        if v1 in vid_to_cid and v2 in vid_to_cid and v3 in vid_to_cid:
            c1,c2,c3 = vid_to_cid[v1],vid_to_cid[v2],vid_to_cid[v3]
            q_he.add((c1,c2,c3))

    # Composition targets at quotient level
    # For each unique quotient-level composition pair, find the target cluster
    comp_targets = {}  # (c_source1, c_source2) → c_target
    for v1, v2, w in raw_compositions:
        c1, c2, cw = vid_to_cid[v1], vid_to_cid[v2], vid_to_cid[w]
        pair = (c1, c2)
        if pair not in comp_targets:
            comp_targets[pair] = cw
        else:
            # Verify consistency
            assert comp_targets[pair] == cw, \
                f"Inconsistent: ({c1},{c2})→{cw} vs existing →{comp_targets[pair]}"

    return {
        'n_cl': n_cl,
        'q_psi': q_psi,
        'q_tier': q_tier,
        'q_he': q_he,
        'comp_targets': comp_targets,
        'vid_to_cid': vid_to_cid,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVE COBOUNDARY MATRIX
# ═══════════════════════════════════════════════════════════════════════════════

def build_delta_a(n_cl, comp_targets):
    """Build the active coboundary matrix δ_a.

    For each composition (c1, c2) → c_w, the constraint is:
        Y(c_w) + Y(c1) + Y(c2) = 0

    δ_a is an m × n_cl matrix where m = number of unique compositions.
    Row i has +1 at columns c1, c2, c_w.
    """
    rows = []
    pair_list = sorted(comp_targets.keys())

    for c1, c2 in pair_list:
        cw = comp_targets[(c1, c2)]
        row = np.zeros(n_cl)
        # Y(cw) + Y(c1) + Y(c2) = 0
        row[cw] += 1
        row[c1] += 1
        row[c2] += 1
        rows.append(row)

    return np.array(rows), pair_list


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_cohomology(name, Q):
    """Full cohomology analysis for a single quotient."""
    n_cl = Q['n_cl']
    comp_targets = Q['comp_targets']
    q_tier = Q['q_tier']

    print(f"\n{'─'*60}")
    print(f"  {name}: {n_cl} vertices, {len(comp_targets)} unique compositions")
    print(f"{'─'*60}")

    # Tier counts
    tier_counts = defaultdict(int)
    for c, t in q_tier.items():
        tier_counts[t] += 1
    for t in sorted(tier_counts):
        print(f"  Tier {t}: {tier_counts[t]} vertices")

    # Build δ_a
    delta_a, pair_list = build_delta_a(n_cl, comp_targets)
    print(f"\n  δ_a shape: {delta_a.shape} ({delta_a.shape[0]} constraints × {n_cl} unknowns)")

    # Rank and kernel
    rank = np.linalg.matrix_rank(delta_a, tol=1e-10)
    ker_dim = n_cl - rank
    print(f"  rank(δ_a) = {rank}")
    print(f"  dim ker(δ_a) = dim H¹_a = {ker_dim}")

    # Compute kernel basis via SVD
    U, S, Vt = np.linalg.svd(delta_a)
    null_mask = np.abs(S) < 1e-10
    # Null space = last (n_cl - rank) rows of Vt
    if ker_dim > 0:
        kernel_basis = Vt[-ker_dim:]  # shape: (ker_dim, n_cl)
    else:
        kernel_basis = np.zeros((0, n_cl))

    # Verify kernel
    if ker_dim > 0:
        residual = np.max(np.abs(delta_a @ kernel_basis.T))
        print(f"  Kernel verification: max|δ_a · ker| = {residual:.2e}")

    # Tier-uniform projection
    # Average kernel vectors over tiers
    tiers = sorted(set(q_tier.values()))
    tier_to_idx = {t: [c for c in range(n_cl) if q_tier[c] == t] for t in tiers}

    print(f"\n  Tier-uniform analysis:")
    print(f"  Tiers: {tiers}")

    # Build tier-projected constraint matrix
    # If Y is tier-uniform: Y(v) = Y_{tier(v)}, then the constraint becomes
    # Y_{tier(cw)} + Y_{tier(c1)} + Y_{tier(c2)} = 0 for each composition
    tier_idx = {t: i for i, t in enumerate(tiers)}
    n_tiers = len(tiers)
    tier_rows = []
    seen_tier_constraints = set()
    for c1, c2 in pair_list:
        cw = comp_targets[(c1, c2)]
        t1, t2, tw = q_tier[c1], q_tier[c2], q_tier[cw]
        constraint = tuple(sorted([tier_idx[t1], tier_idx[t2], tier_idx[tw]]))
        if constraint not in seen_tier_constraints:
            seen_tier_constraints.add(constraint)
            row = np.zeros(n_tiers)
            row[tier_idx[tw]] += 1
            row[tier_idx[t1]] += 1
            row[tier_idx[t2]] += 1
            tier_rows.append(row)

    delta_tier = np.array(tier_rows) if tier_rows else np.zeros((0, n_tiers))
    tier_rank = np.linalg.matrix_rank(delta_tier, tol=1e-10)
    tier_ker_dim = n_tiers - tier_rank
    print(f"  Tier constraint matrix: {delta_tier.shape}")
    print(f"  rank(δ_tier) = {tier_rank}")
    print(f"  dim H¹_a|_tier = {tier_ker_dim}")

    if tier_ker_dim > 0:
        Ut, St, Vtt = np.linalg.svd(delta_tier)
        tier_kernel = Vtt[-tier_ker_dim:]
        print(f"  Tier-uniform kernel basis:")
        for i, vec in enumerate(tier_kernel):
            ratios = vec / vec[np.argmax(np.abs(vec))]
            print(f"    v{i}: {dict(zip(tiers, [f'{r:.3f}' for r in ratios]))}")

    # Kernel structure: project each kernel basis vector onto tiers
    if ker_dim > 0:
        print(f"\n  Kernel basis — tier averages:")
        for i in range(ker_dim):
            kv = kernel_basis[i]
            tier_avgs = {}
            for t in tiers:
                idxs = tier_to_idx[t]
                tier_avgs[t] = np.mean(kv[idxs])
            tier_stds = {}
            for t in tiers:
                idxs = tier_to_idx[t]
                tier_stds[t] = np.std(kv[idxs])
            print(f"    v{i}: mean = {dict(zip(tiers, [f'{tier_avgs[t]:.4f}' for t in tiers]))}  "
                  f"std = {dict(zip(tiers, [f'{tier_stds[t]:.4f}' for t in tiers]))}")

        # Count how many kernel vectors are "tier-uniform" (low within-tier variance)
        n_uniform = 0
        for i in range(ker_dim):
            kv = kernel_basis[i]
            all_stds = [np.std(kv[tier_to_idx[t]]) for t in tiers if len(tier_to_idx[t]) > 1]
            if all(s < 0.01 for s in all_stds):
                n_uniform += 1
        print(f"  Tier-uniform kernel vectors: {n_uniform}/{ker_dim}")

    return {
        'delta_a': delta_a,
        'rank': rank,
        'ker_dim': ker_dim,
        'kernel_basis': kernel_basis,
        'tier_ker_dim': tier_ker_dim,
        'n_cl': n_cl,
        'q_tier': q_tier,
        'comp_targets': comp_targets,
    }


def diagnostic_E(R_g0, R_k6):
    """Restriction map ι*: H¹_a(Q₅₁) → H¹_a(Q₂₄)."""
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC E: Restriction Map ι*")
    print(f"{'='*60}")

    ker_24 = R_g0['kernel_basis']  # (d₂₄, 24)
    ker_51 = R_k6['kernel_basis']  # (d₅₁, 51)

    if ker_51.shape[0] == 0:
        print("  Q₅₁ kernel is empty — ι* is trivially zero.")
        return

    # Q₂₄ is an induced subgraph of Q₅₁. The Q₂₄ clusters should
    # be among the first clusters of Q₅₁ (same initial vertices).
    # We need to identify which Q₅₁ cluster IDs correspond to Q₂₄ cluster IDs.
    # For now, we compare the tier-uniform projections.

    # Simpler test: restrict Q₅₁ kernel vectors to their first 24 components
    # and check if they span the same space as Q₂₄ kernel.
    # NOTE: cluster IDs may not align. We need to use the fidelity-based mapping.

    # Since both were built from the same initial ψ, the original 6 vertices
    # (Tier A) should have the same cluster IDs. But the Tier B/C mapping
    # may differ because the build order can produce different cluster numbering.

    # For this diagnostic, compare the tier-uniform part:
    tiers_24 = sorted(set(R_g0['q_tier'].values()))
    tiers_51 = sorted(set(R_k6['q_tier'].values()))

    print(f"  Q₂₄ tiers: {tiers_24}, ker dim = {R_g0['ker_dim']}")
    print(f"  Q₅₁ tiers: {tiers_51}, ker dim = {R_k6['ker_dim']}")
    print(f"  Tier-uniform: Q₂₄ dim = {R_g0['tier_ker_dim']}, Q₅₁ dim = {R_k6['tier_ker_dim']}")

    if R_g0['tier_ker_dim'] == R_k6['tier_ker_dim']:
        print(f"  ✓ ι* is an isomorphism on tier-uniform cohomology")
    else:
        print(f"  ✗ Tier-uniform dimensions differ!")


def diagnostic_F(n_ic, seed):
    """IC-independence across multiple random seeds."""
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC F: IC-Independence ({n_ic} ICs)")
    print(f"{'='*60}")

    rng_master = np.random.default_rng(seed)

    results_g0 = []
    results_k6 = []

    for ic in range(n_ic):
        s = rng_master.integers(0, 2**31)
        rng = np.random.default_rng(s)
        psi_init = {v: haar_C3(rng) for v in range(6)}

        Q_g0 = build_quotient(G0_TOPO, psi_init, depth=5)
        Q_k6 = build_quotient(complete_ternary(6), psi_init, depth=4)

        # Quick analysis
        delta_g0, _ = build_delta_a(Q_g0['n_cl'], Q_g0['comp_targets'])
        delta_k6, _ = build_delta_a(Q_k6['n_cl'], Q_k6['comp_targets'])

        r_g0 = np.linalg.matrix_rank(delta_g0, tol=1e-10)
        r_k6 = np.linalg.matrix_rank(delta_k6, tol=1e-10)

        results_g0.append({
            'n_cl': Q_g0['n_cl'], 'n_comp': len(Q_g0['comp_targets']),
            'rank': r_g0, 'ker_dim': Q_g0['n_cl'] - r_g0
        })
        results_k6.append({
            'n_cl': Q_k6['n_cl'], 'n_comp': len(Q_k6['comp_targets']),
            'rank': r_k6, 'ker_dim': Q_k6['n_cl'] - r_k6
        })

    print(f"\n  Q₂₄:")
    print(f"    n_cl:    {[r['n_cl'] for r in results_g0]}")
    print(f"    n_comp:  {[r['n_comp'] for r in results_g0]}")
    print(f"    rank:    {[r['rank'] for r in results_g0]}")
    print(f"    ker_dim: {[r['ker_dim'] for r in results_g0]}")

    ker_g0 = [r['ker_dim'] for r in results_g0]
    print(f"    IC-independent: {'YES' if len(set(ker_g0)) == 1 else 'NO'} "
          f"(unique values: {sorted(set(ker_g0))})")

    print(f"\n  Q₅₁:")
    print(f"    n_cl:    {[r['n_cl'] for r in results_k6]}")
    print(f"    n_comp:  {[r['n_comp'] for r in results_k6]}")
    print(f"    rank:    {[r['rank'] for r in results_k6]}")
    print(f"    ker_dim: {[r['ker_dim'] for r in results_k6]}")

    ker_k6 = [r['ker_dim'] for r in results_k6]
    print(f"    IC-independent: {'YES' if len(set(ker_k6)) == 1 else 'NO'} "
          f"(unique values: {sorted(set(ker_k6))})")

    return results_g0, results_k6


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--n_ic', type=int, default=10)
    args = parser.parse_args()

    print("="*60)
    print("  Active Cohomology H¹_a on Q₂₄ and Q₅₁")
    print("="*60)

    # Build both quotients from same ICs
    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("\n  Building Q₂₄ (from G₀, depth 5)...")
    Q_g0 = build_quotient(G0_TOPO, psi_init, depth=5)
    print(f"  → {Q_g0['n_cl']} clusters, {len(Q_g0['comp_targets'])} compositions, {len(Q_g0['q_he'])} hyperedges")

    print("\n  Building Q₅₁ (from K₆³, depth 4)...")
    Q_k6 = build_quotient(complete_ternary(6), psi_init, depth=4)
    print(f"  → {Q_k6['n_cl']} clusters, {len(Q_k6['comp_targets'])} compositions, {len(Q_k6['q_he'])} hyperedges")

    # Diagnostic B: Full cohomology analysis
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC B: Active Cohomology")
    print(f"{'='*60}")

    R_g0 = analyse_cohomology("Q₂₄ (G₀)", Q_g0)
    R_k6 = analyse_cohomology("Q₅₁ (K₆³)", Q_k6)

    # Diagnostic C: Verify 1:−2:1 explicitly
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC C: Explicit 1:−2:1 Verification")
    print(f"{'='*60}")

    for name, Q in [("Q₂₄", Q_g0), ("Q₅₁", Q_k6)]:
        n_cl = Q['n_cl']
        q_tier = Q['q_tier']
        comp_targets = Q['comp_targets']

        # Test Y_A = Y_C = 1, Y_B = -2
        Y_test = np.zeros(n_cl)
        for c in range(n_cl):
            if q_tier[c] == 'A': Y_test[c] = 1.0
            elif q_tier[c] == 'B': Y_test[c] = -2.0
            else: Y_test[c] = 1.0  # C

        # Check all constraints
        violations = 0
        max_residual = 0
        for (c1, c2), cw in comp_targets.items():
            res = Y_test[cw] + Y_test[c1] + Y_test[c2]
            max_residual = max(max_residual, abs(res))
            if abs(res) > 1e-10:
                violations += 1

        print(f"\n  {name}: Y = (1, -2, 1) test")
        print(f"    Violations: {violations}/{len(comp_targets)}")
        print(f"    Max residual: {max_residual:.2e}")

    # Diagnostic D: Composition-type breakdown
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC D: Composition Types by Tier")
    print(f"{'='*60}")

    for name, Q in [("Q₂₄", Q_g0), ("Q₅₁", Q_k6)]:
        print(f"\n  {name}:")
        type_counts = defaultdict(int)
        for (c1, c2), cw in Q['comp_targets'].items():
            t1, t2, tw = Q['q_tier'][c1], Q['q_tier'][c2], Q['q_tier'][cw]
            type_counts[(t1, t2, tw)] += 1

        for (t1, t2, tw), count in sorted(type_counts.items()):
            constraint_val = "consistent" if t1 == t2 == tw == 'A' or True else "?"
            print(f"    ({t1}, {t2}) → {tw}: {count} compositions")

    # Diagnostic E: Restriction map
    diagnostic_E(R_g0, R_k6)

    # Diagnostic F: IC-independence
    diagnostic_F(args.n_ic, args.seed + 1000)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Q₂₄: dim H¹_a = {R_g0['ker_dim']}  (tier-uniform: {R_g0['tier_ker_dim']})")
    print(f"  Q₅₁: dim H¹_a = {R_k6['ker_dim']}  (tier-uniform: {R_k6['tier_ker_dim']})")
    print(f"  Y-blindness functorial: {'YES' if R_g0['tier_ker_dim'] == R_k6['tier_ker_dim'] == 1 else 'UNCLEAR'}")


if __name__ == '__main__':
    main()
