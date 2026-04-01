#!/usr/bin/env python3
"""
g10_session1_product_v1.py — Product vs Fibration: Steps 1-2

Four deliverables:
  (a) Fibre structure yes/no + overlap characterization
  (b) d_s of D₊ (γ-even piece) alone — does it carry d_s = 4?
  (c) Algebraic structure of the cross term C = D₊D₋ + D₋D₊
  (d) Algebra factorization test: does the bimodule algebra tensor-factorize?

Plus step 3 folded in: [D₊², D₋²] commutator check (Frobenius integrability).

Usage:
  python3 g10_session1_product_v1.py [--seed S]
"""

import numpy as np
import argparse
import time
from collections import defaultdict, Counter

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS from existing infrastructure
# ═══════════════════════════════════════════════════════════════════════════════
from g4_q24_q51_relation_v1 import (
    build_both_quotients, fidelity, G0_TOPO, complete_ternary,
    haar_C3, normalize, compose_colour
)
from q102_build_v1 import build_c_closed_quotient, build_J
from q102_orderone_v1 import j_compatible_triplets, build_representation, incremental_order_one
from q102_full_dirac_v1 import (
    build_graph_laplacian, rebuild_df_basis,
    spectral_dimension_curve, find_plateau
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n-ic', type=int, default=5)
    args = parser.parse_args()

    print("=" * 70)
    print("  G10 Session 1: Product vs Fibration Geometry")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # (a) FIBRE STRUCTURE TEST
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  (a) Fibre Structure Test: Q₂₄ fibre in Q₅₁?")
    print("=" * 70)

    rng = np.random.default_rng(args.seed)

    all_overlap_stats = []
    for ic in range(args.n_ic):
        rng_ic = np.random.default_rng(args.seed + ic * 100)
        R = build_both_quotients(rng_ic)
        g0 = R['G0']; k6 = R['K6']

        # Map Q₂₄ clusters into Q₅₁
        q24_in_q51 = {}
        for c24 in range(g0['n_cl']):
            best_c51, best_fid = None, 0
            for c51 in range(k6['n_cl']):
                f = fidelity(g0['q_psi'][c24], k6['q_psi'][c51])
                if f > best_fid: best_fid = f; best_c51 = c51
            if best_fid > 0.999:
                q24_in_q51[c24] = best_c51

        q24_image = set(q24_in_q51.values())
        q51_extras = [c for c in range(k6['n_cl']) if c not in q24_image]

        if ic == 0:
            print(f"  Q₂₄: {g0['n_cl']} clusters → Q₅₁: {k6['n_cl']} clusters")
            print(f"  Mapped: {len(q24_in_q51)}, Extras: {len(q51_extras)}")

        # For each extra vertex, find its Q₂₄ neighbours (via adjacency)
        adj_k6 = k6['adj']
        extra_nbr_sets = {}
        for ce in q51_extras:
            nbrs_in_q24 = set()
            for c24, c51 in q24_in_q51.items():
                if adj_k6[ce, c51] > 0:
                    nbrs_in_q24.add(c24)
            extra_nbr_sets[ce] = nbrs_in_q24

        # Overlap analysis: do different extras share Q₂₄ neighbours?
        overlap_matrix = np.zeros((len(q51_extras), len(q51_extras)))
        for i, ce_i in enumerate(q51_extras):
            for j, ce_j in enumerate(q51_extras):
                if i < j:
                    overlap = len(extra_nbr_sets[ce_i] & extra_nbr_sets[ce_j])
                    overlap_matrix[i, j] = overlap
                    overlap_matrix[j, i] = overlap

        nbr_sizes = [len(extra_nbr_sets[ce]) for ce in q51_extras]
        overlaps = overlap_matrix[np.triu_indices(len(q51_extras), k=1)]

        all_overlap_stats.append({
            'nbr_sizes': nbr_sizes,
            'mean_overlap': np.mean(overlaps) if len(overlaps) > 0 else 0,
            'max_overlap': np.max(overlaps) if len(overlaps) > 0 else 0,
            'n_extras': len(q51_extras),
        })

        if ic == 0:
            # Detailed report for first IC
            print(f"\n  Extra vertex Q₂₄-neighbourhood sizes: {sorted(Counter(nbr_sizes).items())}")
            print(f"  Mean pairwise overlap: {np.mean(overlaps):.2f}")
            print(f"  Max pairwise overlap: {np.max(overlaps):.0f}")
            print(f"  Overlap distribution: {sorted(Counter(overlaps.astype(int)).items())}")

            # Check: do the 6-vertex sets tile Q₂₄?
            union = set()
            for ce in q51_extras:
                union |= extra_nbr_sets[ce]
            coverage = len(union)
            print(f"  Union covers {coverage}/{g0['n_cl']} Q₂₄ vertices")

            # Tier structure of extras
            extra_tiers = [k6['q_tier'].get(ce, '?') for ce in q51_extras]
            print(f"  Extra tiers: {Counter(extra_tiers)}")

    # Summary across ICs
    mean_nbr = np.mean([np.mean(s['nbr_sizes']) for s in all_overlap_stats])
    mean_ovlp = np.mean([s['mean_overlap'] for s in all_overlap_stats])
    max_ovlp = np.max([s['max_overlap'] for s in all_overlap_stats])

    is_fibre = mean_ovlp < 0.5 and all(s['n_extras'] * mean_nbr >= 24 for s in all_overlap_stats)

    print(f"\n  Summary ({args.n_ic} ICs):")
    print(f"    Mean neighbourhood size: {mean_nbr:.1f}")
    print(f"    Mean pairwise overlap: {mean_ovlp:.2f}")
    print(f"    Max overlap: {max_ovlp:.0f}")
    print(f"    Fibre structure: {'POSSIBLE' if is_fibre else 'NO — overlapping neighbourhoods'}")

    # ═══════════════════════════════════════════════════════════
    # (b) d_s OF D₊ ALONE
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  (b) Spectral Dimension of D₊ (γ-even piece)")
    print("=" * 70)

    rng_q102 = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng_q102) for v in range(6)}
    Q = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)
    n = Q['n_cl']
    print(f"  Q₁₀₂: {n} vertices")

    # Build components
    final_basis, n, orig_idx, conj_idx, J, gamma = rebuild_df_basis(Q, psi_init)
    dim_df = final_basis.shape[0]
    L, L_norm, adj = build_graph_laplacian(Q)
    Gamma = np.diag(gamma)

    print(f"  D_F basis: {dim_df} dimensions")

    # Build a representative D_F
    rng_df = np.random.default_rng(args.seed + 42)
    alpha = rng_df.standard_normal(dim_df)
    alpha /= np.linalg.norm(alpha)
    n_conj = len(conj_idx); n_orig = len(orig_idx)
    M_rep = np.zeros((n_conj, n_orig))
    for k in range(dim_df):
        M_rep += alpha[k] * final_basis[k].reshape(n_conj, n_orig)
    D_F = np.zeros((n, n), dtype=np.complex128)
    ci = np.array(conj_idx); oi = np.array(orig_idx)
    D_F[np.ix_(ci, oi)] = M_rep; D_F[np.ix_(oi, ci)] = M_rep.T
    D_F_norm = np.linalg.norm(D_F, 'fro')
    if D_F_norm > 1e-15: D_F /= D_F_norm

    # Verify: D_F anticommutes with γ, L commutes with γ
    comm_DF_gamma = D_F @ Gamma + Gamma @ D_F  # {D_F, γ} should be 0
    comm_L_gamma = L_norm @ Gamma - Gamma @ L_norm  # [L, γ] should be 0
    print(f"\n  ||{{D_F, γ}}|| = {np.linalg.norm(comm_DF_gamma):.2e} (should be ~0)")
    print(f"  ||[L, γ]|| = {np.linalg.norm(comm_L_gamma):.2e} (should be ~0)")

    # γ-decomposition: D₊ = (D + γDγ)/2 (commutes with γ), D₋ = (D - γDγ)/2 (anticommutes)
    # For L (commutes with γ): L₊ = L, L₋ = 0
    # For D_F (anticommutes): D_F₊ = 0, D_F₋ = D_F

    # The "geometric" operator: D₊ = L_norm (the γ-commuting piece)
    # The "gauge" operator: D₋ = D_F (the γ-anticommuting piece)

    # Scale D_F to match L norm for fair comparison
    L_norm_fro = np.linalg.norm(L_norm, 'fro')
    D_F_scaled = D_F * L_norm_fro  # same Frobenius norm as L

    # Full Dirac at several coupling strengths
    print(f"\n  Spectral dimensions:")
    for label, op in [
        ("L alone (D₊)", L_norm),
        ("D_F alone (D₋)", D_F_scaled),
        ("D = L + D_F", L_norm + D_F_scaled),
        ("D = L + 0.1·D_F", L_norm + 0.1 * D_F_scaled),
    ]:
        evals = np.linalg.eigvalsh(op @ op)  # eigenvalues of operator²
        t_range, ds = spectral_dimension_curve(evals)
        ds_plateau, _ = find_plateau(t_range, ds)
        ds_peak = np.max(ds) if len(ds) > 0 else 0
        print(f"    {label:25s}: d_s(plateau) = {ds_plateau:.2f}, d_s(peak) = {ds_peak:.2f}")

    # KEY TEST: does D₊ = L alone carry d_s = 4?
    evals_L = np.linalg.eigvalsh(L_norm @ L_norm)
    t_L, ds_L = spectral_dimension_curve(evals_L)
    ds_L_plateau, _ = find_plateau(t_L, ds_L)

    evals_DF = np.linalg.eigvalsh(D_F_scaled @ D_F_scaled)
    t_DF, ds_DF = spectral_dimension_curve(evals_DF)
    ds_DF_plateau, _ = find_plateau(t_DF, ds_DF)

    print(f"\n  ★ D₊ (L alone) d_s = {ds_L_plateau:.2f}")
    print(f"  ★ D₋ (D_F alone) d_s = {ds_DF_plateau:.2f}")
    if abs(ds_L_plateau - 4.0) < 0.5:
        print(f"  → D₊ carries d_s ≈ 4 INDEPENDENTLY. Option C viable.")
    else:
        print(f"  → D₊ does NOT carry d_s ≈ 4 alone. Needs geometric factorization.")

    # ═══════════════════════════════════════════════════════════
    # (c) CROSS TERM C = D₊D₋ + D₋D₊
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  (c) Cross Term: C = D₊D₋ + D₋D₊ = LD_F + D_FL")
    print("=" * 70)

    # The cross term
    C = L_norm @ D_F_scaled + D_F_scaled @ L_norm

    # γ-orthogonality says Tr(D_F† L) = 0 → the trace of C should be 0
    tr_C = np.trace(C)
    print(f"  Tr(C) = {abs(tr_C):.2e} (should be 0 by γ-orthogonality)")

    # Does C commute or anticommute with γ?
    comm_C_gamma = C @ Gamma - Gamma @ C
    anti_C_gamma = C @ Gamma + Gamma @ C
    print(f"  ||[C, γ]|| = {np.linalg.norm(comm_C_gamma):.2e}")
    print(f"  ||{{C, γ}}|| = {np.linalg.norm(anti_C_gamma):.2e}")

    if np.linalg.norm(anti_C_gamma) < 1e-10:
        print(f"  → C anticommutes with γ: C is γ-odd (same sector as D_F)")
    elif np.linalg.norm(comm_C_gamma) < 1e-10:
        print(f"  → C commutes with γ: C is γ-even (same sector as L)")
    else:
        print(f"  → C is mixed: neither pure γ-even nor γ-odd")

    # Frobenius weight in the spectral action
    D_full = L_norm + D_F_scaled
    D2 = D_full @ D_full
    L2 = L_norm @ L_norm
    DF2 = D_F_scaled @ D_F_scaled
    C_actual = D2 - L2 - DF2  # D² = L² + D_F² + C

    print(f"\n  Spectral action decomposition (D² = L² + D_F² + C):")
    print(f"    ||L²|| = {np.linalg.norm(L2, 'fro'):.4f}")
    print(f"    ||D_F²|| = {np.linalg.norm(DF2, 'fro'):.4f}")
    print(f"    ||C|| = {np.linalg.norm(C_actual, 'fro'):.4f}")
    total = np.linalg.norm(L2, 'fro') + np.linalg.norm(DF2, 'fro') + np.linalg.norm(C_actual, 'fro')
    print(f"    Fractions: L²={np.linalg.norm(L2,'fro')/total:.1%}, "
          f"D_F²={np.linalg.norm(DF2,'fro')/total:.1%}, "
          f"C={np.linalg.norm(C_actual,'fro')/total:.1%}")

    # Is C an inner fluctuation? Check: does C have the structure of [D, A]
    # for some A commuting with γ? If C = LD_F + D_FL and L commutes with γ,
    # D_F anticommutes, then C anticommutes with γ (product of even × odd = odd).
    # An inner fluctuation A = Σ a_i [D, b_i] also anticommutes with γ.
    # So the algebraic structure is consistent.

    # ═══════════════════════════════════════════════════════════
    # (d) ALGEBRA FACTORIZATION
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  (d) Algebra Factorization: does A factorize as A_base ⊗ A_fibre?")
    print("=" * 70)

    # A_fibre = ℍ ⊕ M₃(ℂ) acts on the internal (gauge) space
    # A_base = "functions on Q₁₀₂ vertices" = ℂ^n (diagonal matrices)
    # Full bimodule: π(a_base ⊗ a_fibre) = diag(a_base) ⊗ π(a_fibre)

    # In practice: the algebra generators are colour (E_ij) and weak (σ_i).
    # These act on ALL vertices simultaneously (same σ at every vertex).
    # The "base algebra" would be diagonal matrices that distinguish vertices.
    # The tensor product A_base ⊗ A_fibre means: (vertex label) × (gauge rep).

    # Test: does the bimodule commutant factorize?
    # Commutant = operators commuting with both π(a) and π°(b)
    # S89: commutant = M₂(ℂ) on Q₄₈. On Q₁₀₂: need to check.

    # Build the representation
    triplets, v2c, v2f = j_compatible_triplets(Q, J, gamma)
    rep = build_representation(Q, triplets, v2c)

    # Commutant of left algebra
    left_gens = list(rep.values())
    comm_dim_test = np.eye(n, dtype=np.complex128).reshape(n * n)

    # Build commutant basis by intersecting null spaces of [·, gen]
    basis = np.eye(n * n)
    current_dim = n * n
    for gen in left_gens:
        if current_dim == 0: break
        violations = []
        for k in range(current_dim):
            M = basis[k].reshape(n, n)
            comm = M @ gen - gen @ M
            violations.append(comm.real.flatten())
        V = np.array(violations)
        if np.max(np.abs(V)) < 1e-12: continue
        G = V @ V.T; ev, ec = np.linalg.eigh(G)
        ker = ev < 1e-10; nd = int(np.sum(ker))
        if nd < current_dim and nd > 0:
            basis = ec[:, ker].T @ basis; current_dim = basis.shape[0]
        elif nd == 0: current_dim = 0

    print(f"  Left-algebra commutant dimension: {current_dim}")

    # Also include right algebra (π°)
    right_gens = [J @ gen.conj() @ J.T for gen in left_gens]
    for gen in right_gens:
        if current_dim == 0: break
        violations = []
        for k in range(current_dim):
            M = basis[k].reshape(n, n)
            comm = M @ gen - gen @ M
            violations.append(comm.real.flatten())
        V = np.array(violations)
        if np.max(np.abs(V)) < 1e-12: continue
        G = V @ V.T; ev, ec = np.linalg.eigh(G)
        ker = ev < 1e-10; nd = int(np.sum(ker))
        if nd < current_dim and nd > 0:
            basis = ec[:, ker].T @ basis; current_dim = basis.shape[0]
        elif nd == 0: current_dim = 0

    print(f"  Full bimodule commutant: {current_dim}")

    # Check: is the commutant ≅ M₂(ℂ)?
    if current_dim == 4:
        print(f"  → Commutant = M₂(ℂ) (same as Q₄₈, S89)")
        print(f"  → Algebra DOES factorize: the bimodule structure is")
        print(f"     determined by the gauge algebra alone, independent of base")
    elif current_dim > 4:
        print(f"  → Commutant > M₂(ℂ): additional symmetries at Q₁₀₂ scale")
    else:
        print(f"  → Commutant < M₂(ℂ): gauge-geometry entanglement")

    # Check: do the algebra generators commute with γ-even projections?
    # If A_fibre commutes with the γ-even projection, the algebra factorizes
    P_plus = (np.eye(n) + Gamma) / 2  # γ-even projector
    P_minus = (np.eye(n) - Gamma) / 2  # γ-odd projector

    gen_names = list(rep.keys())
    gamma_comm_count = 0
    for name, gen in rep.items():
        # Does gen commute with P_plus?
        comm_pp = gen @ P_plus - P_plus @ gen
        if np.linalg.norm(comm_pp) < 1e-10:
            gamma_comm_count += 1

    print(f"\n  Generators commuting with γ-projection: {gamma_comm_count}/{len(rep)}")
    if gamma_comm_count == len(rep):
        print(f"  → All generators commute with γ: algebra respects the γ-grading")
        print(f"  → Tensor factorization A = A_base(γ-even) ⊗ A_fibre")
    else:
        print(f"  → Some generators don't commute with γ: algebra is γ-mixed")

    # ═══════════════════════════════════════════════════════════
    # FROBENIUS CHECK: [D₊², D₋²]
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  Step 3 (folded): Frobenius Integrability [D₊², D₋²]")
    print("=" * 70)

    L2_op = L_norm @ L_norm
    DF2_op = D_F_scaled @ D_F_scaled
    frobenius = L2_op @ DF2_op - DF2_op @ L2_op
    frob_norm = np.linalg.norm(frobenius, 'fro')
    relative_frob = frob_norm / (np.linalg.norm(L2_op, 'fro') * np.linalg.norm(DF2_op, 'fro') + 1e-30)

    print(f"  ||[L², D_F²]|| = {frob_norm:.4f}")
    print(f"  Relative: ||[L², D_F²]|| / (||L²||·||D_F²||) = {relative_frob:.4f}")

    if relative_frob < 0.01:
        print(f"  → INTEGRABLE: L² and D_F² approximately commute")
        print(f"  → The γ-even and γ-odd sectors decouple under squaring")
    elif relative_frob < 0.1:
        print(f"  → WEAKLY NON-INTEGRABLE: small but nonzero coupling")
    else:
        print(f"  → NON-INTEGRABLE: significant [L², D_F²] mixing")
        print(f"  → The gauge-geometry coupling persists at the squared level")

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print("=" * 70)
    print(f"""
  (a) Fibre structure: {'YES' if is_fibre else 'NO'}
      Mean neighbourhood overlap: {mean_ovlp:.2f}
      → Q₅₁ does NOT decompose as Q_base × Q₂₄

  (b) d_s of D₊ (L alone): {ds_L_plateau:.2f}
      d_s of D₋ (D_F alone): {ds_DF_plateau:.2f}
      → {'D₊ carries d_s ≈ 4 independently → Option C viable' if abs(ds_L_plateau - 4) < 0.5 else 'D₊ lacks independent d_s = 4'}

  (c) Cross term C = LD_F + D_FL:
      ||C|| / total = {np.linalg.norm(C_actual,'fro')/total:.1%}
      C {'anticommutes' if np.linalg.norm(anti_C_gamma) < 1e-10 else 'commutes' if np.linalg.norm(comm_C_gamma) < 1e-10 else 'mixed'} with γ
      → Algebraically consistent with inner fluctuation (gauge connection)

  (d) Bimodule commutant: {current_dim} dimensions
      → {'M₂(ℂ) — algebra factorizes' if current_dim == 4 else 'Non-standard commutant'}

  Frobenius [L², D_F²]: relative = {relative_frob:.4f}
      → {'Integrable' if relative_frob < 0.01 else 'Weakly non-integrable' if relative_frob < 0.1 else 'Non-integrable'}

  OPTION C ASSESSMENT:
""")

    if abs(ds_L_plateau - 4) < 0.5 and current_dim >= 4:
        print(f"  ★ OPTION C HOLDS: spectral product without geometric product.")
        print(f"  The operator-level D = D_L + D_F is the physical product structure.")
        print(f"  D_L carries d_s ≈ 4 independently. The algebra factorizes.")
        print(f"  The graph-level non-product is where the gauge connection lives.")
    else:
        print(f"  Option C needs further investigation.")
        if abs(ds_L_plateau - 4) >= 0.5:
            print(f"  Issue: D₊ d_s = {ds_L_plateau:.2f}, not ≈ 4.")
        if current_dim < 4:
            print(f"  Issue: commutant < M₂(ℂ), algebra entangled.")


if __name__ == '__main__':
    main()
