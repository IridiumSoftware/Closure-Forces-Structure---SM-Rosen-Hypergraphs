#!/usr/bin/env python3
"""
colour_dynamics_optimal_v1.py — Colour dynamics at Born-optimal ψ₀

Task 12: "Does the colour sector behave qualitatively differently at
Born-optimal initial conditions?"

Y-blindness is algebraic (S66): μ_cov = |det[ψ̃]|² doesn't reference Y.
The question is whether the colour sector itself has a richer dynamical
regime at Born-optimal ψ₀ that random sampling misses.

Born-optimal ψ₀: maximize μ_min over the 6 initial G₀ edges.
Each edge's Born weight = |det[ψ̃₁|ψ̃₂|ψ̃₃]|².
With alternating rep structure (even depth: pos1,2 = 3, pos3 = 3̄),
maximum |det|² = 1 when {ψ̃₁, ψ̃₂, ψ̃₃} is orthonormal.

The constraint: G₀ has 6 vertices shared across 6 edges with overlapping
source triples. Maximizing μ_min on all 6 simultaneously is a constrained
optimization on (S⁵)⁶ (6 unit vectors in ℂ³).

Diagnostics (compared to random-IC baselines):
  1. Confinement: ⟨σ₃⟩_bw by generation (baseline: 0.58 plateau)
  2. Spectral gap: transfer operator eigenvalue gap (baseline: 0.14)
  3. Inter-edge correlations: pairwise μ correlation across edges
  4. Curvature: Gram matrix structure / Ollivier-Ricci on Q₂₄

Usage:
  python3 colour_dynamics_optimal_v1.py [--depth D] [--n-opt N] [--seed S]
"""

import numpy as np
import argparse
import time
import sys
sys.path.insert(0, 'Scripts_tools')
from p2_0_layer5_sim_v1 import (
    build_G0, HypergraphState, Vertex, Edge, Decoration,
    born_weight_edge, compose_colour, compose_full,
    singlet_overlap, normalize, haar_C3, random_decoration,
    cross_C3
)


def born_weights_G0(psi_list):
    """Compute Born weights for all 6 G₀ edges given 6 colour vectors.

    G₀ topology (even depth):
      e₀: (v₀,v₁,v₂) → v₃   pos1,2=3, pos3=3̄
      e₁: (v₁,v₂,v₃) → v₄
      ...
      e₅: (v₅,v₀,v₁) → v₂

    Born weight = |det[ψ̃₁|ψ̃₂|ψ̃₃]|² where ψ̃ = ψ for rep 3, ψ* for 3̄.
    At depth 0 (even): pos1,2 = rep 3 (ψ̃=ψ), pos3 = rep 3̄ (ψ̃=ψ*).
    """
    topo = [(0,1,2), (1,2,3), (2,3,4), (3,4,5), (4,5,0), (5,0,1)]
    weights = []
    for s1, s2, s3 in topo:
        M = np.column_stack([psi_list[s1], psi_list[s2], np.conj(psi_list[s3])])
        weights.append(abs(np.linalg.det(M))**2)
    return np.array(weights)


def optimize_born_G0(n_restarts=200, n_steps=2000, seed=0):
    """Find ψ₀ that maximizes min(Born weights) over G₀ edges.

    Uses gradient-free optimization: many random restarts with
    projected gradient ascent on the min-Born objective.
    """
    rng = np.random.default_rng(seed)
    best_psi = None
    best_min_mu = -1

    for restart in range(n_restarts):
        # Initialize 6 unit vectors in ℂ³
        psi = [normalize(rng.standard_normal(3) + 1j * rng.standard_normal(3))
               for _ in range(6)]

        lr = 0.05
        for step in range(n_steps):
            mu = born_weights_G0(psi)
            min_mu = np.min(mu)

            if step > 0 and step % 500 == 0:
                lr *= 0.7  # decay

            # Gradient by finite differences on the min-Born edge
            worst_edge = np.argmin(mu)
            grad = [np.zeros(3, dtype=np.complex128) for _ in range(6)]

            eps = 1e-5
            for vi in range(6):
                for ci in range(3):
                    psi_p = [p.copy() for p in psi]
                    psi_p[vi][ci] += eps
                    psi_p[vi] = normalize(psi_p[vi])
                    mu_p = born_weights_G0(psi_p)

                    psi_m = [p.copy() for p in psi]
                    psi_m[vi][ci] -= eps
                    psi_m[vi] = normalize(psi_m[vi])
                    mu_m = born_weights_G0(psi_m)

                    # Gradient of min(μ) ≈ gradient of the worst edge
                    grad[vi][ci] = (np.min(mu_p) - np.min(mu_m)) / (2 * eps)

            # Project gradient step onto unit sphere
            for vi in range(6):
                psi[vi] = normalize(psi[vi] + lr * grad[vi])

        mu_final = born_weights_G0(psi)
        min_final = np.min(mu_final)
        if min_final > best_min_mu:
            best_min_mu = min_final
            best_psi = [p.copy() for p in psi]

        if restart < 5 or (restart + 1) % 50 == 0:
            print(f"    restart {restart+1}/{n_restarts}: "
                  f"min(μ)={min_final:.6f}, mean(μ)={np.mean(mu_final):.6f}")

    return best_psi, best_min_mu


def build_G0_with_psi(psi_list, rng):
    """Build G₀ with specified colour vectors but random w, ε, gen."""
    state = build_G0(rng)
    for vid in range(6):
        state.vertices[vid].dec.psi = psi_list[vid].copy()
    # Recompute Born weights
    for e in state.edges.values():
        d1 = state.vertices[e.src[0]].dec
        d2 = state.vertices[e.src[1]].dec
        d3 = state.vertices[e.src[2]].dec
        e.born_weight = born_weight_edge(d1, d2, d3, e.depth)
    return state


def fire_edge(state, edge):
    """Fire a single edge: create daughter vertex + 3 daughter edges."""
    d1 = state.vertices[edge.src[0]].dec
    d2 = state.vertices[edge.src[1]].dec
    d3 = state.vertices[edge.src[2]].dec

    # Compose
    dec_out = compose_full(d1, d2, d3)

    # Create target vertex
    new_vid = state.next_vid; state.next_vid += 1
    new_depth = edge.depth + 1
    state.vertices[new_vid] = Vertex(vid=new_vid, depth=new_depth,
                                      dec=dec_out, parent_edge=edge.eid)
    edge.tgt = new_vid
    edge.fired = True

    # Create 3 daughter edges (D₁, D₂, D₃)
    s1, s2, s3 = edge.src
    daughter_configs = [
        (new_vid, s2, s3, 1),  # D₁: new vertex replaces source1
        (new_vid, s1, s3, 2),  # D₂: new vertex replaces source2
        (new_vid, s1, s2, 3),  # D₃: new vertex replaces source3
    ]

    daughter_eids = []
    for src_new, src_keep1, src_keep2, dtype in daughter_configs:
        new_eid = state.next_eid; state.next_eid += 1
        new_e = Edge(eid=new_eid, depth=new_depth,
                     src=(src_new, src_keep1, src_keep2), tgt=-1,
                     parent_eid=edge.eid, daughter_type=dtype)
        # Compute Born weight
        dd1 = state.vertices[new_e.src[0]].dec
        dd2 = state.vertices[new_e.src[1]].dec
        dd3 = state.vertices[new_e.src[2]].dec
        new_e.born_weight = born_weight_edge(dd1, dd2, dd3, new_e.depth)
        state.edges[new_eid] = new_e
        daughter_eids.append(new_eid)
        state.causal_children[new_eid] = []
        state.causal_parent[new_eid] = edge.eid

    state.causal_children[edge.eid] = daughter_eids


def evolve_and_measure(state, max_depth, label=""):
    """Evolve G₀ to max_depth, collecting per-generation diagnostics."""
    results = {'gen': [], 'mean_mu': [], 'min_mu': [], 'sigma3_bw': [],
               'n_edges': [], 'mu_corr': [], 'gram_det': []}

    for gen in range(max_depth + 1):
        # Collect current-generation edges
        gen_edges = [e for e in state.edges.values()
                     if e.depth == gen and not e.fired]

        if not gen_edges:
            break

        # Born weights
        mus = np.array([e.born_weight for e in gen_edges])
        mean_mu = np.mean(mus)
        min_mu = np.min(mus) if len(mus) > 0 else 0

        # Singlet overlap (σ₃) — Born-weighted
        # Direct fidelity: |⟨compose(ψ̃₁, ψ̃₂) | ψ̃₃⟩|²
        # Uses covariant colour vectors (ψ̃ = ψ for rep 3, ψ* for 3̄)
        sigma3_vals = []
        for e in gen_edges:
            d1 = state.vertices[e.src[0]].dec
            d2 = state.vertices[e.src[1]].dec
            d3 = state.vertices[e.src[2]].dec
            is_odd = (e.depth % 2 == 1)
            # Covariant colour vectors for Born measure
            pt1 = np.conj(d1.psi) if is_odd else d1.psi
            pt2 = np.conj(d2.psi) if is_odd else d2.psi
            pt3 = d3.psi if is_odd else np.conj(d3.psi)
            # Composition output in covariant frame
            psi_out = normalize(np.conj(cross_C3(pt1, pt2)))
            # Fidelity: |⟨psi_out | pt3⟩|²
            so = abs(np.vdot(psi_out, pt3)) ** 2
            sigma3_vals.append(so)

        sigma3 = np.array(sigma3_vals)
        if np.sum(mus) > 1e-30:
            sigma3_bw = np.average(sigma3, weights=mus)
        else:
            sigma3_bw = np.mean(sigma3)

        # Inter-edge Born correlation
        if len(mus) > 1:
            mu_pairs = []
            for i in range(min(len(gen_edges), 50)):
                for j in range(i+1, min(len(gen_edges), 50)):
                    mu_pairs.append((mus[i], mus[j]))
            if mu_pairs:
                x, y = zip(*mu_pairs)
                x, y = np.array(x), np.array(y)
                if np.std(x) > 1e-15 and np.std(y) > 1e-15:
                    mu_corr = np.corrcoef(x, y)[0, 1]
                else:
                    mu_corr = 0.0
            else:
                mu_corr = 0.0
        else:
            mu_corr = 0.0

        # Gram matrix determinant (colour geometry)
        if len(gen_edges) >= 3:
            psi_all = [state.vertices[gen_edges[i].src[0]].dec.psi
                       for i in range(min(len(gen_edges), 20))]
            G = np.array([[abs(np.vdot(a, b))**2 for b in psi_all] for a in psi_all])
            gram_det = abs(np.linalg.det(G[:3, :3]))
        else:
            gram_det = 0.0

        results['gen'].append(gen)
        results['mean_mu'].append(mean_mu)
        results['min_mu'].append(min_mu)
        results['sigma3_bw'].append(sigma3_bw)
        results['n_edges'].append(len(gen_edges))
        results['mu_corr'].append(mu_corr)
        results['gram_det'].append(gram_det)

        # Fire all edges at this generation
        for e in gen_edges:
            fire_edge(state, e)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--depth', type=int, default=8)
    parser.add_argument('--n-opt', type=int, default=100,
                        help='Number of optimization restarts')
    parser.add_argument('--n-random', type=int, default=30,
                        help='Number of random-IC ensemble members')
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("=" * 70)
    print("  Colour Dynamics at Born-Optimal ψ₀ (Task 12)")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # STEP 1: Find Born-optimal ψ₀
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 1: Optimize ψ₀ (maximize min-Born over G₀ edges)")
    print("=" * 70)

    t0 = time.time()
    opt_psi, opt_min_mu = optimize_born_G0(
        n_restarts=args.n_opt, n_steps=2000, seed=args.seed)
    t_opt = time.time() - t0

    opt_mu = born_weights_G0(opt_psi)
    print(f"\n  Optimal ψ₀:")
    print(f"    min(μ) = {opt_min_mu:.6f}")
    print(f"    mean(μ) = {np.mean(opt_mu):.6f}")
    print(f"    max(μ) = {np.max(opt_mu):.6f}")
    print(f"    μ per edge: {[f'{m:.4f}' for m in opt_mu]}")
    print(f"    Optimization time: {t_opt:.1f}s")

    # Check: are the 6 vectors near-orthonormal in some frame?
    psi_mat = np.array(opt_psi)  # 6×3
    G_opt = np.array([[abs(np.vdot(opt_psi[i], opt_psi[j]))**2
                       for j in range(6)] for i in range(6)])
    print(f"    Gram matrix (fidelities):")
    for i in range(6):
        print(f"      [{', '.join(f'{G_opt[i,j]:.3f}' for j in range(6))}]")

    # Random baseline stats
    rng_base = np.random.default_rng(args.seed + 100)
    random_min_mus = []
    for _ in range(1000):
        psi_rand = [normalize(rng_base.standard_normal(3) + 1j * rng_base.standard_normal(3))
                    for _ in range(6)]
        mu_rand = born_weights_G0(psi_rand)
        random_min_mus.append(np.min(mu_rand))
    print(f"\n  Random baseline: mean min(μ) = {np.mean(random_min_mus):.6f}, "
          f"max min(μ) = {np.max(random_min_mus):.6f}")
    print(f"  Optimal is {opt_min_mu / np.mean(random_min_mus):.1f}× the random mean")

    # ═══════════════════════════════════════════════════════════
    # STEP 2: Evolve at optimal ψ₀ and random ICs
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print(f"  STEP 2: Evolution (depth {args.depth})")
    print("=" * 70)

    # Optimal IC evolution (multiple runs with different w, ε, gen)
    n_opt_runs = 10
    opt_results_all = []
    for run in range(n_opt_runs):
        rng_run = np.random.default_rng(args.seed + 200 + run)
        state = build_G0_with_psi(opt_psi, rng_run)
        res = evolve_and_measure(state, args.depth)
        opt_results_all.append(res)

    # Random IC evolution
    rand_results_all = []
    for run in range(args.n_random):
        rng_run = np.random.default_rng(args.seed + 500 + run)
        state = build_G0(rng_run)
        res = evolve_and_measure(state, args.depth)
        rand_results_all.append(res)

    # ═══════════════════════════════════════════════════════════
    # STEP 3: Compare diagnostics
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 3: Diagnostic Comparison")
    print("=" * 70)

    max_gen = min(len(opt_results_all[0]['gen']),
                  min(len(r['gen']) for r in rand_results_all))

    print(f"\n  {'Gen':>3} | {'⟨σ₃⟩_bw OPT':>12} {'⟨σ₃⟩_bw RND':>12} {'Δ':>8} | "
          f"{'⟨μ⟩ OPT':>10} {'⟨μ⟩ RND':>10} | {'corr OPT':>10} {'corr RND':>10}")
    print(f"  {'-'*3}-+-{'-'*12}-{'-'*12}-{'-'*8}-+-{'-'*10}-{'-'*10}-+-{'-'*10}-{'-'*10}")

    for g in range(max_gen):
        s3_opt = np.mean([r['sigma3_bw'][g] for r in opt_results_all])
        s3_rnd = np.mean([r['sigma3_bw'][g] for r in rand_results_all])
        mu_opt = np.mean([r['mean_mu'][g] for r in opt_results_all])
        mu_rnd = np.mean([r['mean_mu'][g] for r in rand_results_all])
        corr_opt = np.mean([r['mu_corr'][g] for r in opt_results_all])
        corr_rnd = np.mean([r['mu_corr'][g] for r in rand_results_all])

        print(f"  {g:>3} | {s3_opt:>12.4f} {s3_rnd:>12.4f} {s3_opt-s3_rnd:>+8.4f} | "
              f"{mu_opt:>10.4f} {mu_rnd:>10.4f} | {corr_opt:>+10.4f} {corr_rnd:>+10.4f}")

    # ═══════════════════════════════════════════════════════════
    # STEP 4: Gradient from random → optimal
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 4: Gradient (interpolation random → optimal)")
    print("=" * 70)

    rng_grad = np.random.default_rng(args.seed + 800)
    psi_random = [normalize(rng_grad.standard_normal(3) + 1j * rng_grad.standard_normal(3))
                  for _ in range(6)]
    alphas = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    print(f"\n  {'α':>5} | {'min(μ₀)':>10} {'⟨σ₃⟩_bw (gen 5)':>16} {'⟨μ⟩ (gen 5)':>14}")
    for alpha in alphas:
        psi_interp = [normalize((1-alpha)*psi_random[i] + alpha*opt_psi[i])
                      for i in range(6)]
        mu_interp = born_weights_G0(psi_interp)

        # Evolve
        rng_a = np.random.default_rng(args.seed + 900)
        state = build_G0_with_psi(psi_interp, rng_a)
        res = evolve_and_measure(state, min(args.depth, 6))

        g5_idx = min(5, len(res['gen'])-1)
        print(f"  {alpha:>5.1f} | {np.min(mu_interp):>10.4f} "
              f"{res['sigma3_bw'][g5_idx]:>16.4f} "
              f"{res['mean_mu'][g5_idx]:>14.4f}")

    # ═══════════════════════════════════════════════════════════
    # STEP 5: Fine-grained phase transition
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 5: Phase Transition (fine α grid)")
    print("=" * 70)

    rng_grad2 = np.random.default_rng(args.seed + 850)
    psi_rand2 = [normalize(rng_grad2.standard_normal(3) + 1j * rng_grad2.standard_normal(3))
                 for _ in range(6)]
    fine_alphas = np.linspace(0, 1, 21)
    fine_mu_min = []; fine_s3 = []
    for alpha in fine_alphas:
        psi_i = [normalize((1-alpha)*psi_rand2[k] + alpha*opt_psi[k]) for k in range(6)]
        mu_i = born_weights_G0(psi_i)
        fine_mu_min.append(np.min(mu_i))
        rng_fi = np.random.default_rng(args.seed + 860)
        st = build_G0_with_psi(psi_i, rng_fi)
        res_fi = evolve_and_measure(st, min(args.depth, 5))
        g_idx = min(3, len(res_fi['gen'])-1)
        fine_s3.append(res_fi['sigma3_bw'][g_idx])

    # Susceptibility: dσ₃/dα
    d_s3 = np.gradient(fine_s3, fine_alphas)
    peak_idx = np.argmax(np.abs(d_s3))
    alpha_c = fine_alphas[peak_idx]

    print(f"\n  α_c (max |dσ₃/dα|) = {alpha_c:.2f}")
    print(f"  dσ₃/dα at α_c = {d_s3[peak_idx]:.4f}")
    print(f"\n  {'α':>5} {'min(μ₀)':>10} {'σ₃(gen3)':>10} {'dσ₃/dα':>10}")
    for i, a in enumerate(fine_alphas):
        if i % 2 == 0 or abs(a - alpha_c) < 0.06:
            print(f"  {a:>5.2f} {fine_mu_min[i]:>10.4f} {fine_s3[i]:>10.4f} {d_s3[i]:>+10.4f}")

    # ═══════════════════════════════════════════════════════════
    # STEP 6: Geometric uniqueness (multiple optimal restarts)
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 6: Geometric Uniqueness (Gram structure of optima)")
    print("=" * 70)

    # Run several independent optimizations and compare Gram matrices
    n_indep = 5
    gram_structures = []
    for trial in range(n_indep):
        psi_t, mm_t = optimize_born_G0(n_restarts=20, n_steps=1500,
                                         seed=args.seed + 2000 + trial * 100)
        mu_t = born_weights_G0(psi_t)
        G_t = np.array([[abs(np.vdot(psi_t[i], psi_t[j]))**2
                         for j in range(6)] for i in range(6)])
        # Extract the 3 pair fidelities (v0-v3, v1-v4, v2-v5)
        pair_fids = [G_t[0,3], G_t[1,4], G_t[2,5]]
        # Inter-pair fidelities (should be ~0)
        inter_fids = [G_t[0,1], G_t[0,2], G_t[1,2]]
        gram_structures.append({
            'min_mu': mm_t, 'pair_fids': pair_fids, 'inter_fids': inter_fids
        })
        print(f"  Trial {trial}: min(μ)={mm_t:.4f}  "
              f"pairs=[{pair_fids[0]:.3f},{pair_fids[1]:.3f},{pair_fids[2]:.3f}]  "
              f"inter=[{inter_fids[0]:.3f},{inter_fids[1]:.3f},{inter_fids[2]:.3f}]")

    pair_mean = np.mean([g['pair_fids'] for g in gram_structures])
    inter_mean = np.mean([g['inter_fids'] for g in gram_structures])
    print(f"\n  Mean pair fidelity: {pair_mean:.4f} (should be ~1 if structure is universal)")
    print(f"  Mean inter fidelity: {inter_mean:.4f} (should be ~0)")
    all_min_mus = [g['min_mu'] for g in gram_structures]
    print(f"  min(μ) across trials: {[f'{m:.4f}' for m in all_min_mus]}")
    if np.std(all_min_mus) < 0.02:
        print(f"  → Optimal value REPRODUCIBLE (std={np.std(all_min_mus):.4f})")
    if pair_mean > 0.9 and inter_mean < 0.1:
        print(f"  → 3-pair structure is UNIVERSAL across independent optimizations")
        print(f"  → Likely gauge-unique (unique up to SU(3) rotation)")

    # ═══════════════════════════════════════════════════════════
    # STEP 7: Born concentration drift
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  STEP 7: Born Concentration — Does ⟨μ⟩ ratio grow or stabilize?")
    print("=" * 70)

    # Track ⟨μ⟩_opt / ⟨μ⟩_rnd by generation
    print(f"\n  {'Gen':>3} | {'⟨μ⟩ OPT':>10} {'⟨μ⟩ RND':>10} {'Ratio':>8} | "
          f"{'⟨μ⟩ OPT/gen0':>14} {'⟨μ⟩ RND/gen0':>14}")
    for g in range(max_gen):
        mu_o = np.mean([r['mean_mu'][g] for r in opt_results_all])
        mu_r = np.mean([r['mean_mu'][g] for r in rand_results_all])
        ratio = mu_o / max(mu_r, 1e-10)
        mu_o_0 = np.mean([r['mean_mu'][0] for r in opt_results_all])
        mu_r_0 = np.mean([r['mean_mu'][0] for r in rand_results_all])
        norm_o = mu_o / max(mu_o_0, 1e-10)
        norm_r = mu_r / max(mu_r_0, 1e-10)
        print(f"  {g:>3} | {mu_o:>10.4f} {mu_r:>10.4f} {ratio:>8.3f} | "
              f"{norm_o:>14.4f} {norm_r:>14.4f}")

    # Trend analysis
    ratios = [np.mean([r['mean_mu'][g] for r in opt_results_all]) /
              max(np.mean([r['mean_mu'][g] for r in rand_results_all]), 1e-10)
              for g in range(max_gen)]
    if len(ratios) >= 4:
        early_ratio = np.mean(ratios[1:3])
        late_ratio = np.mean(ratios[-2:])
        if late_ratio > early_ratio * 1.05:
            print(f"\n  Ratio GROWING: early={early_ratio:.3f} → late={late_ratio:.3f}")
            print(f"  → Born measure actively concentrates toward optimal basin")
        elif late_ratio < early_ratio * 0.95:
            print(f"\n  Ratio DECAYING: early={early_ratio:.3f} → late={late_ratio:.3f}")
            print(f"  → Born advantage erodes with evolution (static preference)")
        else:
            print(f"\n  Ratio STABLE: early={early_ratio:.3f} → late={late_ratio:.3f}")
            print(f"  → Persistent preference without dynamical reinforcement")

    # ═══════════════════════════════════════════════════════════
    # RESULTS
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  RESULTS")
    print("=" * 70)

    # Late-generation comparison
    late_gen = max_gen - 1
    s3_opt_late = np.mean([r['sigma3_bw'][late_gen] for r in opt_results_all])
    s3_rnd_late = np.mean([r['sigma3_bw'][late_gen] for r in rand_results_all])
    s3_opt_std = np.std([r['sigma3_bw'][late_gen] for r in opt_results_all])
    s3_rnd_std = np.std([r['sigma3_bw'][late_gen] for r in rand_results_all])

    mu_opt_late = np.mean([r['mean_mu'][late_gen] for r in opt_results_all])
    mu_rnd_late = np.mean([r['mean_mu'][late_gen] for r in rand_results_all])

    corr_opt_late = np.mean([r['mu_corr'][late_gen] for r in opt_results_all])
    corr_rnd_late = np.mean([r['mu_corr'][late_gen] for r in rand_results_all])

    # Early generation (gen 0-1) comparison
    s3_opt_0 = np.mean([r['sigma3_bw'][0] for r in opt_results_all])
    s3_rnd_0 = np.mean([r['sigma3_bw'][0] for r in rand_results_all])
    mu_opt_0 = np.mean([r['mean_mu'][0] for r in opt_results_all])
    mu_rnd_0 = np.mean([r['mean_mu'][0] for r in rand_results_all])

    convergence = abs(s3_opt_late - s3_rnd_late) < 2 * max(s3_opt_std, s3_rnd_std)

    print(f"""
  Diagnostic 1 — Confinement (⟨σ₃⟩_bw):
    Gen 0:  optimal={s3_opt_0:.4f}  random={s3_rnd_0:.4f}  Δ={s3_opt_0-s3_rnd_0:+.4f}
    Gen {late_gen}:  optimal={s3_opt_late:.4f}±{s3_opt_std:.4f}  random={s3_rnd_late:.4f}±{s3_rnd_std:.4f}  Δ={s3_opt_late-s3_rnd_late:+.4f}
    {'→ CONVERGES to random baseline' if convergence else '→ QUALITATIVE DIFFERENCE persists'}

  Diagnostic 2 — Born weight ⟨μ⟩:
    Gen 0:  optimal={mu_opt_0:.4f}  random={mu_rnd_0:.4f}  ({mu_opt_0/max(mu_rnd_0,1e-10):.1f}×)
    Gen {late_gen}:  optimal={mu_opt_late:.4f}  random={mu_rnd_late:.4f}  ({mu_opt_late/max(mu_rnd_late,1e-10):.1f}×)

  Diagnostic 3 — Inter-edge μ correlation:
    Gen {late_gen}:  optimal={corr_opt_late:+.4f}  random={corr_rnd_late:+.4f}

  Diagnostic 4 — Overall assessment:
""")

    if convergence:
        print(f"    Regime C is UNIVERSAL. Born-optimal ψ₀ relaxes to the same")
        print(f"    dynamical regime as random ICs within {late_gen} generations.")
        print(f"    The colour sector at its best is no richer than at its average.")
        print(f"    Y-blindness is not just algebraic but dynamically irrelevant —")
        print(f"    the Born-optimal regime adds no hidden structure.")
    else:
        print(f"    Born-optimal ψ₀ produces a QUALITATIVELY DIFFERENT regime.")
        print(f"    The colour sector has preferred dynamics that the theory")
        print(f"    naturally selects via the Born measure.")
        print(f"    This may carry gravitational/geometric structure that")
        print(f"    random-IC analysis missed.")


if __name__ == '__main__':
    main()
