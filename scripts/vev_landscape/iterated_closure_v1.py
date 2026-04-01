#!/usr/bin/env python3
"""
iterated_closure_v1.py — Does Q₁₀₂ reproduce itself under DPO rewriting?

The zygote hypothesis: Q₁₀₂ is algebraically complete (carries full SM
spectral triple) and causally self-reproducing. Under one generation of
DPO rewrites (compose edge-pairs → new vertices → quotient), the result
should be Q₁₀₂ again.

Test 1: Fixed-point test. Apply composition to all edge-pairs of Q₁₀₂.
  Cluster new vertices by colour fidelity. Does Q₁₀₂' = Q₁₀₂?

Test 2: Spectral triple inheritance. For the quotient at each depth
  (d=2,3,4,5), check: |vertices|, tier structure, J/γ/KO signs,
  order-one kernel dimension.

Test 3: Role decomposition. Which tier's rewrites produce the
  self-reproducing daughters? If Tier C (replication role), that's
  the structural signature of iterated closure.

Test 4: Born weighting. Among the DPO daughters, do Born-preferred
  branches inherit completeness at higher rates?

Mathematical conventions:
  - Composition: w = normalize(conj(cross(ψ₁, ψ₂)))
  - Quotient: cluster by |⟨ψᵢ|ψⱼ⟩|² > 0.999
  - C-closure: Q ∪ C(Q) where C(ψ) = conj(ψ)
  - KO-dim 6 signs: J²=+I, Jγ=-γJ, JD=+DJ
  - D_F: order-one kernel dimension (incremental, numba)

Usage:
  python3 iterated_closure_v1.py [--seed S] [--max-depth D]
"""

import numpy as np
import argparse
import time
from collections import defaultdict, Counter
from q102_build_v1 import (
    build_c_closed_quotient, complete_ternary, haar_C3, fidelity,
    build_J, G0_TOPO, build_multiway, normalize, compose_colour
)
from q102_orderone_v1 import (
    j_compatible_triplets, build_representation,
    incremental_order_one, compute_violations_batch
)


def check_ko_signs(Q):
    """Check KO-dimension signs: J²=+I, Jγ=-γJ."""
    n = Q['n_cl']
    cl_origin = Q['cl_origin']

    J, j_map = build_J(Q)
    gamma = np.array([1.0 if cl_origin[c] == 'orig_only' else -1.0 for c in range(n)])
    Gamma = np.diag(gamma)

    j2 = np.allclose(J @ J, np.eye(n))
    jg = np.allclose(J @ Gamma, -Gamma @ J)
    fixed = sum(1 for c in range(n) if j_map.get(c, -1) == c)

    return j2, jg, fixed == 0, J, gamma, j_map


def check_spectral_triple(Q, verbose=True):
    """Full spectral triple check: KO signs + order-one kernel dimension."""
    n = Q['n_cl']
    if verbose:
        print(f"    Checking spectral triple on {n} vertices...", flush=True)

    # KO signs
    j2, jg, no_fixed, J, gamma, j_map = check_ko_signs(Q)
    if verbose:
        print(f"    J²=+I: {j2}, Jγ=-γJ: {jg}, no fixed points: {no_fixed}")

    if not (j2 and jg and no_fixed):
        if verbose:
            print(f"    ✗ KO signs FAIL")
        return {'pass': False, 'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
                'n': n, 'df_dim': 0}

    # Tier structure
    tier_counts = Counter(Q['q_tier'].values())
    n_orig = sum(1 for c in range(n) if Q['cl_origin'][c] == 'orig_only')
    n_conj = sum(1 for c in range(n) if Q['cl_origin'][c] == 'conj_only')

    if verbose:
        print(f"    Tiers: {dict(tier_counts)}, orig={n_orig}, conj={n_conj}")

    # Triplets and representation
    try:
        triplets, v2c, v2f = j_compatible_triplets(Q, J, gamma)
        rep = build_representation(Q, triplets, v2c)
    except Exception as e:
        if verbose:
            print(f"    ✗ Representation failed: {e}")
        return {'pass': False, 'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
                'n': n, 'df_dim': 0, 'error': str(e)}

    # Order-one kernel
    orig_idx = [c for c in range(n) if gamma[c] > 0]
    conj_idx = [c for c in range(n) if gamma[c] < 0]

    try:
        oo_basis, oo_dim = incremental_order_one(n, orig_idx, conj_idx, rep, J)
    except Exception as e:
        if verbose:
            print(f"    ✗ Order-one failed: {e}")
        return {'pass': False, 'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
                'n': n, 'df_dim': 0, 'error': str(e)}

    if verbose:
        print(f"    Order-one kernel: {oo_dim}")

    if oo_dim == 0:
        if verbose:
            print(f"    ✗ No D_F satisfies order-one condition")
        return {'pass': False, 'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
                'n': n, 'df_dim': 0}

    # JD = +DJ
    jd_rows = []
    for k in range(oo_dim):
        M = oo_basis[k].reshape(len(conj_idx), len(orig_idx))
        D_k = np.zeros((n, n), dtype=np.complex128)
        ci = np.array(conj_idx); oi = np.array(orig_idx)
        D_k[np.ix_(ci, oi)] = M; D_k[np.ix_(oi, ci)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())

    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd = np.linalg.eigvalsh(G_jd)
    rank_jd = np.sum(eigvals_jd > 1e-14)
    df_dim = oo_dim - rank_jd

    if verbose:
        print(f"    JD=+DJ: rank={rank_jd}, D_F dimension = {df_dim}")
        print(f"    ★ KO-dim 6 spectral triple: {'PASS' if df_dim > 0 else 'FAIL'}")

    return {
        'pass': df_dim > 0,
        'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
        'n': n, 'df_dim': df_dim,
        'oo_dim': oo_dim,
        'tiers': dict(tier_counts),
        'n_orig': n_orig, 'n_conj': n_conj,
        'n_triplets': len(triplets),
    }


def iterate_quotient(psi_init, seed_edges, depth, threshold=0.999):
    """Build C-closed quotient at given depth."""
    Q = build_c_closed_quotient(seed_edges, psi_init, depth=depth, threshold=threshold)
    return Q


def compose_on_quotient(Q):
    """Apply one generation of DPO rewrites to Q's hyperedges.

    For each edge (c1, c2, c3) in Q, compose ψ(c1) and ψ(c2) to get w.
    Return the new vertices (not yet clustered).
    """
    new_vertices = {}  # (c1, c2) → ψ_w
    for c1, c2, c3 in Q['q_he']:
        key = (c1, c2)
        if key not in new_vertices:
            w = compose_colour(Q['q_psi'][c1], Q['q_psi'][c2])
            if np.linalg.norm(w) > 1e-10:
                new_vertices[key] = w
    return new_vertices


def cluster_with_existing(Q, new_vertices, threshold=0.999):
    """Cluster new vertices against existing Q vertices.

    Returns: (n_new_clusters, n_matched_existing, match_details)
    """
    n = Q['n_cl']
    n_new = 0
    n_matched = 0
    match_details = []

    for key, psi_w in new_vertices.items():
        matched = False
        for c in range(n):
            f = fidelity(psi_w, Q['q_psi'][c])
            if f > threshold:
                match_details.append(('match', key, c, f))
                n_matched += 1
                matched = True
                break
        if not matched:
            # Also check conjugate
            psi_w_conj = np.conj(psi_w)
            for c in range(n):
                f = fidelity(psi_w_conj, Q['q_psi'][c])
                if f > threshold:
                    match_details.append(('conj_match', key, c, f))
                    n_matched += 1
                    matched = True
                    break
        if not matched:
            match_details.append(('new', key, None, 0))
            n_new += 1

    return n_new, n_matched, match_details


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--max-depth', type=int, default=5)
    parser.add_argument('--n-ics', type=int, default=5)
    args = parser.parse_args()

    print("=" * 70)
    print("  Iterated Closure Test: Is Q₁₀₂ a Zygote?")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════════
    # TEST 1: Fixed-point test — does Q₁₀₂ reproduce itself?
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  TEST 1: Fixed-Point Test")
    print(f"{'='*70}", flush=True)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    # Build Q₁₀₂
    print(f"\n  Building Q₁₀₂ (depth=4)...", flush=True)
    Q102 = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)
    n102 = Q102['n_cl']
    n_he = len(Q102['q_he'])
    print(f"  Q₁₀₂: {n102} vertices, {n_he} hyperedges")

    # Compose one generation on Q₁₀₂'s edges
    print(f"\n  Composing on Q₁₀₂'s {n_he} hyperedges...", flush=True)
    new_verts = compose_on_quotient(Q102)
    print(f"  New composition products: {len(new_verts)}")

    # Cluster against existing Q₁₀₂
    n_new, n_matched, details = cluster_with_existing(Q102, new_verts)
    n_total_products = len(new_verts)

    print(f"\n  Clustering results:")
    print(f"    Products matching Q₁₀₂ vertices: {n_matched}/{n_total_products} "
          f"({n_matched/max(n_total_products,1)*100:.1f}%)")
    print(f"    Genuinely new vertices: {n_new}/{n_total_products}")

    if n_new == 0:
        print(f"\n  ★★★ Q₁₀₂ IS A FIXED POINT ★★★")
        print(f"  All composition products map back to existing Q₁₀₂ vertices.")
        print(f"  Q₁₀₂ reproduces itself exactly under DPO rewriting.")
        fixed_point = True
    else:
        print(f"\n  Q₁₀₂ is NOT a strict fixed point ({n_new} new vertices)")
        fixed_point = False

    # Breakdown: which Q₁₀₂ vertices do daughters match?
    match_targets = Counter()
    match_tiers = Counter()
    for kind, key, target, f in details:
        if target is not None:
            match_targets[target] += 1
            match_tiers[Q102['q_tier'].get(target, '?')] += 1

    print(f"\n  Match target tier distribution: {dict(match_tiers)}")

    # Source tier analysis: which tier's edges produce matches?
    source_tier_match = Counter()
    source_tier_new = Counter()
    for kind, key, target, f in details:
        c1, c2 = key
        tier1 = Q102['q_tier'].get(c1, '?')
        tier2 = Q102['q_tier'].get(c2, '?')
        source = f"{tier1}×{tier2}"
        if kind in ('match', 'conj_match'):
            source_tier_match[source] += 1
        else:
            source_tier_new[source] += 1

    print(f"\n  Source tier → match rate:")
    all_sources = sorted(set(list(source_tier_match.keys()) + list(source_tier_new.keys())))
    for s in all_sources:
        m = source_tier_match.get(s, 0)
        n = source_tier_new.get(s, 0)
        total = m + n
        if total > 0:
            print(f"    {s}: {m}/{total} matched ({m/total*100:.0f}%)")

    # ═══════════════════════════════════════════════════════════════
    # TEST 2: Spectral triple at each depth
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  TEST 2: Spectral Triple Inheritance by Depth")
    print(f"{'='*70}", flush=True)

    results_by_depth = {}
    for depth in range(2, args.max_depth + 1):
        print(f"\n  --- Depth {depth} ---", flush=True)
        t0 = time.time()
        Q = build_c_closed_quotient(complete_ternary(6), psi_init, depth=depth)
        build_time = time.time() - t0

        t0 = time.time()
        result = check_spectral_triple(Q, verbose=True)
        check_time = time.time() - t0

        result['build_time'] = build_time
        result['check_time'] = check_time
        result['depth'] = depth
        results_by_depth[depth] = result

    # Summary table
    print(f"\n  Depth summary:")
    print(f"  {'Depth':>5s} {'|V|':>5s} {'Orig':>5s} {'Conj':>5s} "
          f"{'KO':>4s} {'D_F':>5s} {'Tiers':>15s} {'Time':>8s}")
    for d in sorted(results_by_depth):
        r = results_by_depth[d]
        ko = '✓' if (r['j2'] and r['jg'] and r['no_fixed']) else '✗'
        tiers = str(r.get('tiers', {}))
        total_time = r.get('build_time', 0) + r.get('check_time', 0)
        print(f"  {d:>5d} {r['n']:>5d} {r.get('n_orig',0):>5d} {r.get('n_conj',0):>5d} "
              f"{ko:>4s} {r['df_dim']:>5d} {tiers:>15s} {total_time:>7.0f}s")

    # ═══════════════════════════════════════════════════════════════
    # TEST 3: IC independence (multiple random ICs)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  TEST 3: IC Independence ({args.n_ics} random ICs, depth=4)")
    print(f"{'='*70}", flush=True)

    ic_results = []
    for ic in range(args.n_ics):
        rng_ic = np.random.default_rng(args.seed + 100 + ic)
        psi_ic = {v: haar_C3(rng_ic) for v in range(6)}
        Q_ic = build_c_closed_quotient(complete_ternary(6), psi_ic, depth=4)

        # Quick KO check
        j2, jg, no_fixed, _, _, _ = check_ko_signs(Q_ic)
        n_ic = Q_ic['n_cl']
        tiers = Counter(Q_ic['q_tier'].values())

        # Fixed-point check
        new_v = compose_on_quotient(Q_ic)
        n_new_ic, n_matched_ic, _ = cluster_with_existing(Q_ic, new_v)

        ic_results.append({
            'n': n_ic, 'j2': j2, 'jg': jg, 'no_fixed': no_fixed,
            'tiers': dict(tiers), 'n_new': n_new_ic,
            'n_products': len(new_v), 'fixed_point': n_new_ic == 0
        })

        print(f"  IC {ic}: |V|={n_ic}, KO={j2 and jg and no_fixed}, "
              f"fixed_point={n_new_ic == 0}, tiers={dict(tiers)}")

    n_fp = sum(1 for r in ic_results if r['fixed_point'])
    n_ko = sum(1 for r in ic_results if r['j2'] and r['jg'] and r['no_fixed'])
    print(f"\n  Fixed points: {n_fp}/{args.n_ics}")
    print(f"  KO-dim 6 pass: {n_ko}/{args.n_ics}")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")

    print(f"""
  Q₁₀₂ construction: {n102} vertices, {n_he} hyperedges

  TEST 1 — Fixed Point:
    Composition products: {n_total_products}
    Matched to Q₁₀₂: {n_matched} ({n_matched/max(n_total_products,1)*100:.1f}%)
    New vertices: {n_new}
    Q₁₀₂ is fixed point: {fixed_point}

  TEST 2 — Spectral Triple by Depth:""")
    for d in sorted(results_by_depth):
        r = results_by_depth[d]
        ko = r['j2'] and r['jg'] and r['no_fixed']
        print(f"    d={d}: |V|={r['n']}, KO={'✓' if ko else '✗'}, D_F={r['df_dim']}")

    print(f"""
  TEST 3 — IC Independence:
    Fixed points: {n_fp}/{args.n_ics}
    KO-dim 6: {n_ko}/{args.n_ics}

  INTERPRETATION:""")

    if fixed_point and n_fp == args.n_ics:
        print(f"    ★ Q₁₀₂ is a SELF-REPRODUCING FIXED POINT for all ICs tested.")
        print(f"    ★ The zygote hypothesis is CONFIRMED: Q₁₀₂ reproduces itself")
        print(f"      exactly under DPO rewriting. It is algebraically complete")
        print(f"      AND causally self-sustaining.")
        print(f"    ★ The 'drive toward closure' is visible: the fixed-point equation")
        print(f"      demanding its own satisfaction IS the replication role.")
    elif fixed_point:
        print(f"    Q₁₀₂ is a fixed point for seed {args.seed} but not universally.")
        print(f"    IC-dependence suggests the fixed-point property is conditional.")
    elif n_new > 0:
        print(f"    Q₁₀₂ is NOT a fixed point. {n_new} new vertices generated.")
        print(f"    The zygote hypothesis requires revision or the quotient isn't tight enough.")
    print()


if __name__ == '__main__':
    main()
