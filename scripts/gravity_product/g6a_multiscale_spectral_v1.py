#!/usr/bin/env python3
"""
g6a_multiscale_spectral_v1.py — Spectral action across Q_n scales

Computes Seeley-DeWitt coefficients a₀, a₂, a₄ on C-closed quotients
at four graph densities:

  G₀ (6 edges, 5%)     → Q₄₈
  Adjacent (36, 30%)    → Q~84
  Adj+Stride2 (48, 40%) → Q~84
  K₆³ (120, 100%)      → Q₁₀₂

For each: build C-closed quotient, construct J/γ/D_F via existing
numba-accelerated order-one infrastructure, decompose spectral action
into gravity (L⁴), Higgs (D_F⁴), and interaction (C² + mixed) sectors.

Key input from S97: Tr(D_F²) = const (a₂ frozen). All running lives in a₄.
The n-dependence of spectral action coefficients IS the running of couplings.

Mathematical conventions:
  - Composition: conj(a × b) (SU(3)-equivariant, Q₂₄ convention)
  - J: charge conjugation, J[c] = conj(ψ[c]) matched to cluster
  - γ: +1 for orig sector, -1 for conj sector
  - D_F: off-diagonal (conj→orig, orig→conj), order-one + JD=+DJ
  - L: unnormalized graph Laplacian (degree - adjacency)
  - D_full = L + α·D_F at natural scale α = ||L||_F/||D_F||_F
  - a₂ = Tr(D²), a₄ = Tr(D⁴)

Generator set: 13 generators = 9 E_{ij} (M₃ℂ) + 3 σ_k (ℍ) + I_H.
Uses numba-accelerated incremental order-one from q102_orderone_v1.py.

IC-dependence: averaging over multiple ICs to separate structural from
IC-dependent quantities. S97 (Tr(D²)=const, CV=0) and S124 (mass gap CV=0)
suggest key observables are IC-independent.

Usage: python g6a_multiscale_spectral_v1.py [--n_ic N] [--seed S] [--depth D]
"""

import numpy as np
import argparse
import sys
import time
import itertools
from collections import defaultdict, Counter

# Import existing infrastructure
from q102_build_v1 import (
    build_c_closed_quotient, complete_ternary, haar_C3, fidelity,
    build_J, build_multiway, G0_TOPO
)
from q102_orderone_v1 import (
    j_compatible_triplets, build_representation,
    incremental_order_one
)


# ═══════════════════════════════════════════════════════════════════════════════
# SEED TOPOLOGIES (from g8a_multiscale_v1.py)
# ═══════════════════════════════════════════════════════════════════════════════

def G0_cyclic():
    """G₀: cyclic hexagon, 6 edges. ~5% of K₆³."""
    return [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

def adjacent_ternary():
    """Adjacent triples: (i, i+1, i+2) + all permutations. ~30% of K₆³."""
    edges = set()
    for i in range(6):
        triple = (i, (i+1)%6, (i+2)%6)
        for p in itertools.permutations(triple):
            edges.add(p)
    return list(edges)

def stride2_ternary():
    """Stride-2 triples: (i, i+2, i+4) + all permutations."""
    edges = set()
    for i in range(6):
        triple = (i, (i+2)%6, (i+4)%6)
        for p in itertools.permutations(triple):
            edges.add(p)
    return list(edges)

def combined_adj_stride2():
    """Adjacent + stride-2 union. ~40% of K₆³."""
    return list(set(adjacent_ternary()) | set(stride2_ternary()))


TOPOLOGIES = [
    ("G₀ (cyclic)", G0_cyclic, 6/120),
    ("Adjacent", adjacent_ternary, 36/120),
    ("Adj+Stride2", combined_adj_stride2, 48/120),
    ("K₆³ (complete)", lambda: complete_ternary(6), 1.0),
]


# ═══════════════════════════════════════════════════════════════════════════════
# LAPLACIAN
# ═══════════════════════════════════════════════════════════════════════════════

def build_laplacian(Q):
    """Unnormalized graph Laplacian from hyperedges."""
    n = Q['n_cl']
    adj = np.zeros((n, n))
    for c1, c2, c3 in Q['q_he']:
        adj[c1,c2] = adj[c2,c1] = 1
        adj[c1,c3] = adj[c3,c1] = 1
        adj[c2,c3] = adj[c3,c2] = 1
    np.fill_diagonal(adj, 0)
    deg = adj.sum(axis=1)
    L = np.diag(deg) - adj
    return L, adj, deg


# ═══════════════════════════════════════════════════════════════════════════════
# D_F CONSTRUCTION (from g1_gravity_spectral_v1.py, generalized)
# ═══════════════════════════════════════════════════════════════════════════════

def build_sample_DF(Q, J):
    """Build a representative D_F on any C-closed quotient.

    Uses the existing numba-accelerated order-one code.
    Returns D_F matrix, D_F dimension, gamma array.
    """
    n = Q['n_cl']
    gamma = np.array([1.0 if Q['cl_origin'][c]=='orig_only' else -1.0
                       for c in range(n)])
    # 'both' vertices: assign to orig sector
    for c in range(n):
        if Q['cl_origin'][c] == 'both':
            gamma[c] = 1.0

    orig_idx = [c for c in range(n) if gamma[c] > 0]
    conj_idx = [c for c in range(n) if gamma[c] < 0]

    triplets, v2c, v2f = j_compatible_triplets(Q, J, gamma)
    rep = build_representation(Q, triplets, v2c)

    print(f"    Triplets: {len(triplets)}, generators: {len(rep)}")
    oo_basis, oo_dim = incremental_order_one(n, orig_idx, conj_idx, rep, J)

    if oo_dim == 0:
        return None, 0, gamma

    # JD = +DJ constraint
    print(f"    Applying JD = +DJ on {oo_dim}-dim kernel...")
    jd_rows = []
    for k in range(oo_dim):
        M = oo_basis[k].reshape(len(conj_idx), len(orig_idx))
        D_k = np.zeros((n, n), dtype=np.complex128)
        ci_arr = np.array(conj_idx); oi_arr = np.array(orig_idx)
        D_k[np.ix_(ci_arr, oi_arr)] = M
        D_k[np.ix_(oi_arr, ci_arr)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())

    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd, eigvecs_jd = np.linalg.eigh(G_jd)
    ker_mask = eigvals_jd < 1e-14
    final_coords = eigvecs_jd[:, ker_mask].T
    final_basis = final_coords @ oo_basis
    dim_DF = final_basis.shape[0]
    print(f"    D_F dimension after JD=+DJ: {dim_DF}")

    if dim_DF == 0:
        return None, 0, gamma

    # Build representative D_F (normalised sum of basis)
    n_conj = len(conj_idx); n_orig = len(orig_idx)
    M_rep = np.zeros((n_conj, n_orig))
    for k in range(dim_DF):
        M_rep += final_basis[k].reshape(n_conj, n_orig)
    M_rep /= np.linalg.norm(M_rep)

    D_F = np.zeros((n, n))
    ci_arr = np.array(conj_idx); oi_arr = np.array(orig_idx)
    D_F[np.ix_(ci_arr, oi_arr)] = M_rep
    D_F[np.ix_(oi_arr, ci_arr)] = M_rep.T

    return D_F, dim_DF, gamma


# ═══════════════════════════════════════════════════════════════════════════════
# SPECTRAL ACTION DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

def spectral_action_decomposition(L, D_F, n):
    """Compute a₀, a₂, a₄ with sector decomposition.

    D_full = L + α·D_F where α = ||L||_F / ||D_F||_F (natural scale).
    """
    tr_L2 = np.trace(L @ L).real
    tr_DF2 = np.trace(D_F @ D_F).real

    alpha = np.sqrt(tr_L2 / tr_DF2) if tr_DF2 > 1e-15 else 1.0
    D_F_s = D_F * alpha

    D = L + D_F_s
    C = L @ D_F_s + D_F_s @ L

    # a₀, a₂
    a0 = n
    D2 = D @ D; L2 = L @ L; DF2 = D_F_s @ D_F_s
    a2_total = np.trace(D2).real
    a2_L = np.trace(L2).real
    a2_DF = np.trace(DF2).real
    a2_cross = np.trace(C).real

    # a₄
    D4 = D2 @ D2; L4 = L2 @ L2; DF4 = DF2 @ DF2
    C2 = C @ C
    mixed = L2 @ DF2 + DF2 @ L2

    a4_total = np.trace(D4).real
    a4_L = np.trace(L4).real
    a4_DF = np.trace(DF4).real
    a4_C2 = np.trace(C2).real
    a4_mixed = np.trace(mixed).real
    a4_interaction = a4_C2 + a4_mixed

    # Frobenius decomposition
    D2_frob = np.linalg.norm(D2, 'fro')**2

    # γ-orthogonality
    gamma_orth = np.trace(L @ D_F_s).real

    # [L², D_F²] commutator
    comm = L2 @ DF2 - DF2 @ L2
    comm_rel = np.linalg.norm(comm, 'fro') / (np.linalg.norm(L2, 'fro') * np.linalg.norm(DF2, 'fro') + 1e-30)

    return {
        'n': n, 'alpha': alpha, 'a0': a0,
        'a2_total': a2_total, 'a2_L': a2_L, 'a2_DF': a2_DF, 'a2_cross': a2_cross,
        'a4_total': a4_total, 'a4_L': a4_L, 'a4_DF': a4_DF,
        'a4_C2': a4_C2, 'a4_mixed': a4_mixed, 'a4_interaction': a4_interaction,
        'a4_grav_frac': a4_L / a4_total if a4_total > 0 else 0,
        'a4_higgs_frac': a4_DF / a4_total if a4_total > 0 else 0,
        'a4_int_frac': a4_interaction / a4_total if a4_total > 0 else 0,
        'gamma_orth': gamma_orth, 'comm_rel': comm_rel,
        'tr_df2_unscaled': tr_DF2,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TOPOLOGY PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def process_topology(name, seed_fn, density, psi_init, depth):
    """Build C-closed quotient and compute spectral action."""
    seed_edges = seed_fn()
    n_edges = len(seed_edges)

    print(f"\n{'─'*60}")
    print(f"  {name}: {n_edges} seed edges, density={density:.1%}")
    print(f"{'─'*60}")

    t0 = time.time()

    # Build C-closed quotient
    Q = build_c_closed_quotient(seed_edges, psi_init, depth=depth)
    n = Q['n_cl']

    tc = Counter(Q['q_tier'].values())
    tier_str = ", ".join(f"{t}:{tc[t]}" for t in sorted(tc))
    print(f"  Quotient: {n} vertices ({tier_str})")
    print(f"  Hyperedges: {len(Q['q_he'])}")

    orig = sum(1 for v in Q['cl_origin'].values() if v == 'orig_only')
    conj = sum(1 for v in Q['cl_origin'].values() if v == 'conj_only')
    both = sum(1 for v in Q['cl_origin'].values() if v == 'both')
    print(f"  Origin: {orig} orig + {conj} conj + {both} overlap")

    # J
    J, j_map = build_J(Q)
    j2_ok = np.allclose(J @ J, np.eye(n))
    print(f"  J²=I: {j2_ok}")

    # Laplacian
    L, adj, deg = build_laplacian(Q)
    n_graph_edges = int(adj.sum()//2)
    print(f"  Graph edges: {n_graph_edges}, degree: {int(deg.min())}–{int(deg.max())}")

    # D_F
    print(f"  Building D_F...")
    D_F, dim_DF, gamma = build_sample_DF(Q, J)

    if D_F is None:
        print(f"  ERROR: D_F construction failed")
        return None

    # Spectral action
    print(f"  Computing spectral action...")
    sa = spectral_action_decomposition(L, D_F, n)

    t_elapsed = time.time() - t0
    print(f"\n  Scale α = {sa['alpha']:.2f}")
    print(f"  a₀ = {sa['a0']}")
    print(f"  a₂: total={sa['a2_total']:.1f}, L²={sa['a2_L']:.1f}, "
          f"D_F²={sa['a2_DF']:.1f}, cross={sa['a2_cross']:.2e}")
    print(f"  a₄: total={sa['a4_total']:.0f}")
    print(f"    gravity(L⁴):     {sa['a4_L']:.0f} ({sa['a4_grav_frac']:.1%})")
    print(f"    Higgs(D_F⁴):     {sa['a4_DF']:.2f} ({sa['a4_higgs_frac']:.1%})")
    print(f"    interaction:      {sa['a4_interaction']:.0f} ({sa['a4_int_frac']:.1%})")
    print(f"  γ-orth: {sa['gamma_orth']:.2e}, [L²,D_F²]={sa['comm_rel']:.4f}")
    print(f"  Tr(D_F²) raw: {sa['tr_df2_unscaled']:.6f}")
    print(f"  Time: {t_elapsed:.0f}s")

    sa['name'] = name; sa['density'] = density; sa['dim_DF'] = dim_DF
    sa['n_edges'] = n_edges; sa['n_he'] = len(Q['q_he'])
    sa['n_graph_edges'] = n_graph_edges
    return sa


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n_ic', type=int, default=3, help='ICs to average')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--depth', type=int, default=4)
    args = parser.parse_args()

    print("="*60)
    print("  G6a: Multi-Scale Spectral Action — Running Couplings")
    print("="*60)
    print(f"  ICs: {args.n_ic}, seed: {args.seed}, depth: {args.depth}")
    print(f"\n  Hypothesis: a₂ frozen (S97), all running in a₄.")
    print(f"  The n-dependence of spectral coefficients IS the coupling running.")

    rng = np.random.default_rng(args.seed)

    all_results = {name: [] for name, _, _ in TOPOLOGIES}

    for ic in range(args.n_ic):
        print(f"\n{'='*60}")
        print(f"  IC {ic+1}/{args.n_ic}")
        print(f"{'='*60}")

        psi_init = {v: haar_C3(rng) for v in range(6)}

        for name, seed_fn, density in TOPOLOGIES:
            result = process_topology(name, seed_fn, density, psi_init, args.depth)
            if result is not None:
                all_results[name].append(result)

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  SUMMARY: Spectral Action Running Across Scales")
    print(f"{'='*60}")

    print(f"\n  {'Topology':<20} {'ρ':>5} {'n':>4} {'D_F':>4} "
          f"{'a₂':>8} {'a₄':>10} {'grav%':>6} {'Hig%':>5} {'int%':>5} "
          f"{'Tr(D²)_raw':>10}")
    print(f"  {'─'*90}")

    summary = []
    for name, _, density in TOPOLOGIES:
        results = all_results[name]
        if not results:
            print(f"  {name:<20} — no results —")
            continue

        keys = ['a2_total','a4_total','a4_grav_frac','a4_higgs_frac',
                'a4_int_frac','gamma_orth','comm_rel','tr_df2_unscaled',
                'a2_L','a2_DF','alpha']
        m = {k: np.mean([r[k] for r in results]) for k in keys}
        s = {k: np.std([r[k] for r in results]) for k in keys}
        n_avg = int(np.mean([r['n'] for r in results]))
        df_avg = int(np.mean([r['dim_DF'] for r in results]))

        print(f"  {name:<20} {density:5.1%} {n_avg:4d} {df_avg:4d} "
              f"{m['a2_total']:8.1f} {m['a4_total']:10.0f} "
              f"{m['a4_grav_frac']:6.1%} {m['a4_higgs_frac']:5.1%} "
              f"{m['a4_int_frac']:5.1%} {m['tr_df2_unscaled']:10.6f}")

        summary.append({
            'name': name, 'density': density, 'n': n_avg, 'dim_DF': df_avg,
            **{f'{k}_mean': m[k] for k in keys},
            **{f'{k}_std': s[k] for k in keys},
            'n_ic': len(results),
        })

    # ═══════════════════════════════════════════════════════════════
    # RUNNING ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    if len(summary) >= 2:
        print(f"\n{'='*60}")
        print(f"  RUNNING ANALYSIS")
        print(f"{'='*60}")

        densities = np.array([r['density'] for r in summary])
        a4s = np.array([r['a4_total_mean'] for r in summary])
        a2s = np.array([r['a2_total_mean'] for r in summary])
        grav = np.array([r['a4_grav_frac_mean'] for r in summary])
        higgs = np.array([r['a4_higgs_frac_mean'] for r in summary])
        ints = np.array([r['a4_int_frac_mean'] for r in summary])
        trd2 = np.array([r['tr_df2_unscaled_mean'] for r in summary])

        # a₂ running check (S97)
        a2_cv = np.std(a2s)/np.mean(a2s) if np.mean(a2s) != 0 else 0
        print(f"\n  a₂ check (S97: should be frozen):")
        print(f"    values: {['%.1f' % x for x in a2s]}")
        print(f"    CV = {a2_cv:.4f} ({'FROZEN ✓' if a2_cv < 0.1 else 'RUNNING — see notes'})")

        print(f"\n  Tr(D_F²) raw (should be const per S97):")
        print(f"    values: {['%.6f' % x for x in trd2]}")

        # a₄ running
        print(f"\n  a₄ running (where couplings live):")
        print(f"    a₄ total: {['%.0f' % x for x in a4s]}")
        print(f"    gravity%: {['%.1f' % (100*x) for x in grav]}")
        print(f"    Higgs%:   {['%.1f' % (100*x) for x in higgs]}")
        print(f"    interact%:{['%.1f' % (100*x) for x in ints]}")

        # Normalized: a₄ per vertex² (removes trivial size scaling)
        ns = np.array([r['n'] for r in summary], dtype=float)
        a4_per_n2 = a4s / ns**2
        print(f"\n  a₄/n² (size-normalized):")
        print(f"    values: {['%.2f' % x for x in a4_per_n2]}")

        # a₄ gravity component running
        a4_grav = np.array([r['a4_grav_frac_mean'] * r['a4_total_mean'] for r in summary])
        a4_higgs_vals = np.array([r['a4_higgs_frac_mean'] * r['a4_total_mean'] for r in summary])
        a4_int_vals = np.array([r['a4_int_frac_mean'] * r['a4_total_mean'] for r in summary])

        print(f"\n  Absolute a₄ sectors:")
        print(f"    gravity: {['%.0f' % x for x in a4_grav]}")
        print(f"    Higgs:   {['%.2f' % x for x in a4_higgs_vals]}")
        print(f"    interact:{['%.0f' % x for x in a4_int_vals]}")

        # Fit: ln(a₄) vs ln(ρ) for power-law scaling
        if len(densities) >= 3:
            log_rho = np.log(densities)
            log_a4 = np.log(a4s)

            coeffs = np.polyfit(log_rho, log_a4, 1)
            fitted = np.polyval(coeffs, log_rho)
            rmse = np.sqrt(np.mean((log_a4 - fitted)**2))

            print(f"\n  Power-law fit: a₄ ∝ ρ^γ")
            print(f"    γ = {coeffs[0]:.3f}, RMSE(log) = {rmse:.4f}")

            # Fit fraction running
            for label, vals in [("gravity%", grav), ("Higgs%", higgs), ("interact%", ints)]:
                if np.std(vals) > 1e-6:
                    c = np.polyfit(log_rho, vals, 1)
                    print(f"    {label}: slope = {c[0]:.4f}/ln(ρ)")

        # β-function comparison
        print(f"\n  β-function structure:")
        print(f"    If a₄ = a₄(L⁴) + a₄(D_F⁴) + a₄(int), and gauge couplings")
        print(f"    live in a₄(int), then the interaction fraction running")
        print(f"    IS the discrete β-function for gauge-gravity coupling.")
        print(f"    Compare S124 mass gap running: m = 0.180→0.497 with ρ.")

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
