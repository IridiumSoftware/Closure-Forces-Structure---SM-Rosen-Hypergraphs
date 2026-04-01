#!/usr/bin/env python3
"""
vev_landscape_v1.py — VEV selection on the D_F landscape

Characterizes V(D_F) = Tr(D⁴) on the 270-dimensional (real) D_F parameter space
of the quark-sector spectral triple on ℂ¹⁴⁴ = Q₄₈ × 3 generations.

Since a₂ = Tr(D²) is rigid (S97, CV=0), the leading potential is a₄ = Tr(D⁴).
We minimize Tr(D⁴) on the unit sphere |θ|² = 1 (direction only; scale fixed by a₂).

Mathematical conventions:
  - D_F = Σᵢ θᵢ Bᵢ where Bᵢ are real basis vectors from the JD=+DJ kernel
  - Bᵢ maps conj→orig block as M (real), with D[orig,conj] = M.T (symmetric D)
  - Gram matrix Tr(Bᵢ Bⱼ) ∝ δᵢⱼ (from S97 rigidity)
  - V(θ) = Tr(D⁴) = Σᵢⱼₖₗ θᵢθⱼθₖθₗ T_{ijkl}
  - Gradient: ∂V/∂θᵢ = 4 Tr(D³ Bᵢ)
  - Hessian: ∂²V/∂θᵢ∂θⱼ = 4[Tr(BⱼD²Bᵢ) + Tr(DBⱼDBᵢ) + Tr(D²BⱼBᵢ)]
  - On sphere: constrained Hessian = P(H - 4V·I)P, P = I - θθᵀ
  - Zero eigenvalues of constrained Hessian = flat directions = vacuum submanifold

SU(3)_gen structure:
  - The D_F basis connects different generations (not SU(3)_gen singlets individually)
  - But V = Tr(D⁴) IS SU(3)_gen invariant (trace is basis-independent)
  - SU(3)_gen acts on θ-space as a rotation → orbit through any minimum is vacuum
  - dim(SU(3)_gen orbit) = 8 - dim(stabiliser) gives Goldstone count

Usage:
  python3 vev_landscape_v1.py [--seed S] [--n-starts N]
"""

import numpy as np
import argparse
import time
from scipy.optimize import minimize as scipy_minimize


def load_basis(seed=0):
    """Load cached D_F basis and build full matrices on ℂ¹⁴⁴."""
    data = np.load(f'_df_basis_cache_seed{seed}.npz')
    basis_vecs = data['basis']
    orig_idx = data['orig_idx']
    conj_idx = data['conj_idx']
    dim_DF = int(data['dim_DF'])
    n_total = max(orig_idx.max(), conj_idx.max()) + 1

    D_matrices = np.zeros((dim_DF, n_total, n_total), dtype=np.float64)
    for k in range(dim_DF):
        M = basis_vecs[k].reshape(len(conj_idx), len(orig_idx))
        D_matrices[k][np.ix_(conj_idx, orig_idx)] = M
        D_matrices[k][np.ix_(orig_idx, conj_idx)] = M.T

    return D_matrices, dim_DF, n_total, orig_idx, conj_idx


# ── Core computations ──────────────────────────────────────────────

def build_D(D_matrices, theta):
    """Build D = Σ θᵢ Bᵢ."""
    return np.einsum('i,ijk->jk', theta, D_matrices)


def compute_V(D_matrices, theta):
    """V(θ) = Tr(D⁴)."""
    D = build_D(D_matrices, theta)
    D2 = D @ D
    return np.trace(D2 @ D2)


def compute_V_and_grad(D_matrices, B_flat, theta):
    """V(θ) and ∂V/∂θᵢ = 4 Tr(D³ Bᵢ), returned simultaneously."""
    D = build_D(D_matrices, theta)
    D2 = D @ D
    V = np.trace(D2 @ D2)
    D3 = D2 @ D
    grad = 4.0 * B_flat @ D3.T.ravel()
    return V, grad


def compute_hessian(D_matrices, theta):
    """∂²V/∂θᵢ∂θⱼ = 4[Tr(Bⱼ D² Bᵢ) + Tr(D Bⱼ D Bᵢ) + Tr(D² Bⱼ Bᵢ)]."""
    dim = len(theta)
    n = D_matrices.shape[1]
    D = build_D(D_matrices, theta)
    D2 = D @ D

    # X_i = D² Bᵢ, Y_i = D Bᵢ
    X = np.einsum('jk,ikl->ijl', D2, D_matrices)
    Y = np.einsum('jk,ikl->ijl', D, D_matrices)

    # Tr(A B) = Σ A[m,n] B[n,m] = (A^T flattened) · (B flattened)
    X_T_flat = np.transpose(X, (0, 2, 1)).reshape(dim, n * n)
    Y_T_flat = np.transpose(Y, (0, 2, 1)).reshape(dim, n * n)
    B_flat = D_matrices.reshape(dim, n * n)
    X_flat = X.reshape(dim, n * n)

    # M1[j,i] = Tr(Bⱼ X_i) = Σ Bⱼ[m,n] X_i[n,m]
    M1 = B_flat @ X_T_flat.T

    # M2[j,i] = Tr(Y_j Y_i) = Σ Y_j[m,n] Y_i[n,m]
    M2 = Y_T_flat @ Y_T_flat.T  # Wait: Tr(Y_j Y_i) = Y_j_flat · Y_i_T_flat

    # Actually: Tr(AB) = Σ_m Σ_n A[m,n] B[n,m]
    # If A_flat = A.ravel() (row-major: A[m,n] at index m*n_cols+n)
    # and B_T_flat = B.T.ravel() (row-major of B^T: B[n,m] at index n*n_rows+m)
    # These don't align for a simple dot product.
    # Use: Tr(AB) = Σ_{mn} A[m,n] B[n,m] = Σ_{mn} (A^T)[n,m] B[n,m] = dot(vec(A^T), vec(B))
    # So Tr(Y_j Y_i) = vec(Y_j^T) · vec(Y_i) = Y_j_T_flat · Y_i_flat
    Y_flat = Y.reshape(dim, n * n)
    M2 = Y_T_flat @ Y_flat.T

    # M3[j,i] = Tr(D² Bⱼ Bᵢ) = Tr(X_j Bᵢ) = vec(X_j^T) · vec(Bᵢ)
    B_T_flat = np.transpose(D_matrices, (0, 2, 1)).reshape(dim, n * n)
    M3 = X_T_flat @ B_T_flat.T  # Wait: Tr(X_j B_i) = vec(X_j^T) · vec(B_i)
    M3 = X_T_flat @ B_flat.T

    H = 4.0 * (M1 + M2 + M3)
    return H


# ── Optimization on sphere ──────────────────────────────────────────

def sphere_minimize(D_matrices, B_flat, theta0, n_steps=3000, minimize=True):
    """Riemannian steepest descent on S^{n-1} with Barzilai-Borwein step.

    BB step gives superlinear convergence for smooth functions on manifolds.
    """
    sign = 1.0 if minimize else -1.0
    theta = theta0 / np.linalg.norm(theta0)

    V, g_full = compute_V_and_grad(D_matrices, B_flat, theta)
    V *= sign; g_full *= sign
    g = g_full - np.dot(g_full, theta) * theta  # project to tangent

    best_V = V
    best_theta = theta.copy()
    alpha = 0.01

    for step in range(n_steps):
        gnorm = np.linalg.norm(g)
        if gnorm < 1e-14:
            break

        # Take step and retract (normalize)
        theta_new = theta - alpha * g
        theta_new /= np.linalg.norm(theta_new)

        V_new, g_full_new = compute_V_and_grad(D_matrices, B_flat, theta_new)
        V_new *= sign; g_full_new *= sign
        g_new = g_full_new - np.dot(g_full_new, theta_new) * theta_new

        # BB step size: α = |Δθ|² / |Δθ · Δg|
        dtheta = theta_new - theta
        dg = g_new - g
        denom = abs(np.dot(dtheta, dg))
        if denom > 1e-20:
            alpha_bb = np.dot(dtheta, dtheta) / denom
            alpha = min(max(alpha_bb, 1e-6), 1.0)

        # Accept if descent (otherwise halve step)
        if V_new <= V + 1e-10:
            theta = theta_new
            V = V_new
            g = g_new
            if V < best_V:
                best_V = V
                best_theta = theta.copy()
        else:
            alpha *= 0.25

    return best_theta, sign * best_V


# ── SU(3)_gen analysis ──────────────────────────────────────────────

def su3_gen_orbit_dimension(D_matrices, theta, n_total, n48, n_gen=3):
    """Compute dim of SU(3)_gen orbit through θ.

    SU(3) has 8 generators (Gell-Mann matrices). Each acts on generation indices.
    Tangent vector: δD = [T_a ⊗ I_vertex, D], projected back to D_F basis.
    Orbit dim = rank of the 8 tangent vectors in θ-space.
    """
    dim = len(theta)
    D = build_D(D_matrices, theta)
    B_flat = D_matrices.reshape(dim, n_total * n_total)

    # Gell-Mann matrices
    gm = []
    gm.append(np.array([[0, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=complex))
    gm.append(np.array([[0, -1j, 0], [1j, 0, 0], [0, 0, 0]], dtype=complex))
    gm.append(np.array([[1, 0, 0], [0, -1, 0], [0, 0, 0]], dtype=complex))
    gm.append(np.array([[0, 0, 1], [0, 0, 0], [1, 0, 0]], dtype=complex))
    gm.append(np.array([[0, 0, -1j], [0, 0, 0], [1j, 0, 0]], dtype=complex))
    gm.append(np.array([[0, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=complex))
    gm.append(np.array([[0, 0, 0], [0, 0, -1j], [0, 1j, 0]], dtype=complex))
    gm.append(np.array([[1, 0, 0], [0, 1, 0], [0, 0, -2]], dtype=complex) / np.sqrt(3))

    tangent_vecs = []
    for T_3x3 in gm:
        T_full = np.zeros((n_total, n_total), dtype=complex)
        for c in range(n48):
            for g1 in range(n_gen):
                for g2 in range(n_gen):
                    T_full[c * n_gen + g1, c * n_gen + g2] = T_3x3[g1, g2]

        comm = T_full @ D - D @ T_full
        # Project: δθᵢ = Tr(Bᵢ · comm) (real part, since D_F basis is real)
        delta_theta = B_flat @ comm.T.ravel().real
        tangent_vecs.append(delta_theta)

    tangent_mat = np.array(tangent_vecs)  # (8, dim)
    sv = np.linalg.svd(tangent_mat, compute_uv=False)
    orbit_dim = int(np.sum(sv > 1e-10 * sv[0]))
    return orbit_dim, tangent_mat, sv


# ── Constrained Hessian ────────────────────────────────────────────

def constrained_hessian_on_sphere(D_matrices, theta):
    """Constrained Hessian of V on S^{n-1} at critical point θ.

    At critical point: ∇V = λθ, λ = 4V (Euler theorem, deg-4 homogeneous).
    H_sphere = P(H_free - λI)P, P = I - θθᵀ.
    Zero eigenvalues beyond the 1 radial mode = vacuum manifold dimension.
    """
    V = compute_V(D_matrices, theta)
    H = compute_hessian(D_matrices, theta)
    dim = len(theta)
    lam = 4.0 * V
    P = np.eye(dim) - np.outer(theta, theta)
    H_c = P @ (H - lam * np.eye(dim)) @ P
    return H_c, V, lam


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n-starts', type=int, default=100)
    args = parser.parse_args()

    print("=" * 70)
    print("  VEV Landscape Analysis: V(D_F) = Tr(D⁴) on 270-dim D_F Space")
    print("=" * 70)

    # ─── PART 0: Load and verify ───
    print(f"\n  Loading D_F basis (seed {args.seed})...", flush=True)
    D_matrices, dim_DF, n_total, orig_idx, conj_idx = load_basis(args.seed)
    B_flat = D_matrices.reshape(dim_DF, -1)
    n48 = n_total // 3
    print(f"  dim_DF = {dim_DF}, n_total = {n_total}, n48 = {n48}", flush=True)

    # Verify S97
    gram_diag = np.array([np.trace(D_matrices[k] @ D_matrices[k]) for k in range(dim_DF)])
    print(f"  Tr(Bᵢ²): mean={gram_diag.mean():.6f}, CV={gram_diag.std()/gram_diag.mean():.2e}")

    # ═══════════════════════════════════════════════════════════════
    # PART 1: Hessian at uniform direction (landscape structure)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 1: Hessian of Tr(D⁴) at Uniform Direction")
    print(f"{'='*70}", flush=True)

    theta_u = np.ones(dim_DF) / np.sqrt(dim_DF)
    V_u = compute_V(D_matrices, theta_u)
    t0 = time.time()
    H_u = compute_hessian(D_matrices, theta_u)
    print(f"  Hessian computed in {time.time()-t0:.1f}s", flush=True)
    evals_H = np.linalg.eigvalsh(H_u)

    print(f"  V(uniform) = {V_u:.8f}")
    print(f"  Hessian eigenvalue range: [{evals_H[0]:.6f}, {evals_H[-1]:.6f}]")
    print(f"  # positive: {np.sum(evals_H > 1e-10)}")
    print(f"  # near-zero: {np.sum(np.abs(evals_H) < 1e-10)}")
    print(f"  # negative: {np.sum(evals_H < -1e-10)}")

    # Count distinct eigenvalues
    evals_sorted = np.sort(evals_H)
    distinct = [evals_sorted[0]]
    for e in evals_sorted[1:]:
        if abs(e - distinct[-1]) > 1e-8 * max(abs(e), abs(distinct[-1]), 1e-10):
            distinct.append(e)
    print(f"  # distinct eigenvalues: {len(distinct)}")

    # ═══════════════════════════════════════════════════════════════
    # PART 2: Minimize Tr(D⁴) on S^{dim-1}
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 2: Minimize V(θ) = Tr(D⁴) on S^{dim_DF-1}")
    print(f"{'='*70}", flush=True)

    n_starts = args.n_starts
    rng = np.random.default_rng(args.seed + 7)
    minima = []
    all_V = []

    t_start = time.time()
    for trial in range(n_starts):
        theta0 = rng.standard_normal(dim_DF)
        theta_min, V_min = sphere_minimize(D_matrices, B_flat, theta0,
                                           n_steps=3000, minimize=True)
        minima.append(theta_min)
        all_V.append(V_min)

        if (trial + 1) % 20 == 0:
            elapsed = time.time() - t_start
            rate = (trial + 1) / elapsed
            eta = (n_starts - trial - 1) / rate
            print(f"    {trial+1}/{n_starts}: best V = {min(all_V):.10f} "
                  f"({elapsed:.0f}s, ~{eta:.0f}s left)", flush=True)

    all_V = np.array(all_V)
    best_idx = np.argmin(all_V)
    theta_star = minima[best_idx]
    V_star = all_V[best_idx]
    elapsed = time.time() - t_start

    print(f"\n  Total: {elapsed:.0f}s for {n_starts} starts")
    print(f"  Global minimum: V* = {V_star:.12f}")
    print(f"  V range: [{all_V.min():.10f}, {all_V.max():.10f}]")
    print(f"  V mean: {all_V.mean():.10f}, std: {all_V.std():.10f}")

    # Cluster minima by V value
    V_sorted_idx = np.argsort(all_V)
    clusters = []
    for idx in V_sorted_idx:
        v = all_V[idx]
        found = False
        for c in clusters:
            if abs(v - c[0]) < 1e-6:
                c[1].append(idx)
                found = True
                break
        if not found:
            clusters.append((v, [idx]))

    print(f"\n  Distinct V-clusters (tol=1e-6): {len(clusters)}")
    for i, (v, members) in enumerate(clusters[:10]):
        print(f"    V = {v:.10f} ({len(members)} hits, {len(members)/n_starts*100:.0f}%)")
    if len(clusters) > 10:
        print(f"    ... + {len(clusters)-10} more")

    # Verify gradient at minimum
    _, grad = compute_V_and_grad(D_matrices, B_flat, theta_star)
    g_tang = grad - np.dot(grad, theta_star) * theta_star
    print(f"\n  At global minimum:")
    print(f"    |θ*| = {np.linalg.norm(theta_star):.12f}")
    print(f"    V(θ*) = {compute_V(D_matrices, theta_star):.12f}")
    print(f"    |∇V_tang| = {np.linalg.norm(g_tang):.2e}")

    # ═══════════════════════════════════════════════════════════════
    # PART 3: Maximize V (landscape extent)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 3: Maximize V(θ) (30 starts)")
    print(f"{'='*70}", flush=True)

    max_V_list = []
    for trial in range(30):
        theta0 = rng.standard_normal(dim_DF)
        _, V_max = sphere_minimize(D_matrices, B_flat, theta0,
                                   n_steps=3000, minimize=False)
        max_V_list.append(V_max)

    V_max_global = max(max_V_list)
    print(f"  V_max = {V_max_global:.10f}")
    print(f"  V_max/V_min = {V_max_global/V_star:.6f}")

    # ═══════════════════════════════════════════════════════════════
    # PART 4: Constrained Hessian at global minimum → vacuum dim
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 4: Constrained Hessian at Global Minimum")
    print(f"{'='*70}", flush=True)

    t0 = time.time()
    H_c, V_at_min, lam = constrained_hessian_on_sphere(D_matrices, theta_star)
    evals_c = np.linalg.eigvalsh(H_c)
    print(f"  Hessian computed in {time.time()-t0:.1f}s", flush=True)

    print(f"  V = {V_at_min:.10f}, λ = 4V = {lam:.6f}")

    evals_sorted = np.sort(evals_c)
    n_zero = int(np.sum(np.abs(evals_sorted) < 1e-6))
    n_near_zero = int(np.sum(np.abs(evals_sorted) < 1e-4))
    n_pos = int(np.sum(evals_sorted > 1e-6))
    n_neg = int(np.sum(evals_sorted < -1e-6))

    print(f"\n  Eigenvalue counts:")
    print(f"    Zero (|λ|<1e-6):      {n_zero} [1 = radial constraint]")
    print(f"    Near-zero (|λ|<1e-4): {n_near_zero}")
    print(f"    Positive (>1e-6):     {n_pos}")
    print(f"    Negative (<-1e-6):    {n_neg}")
    vacuum_dim_strict = max(0, n_zero - 1)
    vacuum_dim_relaxed = max(0, n_near_zero - 1)
    print(f"\n  ★ Vacuum submanifold dimension: {vacuum_dim_strict} (strict)")
    print(f"  ★ Vacuum submanifold dimension: {vacuum_dim_relaxed} (relaxed, <1e-4)")

    # Eigenvalue spectrum
    print(f"\n  Smallest 30 eigenvalues:")
    for i in range(min(30, dim_DF)):
        print(f"    λ_{i:3d} = {evals_sorted[i]:+.10f}")
    print(f"\n  Largest 10 eigenvalues:")
    for i in range(max(0, dim_DF - 10), dim_DF):
        print(f"    λ_{i:3d} = {evals_sorted[i]:+.10f}")

    # Non-zero spectrum statistics
    evals_nz = evals_sorted[np.abs(evals_sorted) > 1e-6]
    if len(evals_nz) > 0:
        print(f"\n  Nonzero eigenvalue stats:")
        print(f"    Count: {len(evals_nz)}")
        print(f"    Range: [{evals_nz[0]:.8f}, {evals_nz[-1]:.8f}]")
        print(f"    Mean: {np.mean(evals_nz):.8f}")

    # ═══════════════════════════════════════════════════════════════
    # PART 5: Hessian at multiple minima (consistency)
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 5: Hessian at Multiple Minima")
    print(f"{'='*70}", flush=True)

    # Pick 5 distinct minima
    unique_min = []
    for idx in np.argsort(all_V):
        is_new = True
        for um_idx in unique_min:
            if abs(all_V[idx] - all_V[um_idx]) < 1e-6:
                overlap = abs(np.dot(minima[idx], minima[um_idx]))
                if overlap > 0.99:
                    is_new = False
                    break
        if is_new:
            unique_min.append(idx)
        if len(unique_min) >= 5:
            break

    evals_c_full, evecs_c_full = np.linalg.eigh(H_c)  # for Part 6

    for rank, idx in enumerate(unique_min):
        H_ci, V_i, _ = constrained_hessian_on_sphere(D_matrices, minima[idx])
        ev_i = np.sort(np.linalg.eigvalsh(H_ci))
        nz_i = int(np.sum(np.abs(ev_i) < 1e-6))
        nnz_i = int(np.sum(np.abs(ev_i) < 1e-4))
        nn_i = int(np.sum(ev_i < -1e-6))
        print(f"  Min #{rank+1}: V={V_i:.10f}, zero={nz_i}, near-zero={nnz_i}, "
              f"neg={nn_i}, dim_vac={nz_i-1}")

    # ═══════════════════════════════════════════════════════════════
    # PART 6: SU(3)_gen orbit analysis
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 6: SU(3)_gen Orbit at Global Minimum")
    print(f"{'='*70}", flush=True)

    orbit_dim, tangent_mat, sv_orbit = su3_gen_orbit_dimension(
        D_matrices, theta_star, n_total, n48)

    print(f"  SU(3)_gen generators: 8")
    print(f"  Orbit dimension: {orbit_dim}")
    print(f"  Residual symmetry: dim = {8 - orbit_dim}")
    print(f"  Tangent map singular values:")
    for i, s in enumerate(sv_orbit):
        print(f"    σ_{i} = {s:.10f}")

    # Check if orbit directions lie in Hessian null space
    if orbit_dim > 0:
        _, _, Vt_orbit = np.linalg.svd(tangent_mat)
        orbit_dirs = Vt_orbit[:orbit_dim]

        zero_mask = np.abs(evals_c_full) < 1e-4
        zero_evecs = evecs_c_full[:, zero_mask]

        if zero_evecs.shape[1] > 0:
            overlap = orbit_dirs @ zero_evecs
            svs = np.linalg.svd(overlap, compute_uv=False)
            n_in = int(np.sum(svs > 0.99))
            print(f"\n  Orbit ↔ Hessian null space:")
            print(f"    Orbit dim: {orbit_dim}")
            print(f"    Null space dim: {zero_evecs.shape[1]}")
            print(f"    Overlap SVs: {[f'{s:.4f}' for s in svs[:min(orbit_dim, 8)]]}")
            print(f"    # orbit dirs in null space: {n_in}/{orbit_dim}")
        else:
            print(f"  No Hessian null directions to compare against")

    # ═══════════════════════════════════════════════════════════════
    # PART 7: Higgs subspace slice
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 7: Higgs Subspace Analysis")
    print(f"{'='*70}", flush=True)

    try:
        from three_gen_orderone_v1 import build_3gen_q48, build_3gen_representation
        _, _, qp48, qt, cl_origin, J, gamma, j_map = build_3gen_q48(args.seed)
        rep, triplets = build_3gen_representation(
            n48, n_total, qp48, qt, cl_origin, J, gamma, j_map)
        J_inv = J.T

        # Build Higgs directions via commutator method at the minimum
        D_star = build_D(D_matrices, theta_star)
        H_gens = [rep['I_H'], rep['sigma1'], rep['sigma2'], rep['sigma3']]

        higgs_vecs = []
        for q1 in H_gens:
            for q2 in H_gens:
                C = D_star @ q2 - q2 @ D_star
                A = q1 @ C
                A_sym = A + J @ A @ J_inv
                if np.linalg.norm(A_sym, 'fro') > 1e-12:
                    proj = B_flat @ A_sym.T.ravel().real
                    higgs_vecs.append(proj)

        if higgs_vecs:
            hmat = np.array(higgs_vecs)
            _, Sh, Vth = np.linalg.svd(hmat, full_matrices=False)
            h_rank = int(np.sum(Sh > 1e-10 * Sh[0]))
            h_dirs = Vth[:h_rank]
            print(f"  Higgs subspace: {h_rank} dimensions")

            # Mexican hat scan
            print(f"\n  Radial scan along Higgs directions from θ*:")
            phi_range = np.linspace(-2, 2, 101)
            for h in range(h_rank):
                V_scan = []
                for phi in phi_range:
                    th = theta_star + phi * h_dirs[h]
                    th /= np.linalg.norm(th)
                    V_scan.append(compute_V(D_matrices, th))
                V_scan = np.array(V_scan)
                i_min = np.argmin(V_scan)
                depth = V_scan.max() - V_scan.min()
                print(f"    H_{h}: V∈[{V_scan.min():.8f}, {V_scan.max():.8f}], "
                      f"min at φ={phi_range[i_min]:.2f}, depth={depth:.8f}")

            # Higgs ↔ null space overlap
            zero_mask_tight = np.abs(evals_c_full) < 1e-6
            zero_evecs_tight = evecs_c_full[:, zero_mask_tight]
            if zero_evecs_tight.shape[1] > 0 and h_rank > 0:
                olap = h_dirs @ zero_evecs_tight
                svs_h = np.linalg.svd(olap, compute_uv=False)
                print(f"\n  Higgs ↔ null space:")
                print(f"    Higgs dim: {h_rank}, Null dim: {zero_evecs_tight.shape[1]}")
                print(f"    SVs: {[f'{s:.4f}' for s in svs_h[:h_rank]]}")
        else:
            print(f"  No Higgs directions found")
    except Exception as e:
        print(f"  Higgs analysis failed: {e}")

    # ═══════════════════════════════════════════════════════════════
    # PART 8: Physical parameter counting
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  PART 8: Parameter Counting")
    print(f"{'='*70}")

    print(f"\n  D_F space: {dim_DF} real directions")
    print(f"  V = Tr(D⁴): quartic, degree 4")
    print(f"  On S^{dim_DF-1}: V has critical points")
    print(f"")
    print(f"  Vacuum submanifold: dim = {vacuum_dim_strict} (strict) / {vacuum_dim_relaxed} (relaxed)")
    print(f"  SU(3)_gen orbit: dim = {orbit_dim}")
    if orbit_dim <= vacuum_dim_strict:
        phys_strict = vacuum_dim_strict - orbit_dim
        print(f"  Physical params (strict): {vacuum_dim_strict} - {orbit_dim} = {phys_strict}")
    if orbit_dim <= vacuum_dim_relaxed:
        phys_relaxed = vacuum_dim_relaxed - orbit_dim
        print(f"  Physical params (relaxed): {vacuum_dim_relaxed} - {orbit_dim} = {phys_relaxed}")

    print(f"\n  SM quark sector: ~13 parameters")
    print(f"    6 masses + 3 CKM angles + 1 CP phase + 1 vev + 1 m_H + 1 α_s")
    print(f"")
    print(f"  Landscape anisotropy: V_max/V_min = {V_max_global/V_star:.6f}")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")

    print(f"""
  D_F landscape: {dim_DF} real parameters on ℂ^{n_total}
  Potential V(θ) = Tr(D⁴), quartic homogeneous on S^{dim_DF-1}
  a₂ = Tr(D²) rigid (S97) → V starts at a₄

  V_min  = {V_star:.12f}
  V_max  = {V_max_global:.12f}
  Ratio  = {V_max_global/V_star:.6f}

  Constrained Hessian at minimum:
    Zero (|λ|<1e-6):      {n_zero}  (1 radial + {vacuum_dim_strict} flat)
    Near-zero (|λ|<1e-4): {n_near_zero}
    Positive:             {n_pos}
    Negative:             {n_neg}

  ★ Vacuum submanifold dim = {vacuum_dim_strict} (strict) / {vacuum_dim_relaxed} (relaxed)

  SU(3)_gen orbit dim = {orbit_dim}
  Goldstone modes = {orbit_dim}
  Physical vacuum params = {vacuum_dim_strict - orbit_dim if orbit_dim <= vacuum_dim_strict else 'N/A'} (strict)

  Hessian distinct eigenvalues at uniform: {len(distinct)}
""")


if __name__ == '__main__':
    main()
