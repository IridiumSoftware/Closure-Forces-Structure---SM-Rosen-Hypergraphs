#!/usr/bin/env python3
"""
g3_session1_higgs_filter_v1.py — Identify the Higgs direction in D_F space

Session 1 of the G3 VEV project. Two independent criteria:

  Criterion 1 (Commutator filtering):
    For each D_F basis vector Dᵢ, compute ||[Dᵢ, π(a)]||² for all algebra generators.
    Higgs = couples to ℍ, colour-singlet.

  Criterion 2 (Tier B projection):
    For each Dᵢ, compute fraction of norm in Tier B ↔ rest matrix elements.
    Higgs should maximise Tier B coupling.

  Cross-check (Gauge orbit):
    Compute [X, D₀] for gauge Lie algebra generators X.
    Higgs must be orthogonal to gauge orbit tangent space.

Usage:
  python3 g3_session1_higgs_filter_v1.py [--seed S]
"""

import numpy as np
import argparse
import time
from collections import defaultdict
from three_gen_orderone_v1 import (
    build_3gen_q48, build_3gen_representation,
    compute_violations_batch
)


def compute_df_basis(n48, n_total, qp48, qt, cl_origin, J, gamma, j_map, rep):
    """Recompute the D_F basis (order-one + JD=+DJ) on ℂ^{n_total}."""
    n_gen = 3
    Gamma = np.diag(gamma)
    orig_idx = np.array([i for i in range(n_total) if gamma[i] > 0], dtype=np.int64)
    conj_idx = np.array([i for i in range(n_total) if gamma[i] < 0], dtype=np.int64)
    n_orig = len(orig_idx); n_conj = len(conj_idx)
    dim_M = n_conj * n_orig

    J_inv = J.T
    opp = {name: J @ pi.conj() @ J_inv for name, pi in rep.items()}
    gen_names = [f'E_{i}{j}' for i in range(3) for j in range(3)] + ['sigma1','sigma2','sigma3']

    print(f"  Order-one on ℂ^{n_total}: dim_M={dim_M}")

    # Warmup numba
    _ = compute_violations_batch(
        np.eye(2, dim_M), conj_idx, orig_idx,
        np.zeros((n_total,n_total), dtype=np.complex128),
        np.zeros((n_total,n_total), dtype=np.complex128), n_total)

    basis = np.eye(dim_M)
    current_dim = dim_M
    t0 = time.time()
    total_pairs = len(gen_names)**2

    for ai, a_name in enumerate(gen_names):
        pi_a = rep[a_name].astype(np.complex128)
        for bi, b_name in enumerate(gen_names):
            pi_b_opp = opp[b_name].astype(np.complex128)
            if current_dim == 0: break
            V = compute_violations_batch(basis, conj_idx, orig_idx, pi_a, pi_b_opp, n_total)
            if np.max(np.abs(V)) < 1e-12: continue
            G = V @ V.T
            eigvals, eigvecs = np.linalg.eigh(G)
            ker_mask = eigvals < 1e-14
            new_dim = int(np.sum(ker_mask))
            if new_dim < current_dim and new_dim > 0:
                basis = eigvecs[:, ker_mask].T @ basis
                current_dim = basis.shape[0]
            elif new_dim == 0:
                current_dim = 0; break
        if current_dim == 0: break
        if (ai+1) % 3 == 0:
            print(f"    gen {ai+1}/{len(gen_names)}: dim={current_dim} ({time.time()-t0:.0f}s)")

    print(f"  Order-one kernel: {current_dim} ({time.time()-t0:.0f}s)")

    if current_dim == 0:
        return None, orig_idx, conj_idx, 0

    # JD = +DJ
    jd_rows = []
    for k in range(current_dim):
        M = basis[k].reshape(n_conj, n_orig)
        D_k = np.zeros((n_total, n_total), dtype=np.complex128)
        D_k[np.ix_(conj_idx, orig_idx)] = M
        D_k[np.ix_(orig_idx, conj_idx)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())

    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd, eigvecs_jd = np.linalg.eigh(G_jd)
    ker_mask = eigvals_jd < 1e-14
    final_coords = eigvecs_jd[:, ker_mask].T
    final_basis = final_coords @ basis
    dim_DF = final_basis.shape[0]

    print(f"  Final D_F dimension: {dim_DF}")
    return final_basis, orig_idx, conj_idx, dim_DF


def basis_to_matrix(vec, conj_idx, orig_idx, n_total):
    """Convert a basis vector to a full n_total × n_total matrix."""
    n_conj = len(conj_idx); n_orig = len(orig_idx)
    M = vec.reshape(n_conj, n_orig)
    D = np.zeros((n_total, n_total), dtype=np.complex128)
    D[np.ix_(conj_idx, orig_idx)] = M
    D[np.ix_(orig_idx, conj_idx)] = M.T
    return D


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("="*60)
    print("  G3 Session 1: Higgs Direction in D_F Space")
    print("="*60)

    # Build 3-gen Q₄₈
    n48, n_total, qp48, qt, cl_origin, J, gamma, j_map = build_3gen_q48(args.seed)
    n_gen = 3
    print(f"\n  Q₄₈: {n48} vertices, 3-gen space: ℂ^{n_total}")

    # Build representation
    rep, triplets = build_3gen_representation(n48, n_total, qp48, qt, cl_origin, J, gamma, j_map)

    # Compute D_F basis
    print(f"\n  Computing D_F basis...")
    final_basis, orig_idx, conj_idx, dim_DF = compute_df_basis(
        n48, n_total, qp48, qt, cl_origin, J, gamma, j_map, rep)

    if final_basis is None:
        print("  ERROR: D_F basis computation failed")
        return

    # Build D_F matrices for all basis vectors
    print(f"\n  Building {dim_DF} D_F matrices...")
    D_matrices = []
    for k in range(dim_DF):
        D_k = basis_to_matrix(final_basis[k], conj_idx, orig_idx, n_total)
        D_matrices.append(D_k)

    # ═══════════════════════════════════════════════════════════
    # CRITERION 1: Commutator filtering
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  CRITERION 1: Commutator Filtering")
    print(f"{'='*60}")

    # For each D_k, compute ||[D_k, gen]||² for each generator
    colour_gens = [f'E_{i}{j}' for i in range(3) for j in range(3)]
    weak_gens = ['sigma1', 'sigma2', 'sigma3']

    colour_norms = np.zeros((dim_DF, len(colour_gens)))
    weak_norms = np.zeros((dim_DF, len(weak_gens)))

    for k, D_k in enumerate(D_matrices):
        for gi, gname in enumerate(colour_gens):
            comm = D_k @ rep[gname] - rep[gname] @ D_k
            colour_norms[k, gi] = np.linalg.norm(comm, 'fro') ** 2
        for gi, gname in enumerate(weak_gens):
            comm = D_k @ rep[gname] - rep[gname] @ D_k
            weak_norms[k, gi] = np.linalg.norm(comm, 'fro') ** 2

    # Summary statistics
    colour_total = colour_norms.sum(axis=1)  # total colour coupling per D_k
    weak_total = weak_norms.sum(axis=1)      # total weak coupling per D_k

    print(f"\n  ||[Dᵢ, M₃(ℂ)]||² per basis vector:")
    print(f"    Range: {colour_total.min():.6f} – {colour_total.max():.6f}")
    print(f"    Mean: {colour_total.mean():.6f}")
    print(f"    # with colour coupling > 1e-10: {np.sum(colour_total > 1e-10)}")
    print(f"    # colour-singlet (< 1e-10): {np.sum(colour_total < 1e-10)}")

    print(f"\n  ||[Dᵢ, ℍ]||² per basis vector:")
    print(f"    Range: {weak_total.min():.6f} – {weak_total.max():.6f}")
    print(f"    Mean: {weak_total.mean():.6f}")
    print(f"    # with weak coupling > 1e-10: {np.sum(weak_total > 1e-10)}")
    print(f"    # weak-inert (< 1e-10): {np.sum(weak_total < 1e-10)}")

    # Classification
    colour_singlet = colour_total < 1e-10
    weak_active = weak_total > 1e-10

    higgs_mask = colour_singlet & weak_active    # Higgs: colour-singlet, weak-active
    yukawa_mask = ~colour_singlet & weak_active   # Yukawa: colour-active, weak-active
    gauge_mask = colour_singlet & ~weak_active    # Pure gauge: singlet, inert
    mixed_mask = ~colour_singlet & ~weak_active   # Inert to both

    n_higgs = np.sum(higgs_mask)
    n_yukawa = np.sum(yukawa_mask)
    n_gauge = np.sum(gauge_mask)
    n_mixed = np.sum(mixed_mask)

    print(f"\n  Classification of {dim_DF} D_F directions:")
    print(f"    Higgs (colour-singlet, weak-active): {n_higgs}")
    print(f"    Yukawa (colour-active, weak-active): {n_yukawa}")
    print(f"    Inert-gauge (colour-singlet, weak-inert): {n_gauge}")
    print(f"    Other (colour-active, weak-inert): {n_mixed}")
    print(f"    Total: {n_higgs + n_yukawa + n_gauge + n_mixed}")

    # ═══════════════════════════════════════════════════════════
    # CRITERION 2: Tier B projection
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  CRITERION 2: Tier B Projection")
    print(f"{'='*60}")

    # Identify Tier B indices in ℂ^{n_total}
    tier_b_vertices = [c for c in range(n48) if qt.get(c) == 'B']
    tier_b_idx = set()
    for c in tier_b_vertices:
        for g in range(n_gen):
            tier_b_idx.add(c * n_gen + g)
    tier_b_idx = sorted(tier_b_idx)
    non_b_idx = sorted(set(range(n_total)) - set(tier_b_idx))

    print(f"  Tier B indices: {len(tier_b_idx)} / {n_total}")

    # For each D_k, compute fraction of norm in Tier B ↔ rest
    h_scores = np.zeros(dim_DF)
    for k, D_k in enumerate(D_matrices):
        # Norm in B↔non-B blocks
        block_Bn = D_k[np.ix_(tier_b_idx, non_b_idx)]
        block_nB = D_k[np.ix_(non_b_idx, tier_b_idx)]
        tier_b_norm = np.linalg.norm(block_Bn, 'fro')**2 + np.linalg.norm(block_nB, 'fro')**2
        total_norm = np.linalg.norm(D_k, 'fro')**2
        h_scores[k] = tier_b_norm / total_norm if total_norm > 0 else 0

    print(f"\n  h_i = ||D_i|_{{B↔rest}}||² / ||D_i||²:")
    print(f"    Range: {h_scores.min():.4f} – {h_scores.max():.4f}")
    print(f"    Mean: {h_scores.mean():.4f}")

    # Top directions by Tier B coupling
    top_k = min(20, dim_DF)
    top_idx = np.argsort(h_scores)[::-1][:top_k]
    print(f"\n  Top {top_k} by Tier B coupling:")
    print(f"  {'idx':>5} {'h_i':>8} {'colour':>10} {'weak':>10} {'class':>10}")
    for idx in top_idx:
        cls = ('Higgs' if higgs_mask[idx] else
               'Yukawa' if yukawa_mask[idx] else
               'Inert-G' if gauge_mask[idx] else 'Other')
        print(f"  {idx:>5} {h_scores[idx]:>8.4f} {colour_total[idx]:>10.4f} "
              f"{weak_total[idx]:>10.4f} {cls:>10}")

    # ═══════════════════════════════════════════════════════════
    # CROSS-CHECK: Gauge orbit tangent space
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  CROSS-CHECK: Gauge Orbit Tangent Space")
    print(f"{'='*60}")

    # Build a representative D_F (normalised sum)
    D_rep = np.zeros((n_total, n_total), dtype=np.complex128)
    for D_k in D_matrices:
        D_rep += D_k
    D_rep /= np.linalg.norm(D_rep, 'fro')

    # Gauge generators: [X, D_rep] for X in su(3) ⊕ su(2) ⊕ u(1)
    # su(3): E_{ij} - E_{ji} (antisymmetric) and i(E_{ij} + E_{ji}) (symmetric)
    # Plus diagonal: E_{00}-E_{11}, E_{00}-E_{22} (traceless diagonal)
    gauge_fluctuations = []

    # su(3) generators (8 Gell-Mann-like)
    for i in range(3):
        for j in range(i+1, 3):
            # Real antisymmetric
            X = rep[f'E_{i}{j}'] - rep[f'E_{j}{i}']
            comm = X @ D_rep - D_rep @ X
            if np.linalg.norm(comm, 'fro') > 1e-12:
                gauge_fluctuations.append(('su3_real', comm))
            # Imaginary symmetric
            X = 1j * (rep[f'E_{i}{j}'] + rep[f'E_{j}{i}'])
            comm = X @ D_rep - D_rep @ X
            if np.linalg.norm(comm, 'fro') > 1e-12:
                gauge_fluctuations.append(('su3_imag', comm))
    # Diagonal traceless
    X = rep['E_00'] - rep['E_11']
    comm = X @ D_rep - D_rep @ X
    if np.linalg.norm(comm, 'fro') > 1e-12:
        gauge_fluctuations.append(('su3_diag', comm))
    X = rep['E_00'] + rep['E_11'] - 2*rep['E_22']
    comm = X @ D_rep - D_rep @ X
    if np.linalg.norm(comm, 'fro') > 1e-12:
        gauge_fluctuations.append(('su3_diag', comm))

    # su(2) generators
    for name in ['sigma1', 'sigma2', 'sigma3']:
        X = rep[name]
        comm = X @ D_rep - D_rep @ X
        if np.linalg.norm(comm, 'fro') > 1e-12:
            gauge_fluctuations.append(('su2', comm))

    # u(1): identity on Tier B (hypercharge-like)
    X = rep.get('I_H', np.zeros((n_total, n_total)))
    comm = X @ D_rep - D_rep @ X
    if np.linalg.norm(comm, 'fro') > 1e-12:
        gauge_fluctuations.append(('u1', comm))

    print(f"  Non-zero gauge fluctuations [X, D₀]: {len(gauge_fluctuations)}")
    for gtype, _ in gauge_fluctuations:
        count = sum(1 for t, _ in gauge_fluctuations if t == gtype)
    for gtype in sorted(set(t for t, _ in gauge_fluctuations)):
        count = sum(1 for t, _ in gauge_fluctuations if t == gtype)
        print(f"    {gtype}: {count}")

    # Project gauge fluctuations onto D_F parameter space
    # For each gauge fluctuation matrix G, compute overlap with each D_F basis vector
    if gauge_fluctuations:
        gauge_vecs = []
        for _, comm in gauge_fluctuations:
            # Extract the off-diagonal block (conj × orig) — same parameterisation as D_F
            M_gauge = comm[np.ix_(conj_idx, orig_idx)]
            gauge_vecs.append(M_gauge.real.flatten())

        gauge_mat = np.array(gauge_vecs)
        # Rank of gauge orbit tangent space within D_F
        rank_gauge = np.linalg.matrix_rank(gauge_mat, tol=1e-10)
        print(f"\n  Gauge orbit tangent space dimension: {rank_gauge}")

        # Orthogonal complement = Higgs + Yukawa directions
        # Project D_F basis onto gauge orbit and compute residual
        U_gauge, S_gauge, Vt_gauge = np.linalg.svd(gauge_mat, full_matrices=False)
        gauge_rank = np.sum(S_gauge > 1e-10)
        gauge_basis = Vt_gauge[:gauge_rank]  # orthonormal basis for gauge orbit

        # For each D_F basis vector, compute overlap with gauge orbit
        gauge_overlap = np.zeros(dim_DF)
        for k in range(dim_DF):
            D_vec = final_basis[k]  # in the off-diagonal parameterisation
            proj = gauge_basis @ D_vec
            gauge_overlap[k] = np.linalg.norm(proj)**2 / (np.linalg.norm(D_vec)**2 + 1e-30)

        print(f"  Gauge orbit overlap per D_F vector:")
        print(f"    Range: {gauge_overlap.min():.6f} – {gauge_overlap.max():.6f}")
        print(f"    Mean: {gauge_overlap.mean():.6f}")
        print(f"    # orthogonal to gauge (overlap < 0.01): {np.sum(gauge_overlap < 0.01)}")
    else:
        print(f"  No gauge fluctuations (all [X, D₀] = 0)")
        gauge_overlap = np.zeros(dim_DF)

    # ═══════════════════════════════════════════════════════════
    # CONSISTENCY CHECK: Do Criteria 1 and 2 agree?
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  CONSISTENCY: Criteria 1 vs 2")
    print(f"{'='*60}")

    # Correlation between weak coupling strength and Tier B projection
    corr = np.corrcoef(weak_total, h_scores)[0,1]
    print(f"\n  Correlation (weak coupling ↔ Tier B fraction): r = {corr:.4f}")

    # Do the Higgs-classified directions (Criterion 1) have high h_i (Criterion 2)?
    if n_higgs > 0:
        higgs_h = h_scores[higgs_mask]
        non_higgs_h = h_scores[~higgs_mask]
        print(f"  Mean h_i for Higgs directions: {higgs_h.mean():.4f}")
        print(f"  Mean h_i for non-Higgs directions: {non_higgs_h.mean():.4f}")
        print(f"  Separation: {higgs_h.mean() / non_higgs_h.mean():.2f}x" if non_higgs_h.mean() > 0 else "")

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    print(f"""
  D_F family: {dim_DF} parameters on ℂ^{n_total}

  Criterion 1 (Commutator filtering):
    Colour-singlet ([D, M₃]=0): {np.sum(colour_singlet)} / {dim_DF}
    Weak-active ([D, ℍ]≠0):     {np.sum(weak_active)} / {dim_DF}
    Higgs (singlet + active):    {n_higgs}
    Yukawa (colour + active):    {n_yukawa}
    Inert:                       {n_gauge + n_mixed}

  Criterion 2 (Tier B projection):
    Mean h_i (Higgs dirs):       {h_scores[higgs_mask].mean():.4f if n_higgs > 0 else 'N/A'}
    Mean h_i (non-Higgs):        {h_scores[~higgs_mask].mean():.4f if n_higgs < dim_DF else 'N/A'}

  Criteria 1↔2 correlation:      r = {corr:.4f}

  Gauge orbit tangent dim:       {len(gauge_fluctuations)}
""")

    if n_higgs > 0 and corr > 0.5:
        print(f"  ★ Criteria 1 and 2 AGREE: Higgs = weak-active, colour-singlet, Tier B coupled")
    elif n_higgs > 0:
        print(f"  Criteria 1 identifies {n_higgs} Higgs directions but weak correlation with Criterion 2")
    else:
        print(f"  No Higgs directions found by Criterion 1")


if __name__ == '__main__':
    main()
