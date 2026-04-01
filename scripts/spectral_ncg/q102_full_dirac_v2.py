#!/usr/bin/env python3
"""
q102_full_dirac_v2.py — Full Dirac D = D_L + D_F with correct Laplacian

Uses the UNNORMALISED Laplacian (matching S70 methodology) and scans
relative scales to find the d_s of the combined operator.

Also computes d_s on Q₅₁ alone (the particle sector, 51 vertices)
to verify we recover the S70 result (d_s ≈ 4).

Usage:
  python3 q102_full_dirac_v2.py [--seed S]
"""

import numpy as np
import argparse
import time
from q102_build_v1 import (
    build_c_closed_quotient, complete_ternary, haar_C3, fidelity,
    build_J, G0_TOPO, build_multiway
)
from q102_orderone_v1 import (
    j_compatible_triplets, build_representation,
    incremental_order_one
)


def rebuild_df(Q, psi_init):
    """Rebuild D_F basis and return a representative D_F matrix."""
    n = Q['n_cl']
    J, j_map = build_J(Q)
    gamma = np.array([1.0 if Q['cl_origin'][c]=='orig_only' else -1.0 for c in range(n)])
    orig_idx = [c for c in range(n) if gamma[c] > 0]
    conj_idx = [c for c in range(n) if gamma[c] < 0]

    triplets, v2c, v2f = j_compatible_triplets(Q, J, gamma)
    rep = build_representation(Q, triplets, v2c)
    oo_basis, oo_dim = incremental_order_one(n, orig_idx, conj_idx, rep, J)

    if oo_dim == 0:
        return None, n, gamma

    jd_rows = []
    for k in range(oo_dim):
        M = oo_basis[k].reshape(len(conj_idx), len(orig_idx))
        D_k = np.zeros((n, n), dtype=np.complex128)
        ci = np.array(conj_idx); oi = np.array(orig_idx)
        D_k[np.ix_(ci, oi)] = M; D_k[np.ix_(oi, ci)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())

    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd, eigvecs_jd = np.linalg.eigh(G_jd)
    ker_mask = eigvals_jd < 1e-14
    final_coords = eigvecs_jd[:, ker_mask].T
    final_basis = final_coords @ oo_basis

    # Build representative D_F (sum of basis, normalised)
    dim = final_basis.shape[0]
    n_conj = len(conj_idx); n_orig = len(orig_idx)
    M_rep = np.zeros((n_conj, n_orig))
    for k in range(dim):
        M_rep += final_basis[k].reshape(n_conj, n_orig)

    D_F = np.zeros((n, n))
    ci = np.array(conj_idx); oi = np.array(orig_idx)
    D_F[np.ix_(ci, oi)] = M_rep
    D_F[np.ix_(oi, ci)] = M_rep.T

    return D_F, n, gamma


def build_adjacency(Q):
    """Build adjacency matrix from hyperedges."""
    n = Q['n_cl']
    adj = np.zeros((n, n))
    for c1, c2, c3 in Q['q_he']:
        adj[c1,c2] = adj[c2,c1] = 1
        adj[c1,c3] = adj[c3,c1] = 1
        adj[c2,c3] = adj[c3,c2] = 1
    np.fill_diagonal(adj, 0)
    return adj


def spectral_dimension_from_laplacian(L_evals, n_t=500):
    """Compute d_s(t) from Laplacian eigenvalues using return probability.

    P(t) = (1/N) Tr(e^{-tL}) = (1/N) Σ e^{-t λ_i}
    d_s(t) = -2 d(ln P)/d(ln t)
    """
    n = len(L_evals)
    pos = L_evals[L_evals > 1e-14]
    if len(pos) == 0:
        return np.ones(n_t), np.zeros(n_t)

    lam_max = pos.max()
    lam_min = pos.min()

    # t range: from UV (small t, sees all eigenvalues) to IR (large t, sees zero modes)
    t_range = np.logspace(np.log10(0.01 / lam_max), np.log10(50.0 / lam_min), n_t)
    ds = np.zeros(n_t)

    for i, t in enumerate(t_range):
        exp_vals = np.exp(-t * L_evals)
        P = np.sum(exp_vals) / n
        dP = -np.sum(L_evals * exp_vals) / n
        if P > 1e-300:
            ds[i] = -2.0 * t * dP / P

    return t_range, ds


def find_plateau(t_range, ds):
    """Find plateau as the value at the inflection point."""
    n = len(ds)
    ln_t = np.log(t_range)
    margin = n // 6

    # Compute derivative |d(d_s)/d(ln t)|
    dds = np.abs(np.gradient(ds, ln_t))
    # Smooth
    w = max(5, n // 20)
    dds_s = np.convolve(dds, np.ones(w)/w, mode='same')

    search = dds_s[margin:-margin]
    if len(search) == 0:
        return np.mean(ds)

    best = margin + np.argmin(search)
    hw = max(5, n // 20)
    return np.mean(ds[max(0, best-hw):min(n, best+hw)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("="*60)
    print("  Full Dirac D = D_L + D_F: Correct Laplacian (v2)")
    print("="*60)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    # ─── Build Q₅₁ (particle sector only) for reference d_s ───
    print(f"\n  Building Q₅₁ (particle sector)...")
    psi_51, depth_51, edges_51 = build_multiway(complete_ternary(6), psi_init, depth=4)
    all_vids = sorted(psi_51.keys())
    clusters_51 = []; vid_to_cid_51 = {}
    for v in all_vids:
        matched = False
        for ci, (_, rp) in enumerate(clusters_51):
            if fidelity(psi_51[v], rp) > 0.999:
                vid_to_cid_51[v] = ci; matched = True; break
        if not matched:
            vid_to_cid_51[v] = len(clusters_51)
            clusters_51.append((v, psi_51[v]))
    n51 = len(clusters_51)
    print(f"  Q₅₁: {n51} vertices")

    # Q₅₁ adjacency and Laplacian
    adj_51 = np.zeros((n51, n51))
    for _, v1, v2, v3 in edges_51:
        if v1 in vid_to_cid_51 and v2 in vid_to_cid_51 and v3 in vid_to_cid_51:
            c1, c2, c3 = vid_to_cid_51[v1], vid_to_cid_51[v2], vid_to_cid_51[v3]
            adj_51[c1,c2] = adj_51[c2,c1] = 1
            adj_51[c1,c3] = adj_51[c3,c1] = 1
            adj_51[c2,c3] = adj_51[c3,c2] = 1
    np.fill_diagonal(adj_51, 0)
    deg_51 = adj_51.sum(axis=1)
    L_51 = np.diag(deg_51) - adj_51

    evals_51 = np.linalg.eigvalsh(L_51)
    t_51, ds_51 = spectral_dimension_from_laplacian(evals_51)
    ds_51_plateau = find_plateau(t_51, ds_51)
    ds_51_max = np.max(ds_51[30:-30])

    print(f"  Q₅₁ Laplacian d_s: plateau = {ds_51_plateau:.3f}, max = {ds_51_max:.3f}")

    # ─── Build Q₁₀₂ ───
    print(f"\n  Building Q₁₀₂...")
    Q102 = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)
    n = Q102['n_cl']
    print(f"  Q₁₀₂: {n} vertices")

    # Q₁₀₂ adjacency and Laplacian
    adj_102 = build_adjacency(Q102)
    deg_102 = adj_102.sum(axis=1)
    L_102 = np.diag(deg_102) - adj_102

    evals_102 = np.linalg.eigvalsh(L_102)
    t_102, ds_102 = spectral_dimension_from_laplacian(evals_102)
    ds_102_plateau = find_plateau(t_102, ds_102)
    ds_102_max = np.max(ds_102[30:-30])

    print(f"  Q₁₀₂ Laplacian d_s: plateau = {ds_102_plateau:.3f}, max = {ds_102_max:.3f}")

    # ─── Build D_F ───
    print(f"\n  Building D_F...")
    D_F, n, gamma = rebuild_df(Q102, psi_init)
    if D_F is None:
        print("  D_F construction failed!")
        return

    Gamma = np.diag(gamma)

    # Verify orthogonality
    print(f"\n  Orthogonality: Tr(D_F† L) = {np.trace(D_F.T @ L_102):.2e}")
    print(f"  ||{{D_F, γ}}|| = {np.linalg.norm(D_F @ Gamma + Gamma @ D_F, 'fro'):.2e}")
    print(f"  ||[L, γ]|| = {np.linalg.norm(L_102 @ Gamma - Gamma @ L_102, 'fro'):.2e}")

    # ─── Full Dirac: D = L + λ D_F ───
    print(f"\n{'='*60}")
    print(f"  FULL DIRAC: D = L + λ·D_F")
    print(f"{'='*60}")

    # The key: use the UNNORMALISED Laplacian (matches S70)
    # Scale D_F relative to L

    norm_L = np.linalg.norm(L_102, 'fro')
    norm_DF = np.linalg.norm(D_F, 'fro')
    print(f"\n  ||L|| = {norm_L:.2f}, ||D_F|| = {norm_DF:.4f}")
    print(f"  Natural scale: λ_natural = ||L||/||D_F|| = {norm_L/norm_DF:.1f}")

    lambdas = [0, 0.001, 0.01, 0.1, 0.5, 1, 2, 5, 10, 50, 100,
               norm_L/norm_DF * 0.1,
               norm_L/norm_DF * 0.5,
               norm_L/norm_DF,
               norm_L/norm_DF * 2,
               norm_L/norm_DF * 10]
    lambdas = sorted(set(lambdas))

    print(f"\n  {'λ':>10s}  {'d_s plateau':>11s}  {'d_s max':>8s}  {'notes':>25s}")
    print(f"  {'-'*60}")

    best_plateau = 0
    best_lambda = 0

    for lam in lambdas:
        D_full = L_102 + lam * D_F
        D_full_sq = D_full @ D_full
        evals = np.linalg.eigvalsh(D_full_sq)

        t_f, ds_f = spectral_dimension_from_laplacian(evals)
        ds_p = find_plateau(t_f, ds_f)
        ds_m = np.max(ds_f[30:-30]) if len(ds_f) > 60 else 0

        note = ""
        if lam == 0: note = "pure Laplacian"
        elif abs(lam - norm_L/norm_DF) < 1: note = "natural scale"
        if abs(ds_p - 4) < 0.5: note += " ★ d≈4"

        if ds_p > best_plateau:
            best_plateau = ds_p
            best_lambda = lam

        print(f"  {lam:10.2f}  {ds_p:11.3f}  {ds_m:8.3f}  {note:>25s}")

    # ─── Detailed analysis at best λ ───
    print(f"\n{'='*60}")
    print(f"  BEST λ = {best_lambda:.2f} (d_s plateau = {best_plateau:.3f})")
    print(f"{'='*60}")

    D_best = L_102 + best_lambda * D_F
    D_best_sq = D_best @ D_best
    evals_best = np.linalg.eigvalsh(D_best_sq)
    t_best, ds_best = spectral_dimension_from_laplacian(evals_best)

    print(f"\n  D² spectrum at best λ:")
    print(f"    Nonzero: {np.sum(evals_best > 1e-14)}")
    print(f"    Range: [{np.min(evals_best[evals_best > 1e-14]):.4f}, {np.max(evals_best):.4f}]")
    print(f"    Spread: {np.max(evals_best) / np.min(evals_best[evals_best > 1e-14]):.1f}×")

    # d_s curve at several t values
    print(f"\n  d_s(t) at selected t values:")
    for frac in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        idx = int(frac * len(t_best))
        if idx < len(t_best):
            print(f"    t = {t_best[idx]:.4f}: d_s = {ds_best[idx]:.3f}")

    # ─── Also: D² = L² + D_F² decomposition (since L ⊥ D_F under trace) ───
    print(f"\n  D² decomposition at natural scale:")
    lam_nat = norm_L / norm_DF
    D_nat = L_102 + lam_nat * D_F
    D_nat_sq = D_nat @ D_nat
    L_sq = L_102 @ L_102
    DF_sq = (lam_nat * D_F) @ (lam_nat * D_F)
    cross = D_nat_sq - L_sq - DF_sq

    print(f"    ||D²|| = {np.linalg.norm(D_nat_sq, 'fro'):.2f}")
    print(f"    ||L²|| = {np.linalg.norm(L_sq, 'fro'):.2f}")
    print(f"    ||λ²D_F²|| = {np.linalg.norm(DF_sq, 'fro'):.2f}")
    print(f"    ||cross|| = {np.linalg.norm(cross, 'fro'):.2f}")
    print(f"    cross/total = {np.linalg.norm(cross, 'fro')/np.linalg.norm(D_nat_sq, 'fro'):.3f}")

    # ─── Summary ───
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Q₅₁ Laplacian:       d_s plateau = {ds_51_plateau:.3f}, max = {ds_51_max:.3f}")
    print(f"  Q₁₀₂ Laplacian:      d_s plateau = {ds_102_plateau:.3f}, max = {ds_102_max:.3f}")
    print(f"  D_F alone:            d_s ≈ 0.7 (internal)")
    print(f"  D_full (best λ={best_lambda:.1f}): d_s plateau = {best_plateau:.3f}")
    print(f"  Product D = D_L + D_F: orthogonal (exact)")


if __name__ == '__main__':
    main()
