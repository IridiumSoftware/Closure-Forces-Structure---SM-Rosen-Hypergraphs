#!/usr/bin/env python3
"""
g3_session4_higgs_mass_v1.py — Higgs mass matrix, quartic tensor, VEV

Computes:
  1. Quadratic mass matrix M²_{ij} = Tr(D_i D_j) on the 4-dim Higgs subspace
  2. Full quartic tensor λ_{ijkl} = Tr(D_i D_j D_k D_l)
  3. Higgs potential V(φ) with background D_F: Tr((D_bg + Σ φ_i H_i)²), Tr((...)⁴)
  4. VEV from potential minimization
  5. Mass eigenvalues at the VEV → physical Higgs mass

Uses cached D_F basis.

Usage:
  python3 g3_session4_higgs_mass_v1.py [--seed S]
"""

import numpy as np
import argparse
import os
from collections import defaultdict
from three_gen_orderone_v1 import build_3gen_q48, build_3gen_representation


def b2m(vec, conj_idx, orig_idx, n_total):
    M = vec.reshape(len(conj_idx), len(orig_idx))
    D = np.zeros((n_total, n_total), dtype=np.complex128)
    D[np.ix_(conj_idx, orig_idx)] = M
    D[np.ix_(orig_idx, conj_idx)] = M.T
    return D


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("="*60)
    print("  G3 Session 4: Higgs Mass Matrix and VEV")
    print("="*60)

    # Setup
    n48, n_total, qp48, qt, cl_origin, J, gamma, j_map = build_3gen_q48(args.seed)
    n_gen = 3
    rep, triplets = build_3gen_representation(n48, n_total, qp48, qt, cl_origin, J, gamma, j_map)

    data = np.load(f'_df_basis_cache_seed{args.seed}.npz')
    final_basis = data['basis']; orig_idx = data['orig_idx']
    conj_idx = data['conj_idx']; dim_DF = int(data['dim_DF'])
    J_inv = J.T

    D_matrices = [b2m(final_basis[k], conj_idx, orig_idx, n_total) for k in range(dim_DF)]

    # Representative D₀
    D0 = sum(D_matrices) / len(D_matrices)
    D0 /= np.linalg.norm(D0, 'fro')

    # Reconstruct Higgs basis (J-symmetrised, from Session 3)
    H_gens = [rep['I_H'], rep['sigma1'], rep['sigma2'], rep['sigma3']]
    higgs_vecs = []
    for q1 in H_gens:
        for q2 in H_gens:
            C = D0 @ q2 - q2 @ D0
            A = q1 @ C
            A_sym = A + J @ A @ J_inv
            if np.linalg.norm(A_sym, 'fro') > 1e-12:
                higgs_vecs.append(A_sym[np.ix_(conj_idx, orig_idx)].real.flatten())

    U_h, S_h, Vt_h = np.linalg.svd(np.array(higgs_vecs), full_matrices=False)
    higgs_rank = int(np.sum(S_h > 1e-10 * S_h[0]))
    higgs_param_basis = Vt_h[:higgs_rank]  # higgs_rank × dim_M (off-diag param space)
    print(f"\n  Higgs subspace: {higgs_rank} dimensions")

    # Build Higgs direction matrices H_i on ℂ^{n_total}
    H_matrices = []
    for i in range(higgs_rank):
        H_i = b2m(higgs_param_basis[i], conj_idx, orig_idx, n_total)
        H_i /= np.linalg.norm(H_i, 'fro')  # normalise
        H_matrices.append(H_i)

    # ═══════════════════════════════════════════════════════════
    # PART 1: Quadratic mass matrix M²_{ij} = Tr(H_i H_j)
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 1: Quadratic Mass Matrix")
    print(f"{'='*60}")

    M2 = np.zeros((higgs_rank, higgs_rank))
    for i in range(higgs_rank):
        for j in range(higgs_rank):
            M2[i, j] = np.trace(H_matrices[i] @ H_matrices[j]).real

    print(f"\n  M²_{'{ij}'} = Tr(H_i H_j):")
    for i in range(higgs_rank):
        row = ' '.join(f'{M2[i,j]:8.5f}' for j in range(higgs_rank))
        print(f"    [{row}]")

    eigvals_M2, eigvecs_M2 = np.linalg.eigh(M2)
    print(f"\n  Eigenvalues of M²: {[f'{e:.6f}' for e in eigvals_M2]}")
    print(f"  Condition number: {eigvals_M2[-1]/eigvals_M2[0]:.2f}")

    # ═══════════════════════════════════════════════════════════
    # PART 2: Quartic tensor λ_{ijkl} = Tr(H_i H_j H_k H_l)
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 2: Quartic Coupling Tensor")
    print(f"{'='*60}")

    # Full tensor is 4⁴ = 256 components, but symmetry reduces this
    # λ_{ijkl} is symmetric under cyclic permutation of (i,j,k,l) due to trace cyclicity
    lam = np.zeros((higgs_rank, higgs_rank, higgs_rank, higgs_rank))
    for i in range(higgs_rank):
        for j in range(higgs_rank):
            HiHj = H_matrices[i] @ H_matrices[j]
            for k in range(higgs_rank):
                for l in range(higgs_rank):
                    lam[i,j,k,l] = np.trace(HiHj @ H_matrices[k] @ H_matrices[l]).real

    # The physically relevant quartic is the fully symmetrised version
    lam_sym = np.zeros_like(lam)
    from itertools import permutations
    for i in range(higgs_rank):
        for j in range(higgs_rank):
            for k in range(higgs_rank):
                for l in range(higgs_rank):
                    perms = set(permutations([i,j,k,l]))
                    lam_sym[i,j,k,l] = np.mean([lam[p] for p in perms])

    # Diagonal quartics λ_{iiii}
    print(f"\n  Diagonal quartics λ_{{iiii}} (self-coupling):")
    for i in range(higgs_rank):
        print(f"    λ_{{{i}{i}{i}{i}}} = {lam_sym[i,i,i,i]:.6f}")

    # Off-diagonal quartics λ_{iijj} (cross-coupling)
    print(f"\n  Cross-couplings λ_{{iijj}}:")
    for i in range(higgs_rank):
        for j in range(i+1, higgs_rank):
            print(f"    λ_{{{i}{i}{j}{j}}} = {lam_sym[i,i,j,j]:.6f}")

    # ═══════════════════════════════════════════════════════════
    # PART 3: Higgs potential with background
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 3: Higgs Potential V(φ) with Background")
    print(f"{'='*60}")

    # Build a background D_F from the Yukawa sector (orthogonal to Higgs)
    # D_bg = D₀ projected OUT of the Higgs subspace
    D0_param = np.zeros(len(conj_idx) * len(orig_idx))
    for k in range(dim_DF):
        D0_param += final_basis[k]
    D0_param /= np.linalg.norm(D0_param)

    # Project out Higgs component
    higgs_proj = higgs_param_basis.T @ (higgs_param_basis @ D0_param)
    D_bg_param = D0_param - higgs_proj
    D_bg_param /= np.linalg.norm(D_bg_param)
    D_bg = b2m(D_bg_param, conj_idx, orig_idx, n_total)

    # Scale D_bg to have Tr(D_bg²) = 1
    tr_bg = np.trace(D_bg @ D_bg).real
    D_bg /= np.sqrt(tr_bg)

    print(f"  Background D_bg: Tr(D²) = {np.trace(D_bg @ D_bg).real:.6f}")
    print(f"  Higgs content of D_bg: {np.linalg.norm(higgs_proj)**2/np.linalg.norm(D0_param)**2:.6f} (should be ~0)")

    # Full potential: V(φ) = Tr(f((D_bg + Σ φ_i H_i)²/Λ²))
    # At a₂ level: Tr((D_bg + Σ φ_i H_i)²) = Tr(D_bg²) + 2Σ φ_i Tr(D_bg H_i) + Σ_{ij} φ_i φ_j Tr(H_i H_j)
    # At a₄ level: Tr((D_bg + Σ φ_i H_i)⁴) = more complex

    # Cross terms Tr(D_bg H_i)
    cross_a2 = np.array([np.trace(D_bg @ H_matrices[i]).real for i in range(higgs_rank)])
    print(f"\n  a₂ cross terms Tr(D_bg H_i): {[f'{c:.6e}' for c in cross_a2]}")

    # Scan along the first Higgs direction with background
    phi_range = np.linspace(-5, 5, 201)
    V_a2 = np.zeros_like(phi_range)
    V_a4 = np.zeros_like(phi_range)

    for ip, phi in enumerate(phi_range):
        D_total = D_bg + phi * H_matrices[0]
        D2 = D_total @ D_total
        V_a2[ip] = np.trace(D2).real
        V_a4[ip] = np.trace(D2 @ D2).real

    # The potential is V(φ) = -f₂/2Λ² · a₂(φ) + f₄/Λ⁴ · a₄(φ)
    # Since we don't know f₂, f₄, Λ, work with dimensionless ratios
    # V(φ) ∝ -α · a₂(φ) + a₄(φ) where α = f₂ Λ²/(2f₄)

    # Find the minimum of a₄ - α a₂ for various α
    print(f"\n  Potential scan along H₀ direction:")
    print(f"    a₂(0) = {V_a2[100]:.4f}, a₂ range: {V_a2.min():.4f}–{V_a2.max():.4f}")
    print(f"    a₄(0) = {V_a4[100]:.4f}, a₄ range: {V_a4.min():.4f}–{V_a4.max():.4f}")

    # Check a₂ curvature
    a2_coeff = (V_a2[101] - 2*V_a2[100] + V_a2[99]) / (phi_range[1] - phi_range[0])**2
    a4_coeff = (V_a4[101] - 2*V_a4[100] + V_a4[99]) / (phi_range[1] - phi_range[0])**2
    print(f"    d²a₂/dφ² at φ=0: {a2_coeff:.6f} (= 2·Tr(H₀²) = {2*M2[0,0]:.6f})")
    print(f"    d²a₄/dφ² at φ=0: {a4_coeff:.4f}")

    # ═══════════════════════════════════════════════════════════
    # PART 4: Mass eigenvalues
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 4: Higgs Mass Eigenvalues")
    print(f"{'='*60}")

    # The physical mass matrix at the VEV is:
    # (m²)_{ij} = ∂²V/∂φ_i ∂φ_j |_{VEV}
    #
    # For V(φ) = -μ² Σ M²_{ij} φ_i φ_j + λ Σ λ_{ijkl} φ_i φ_j φ_k φ_l
    # the VEV minimises V. For the isotropic case (M² = I, λ_{ijkl} = λ δ pairs),
    # the VEV is along any direction with |φ| = μ/√(2λ).
    #
    # More general: the mass matrix at VEV φ₀ is:
    # m²_{ij} = -2μ² M²_{ij} + 12λ Σ_{kl} λ_{ijkl} (φ₀)_k (φ₀)_l
    #
    # For now, compute the effective mass matrix from the quartic structure

    # The "Hessian" of a₄ at φ=0 (the quartic contribution to the mass)
    # ∂²Tr(D⁴)/∂φ_i∂φ_j |_{φ=0} evaluated with D = D_bg + Σ φ_i H_i
    hess_a4 = np.zeros((higgs_rank, higgs_rank))
    eps = 0.01
    for i in range(higgs_rank):
        for j in range(i, higgs_rank):
            # ∂²a₄/∂φ_i∂φ_j by finite difference
            def a4(phis):
                D = D_bg.copy()
                for k, ph in enumerate(phis):
                    D = D + ph * H_matrices[k]
                D2 = D @ D
                return np.trace(D2 @ D2).real

            phi0 = np.zeros(higgs_rank)
            phi_pp = phi0.copy(); phi_pp[i] += eps; phi_pp[j] += eps
            phi_pm = phi0.copy(); phi_pm[i] += eps; phi_pm[j] -= eps
            phi_mp = phi0.copy(); phi_mp[i] -= eps; phi_mp[j] += eps
            phi_mm = phi0.copy(); phi_mm[i] -= eps; phi_mm[j] -= eps

            hess_a4[i,j] = (a4(phi_pp) - a4(phi_pm) - a4(phi_mp) + a4(phi_mm)) / (4*eps**2)
            hess_a4[j,i] = hess_a4[i,j]

    print(f"\n  Hessian of a₄ at φ=0 (with background):")
    for i in range(higgs_rank):
        row = ' '.join(f'{hess_a4[i,j]:10.4f}' for j in range(higgs_rank))
        print(f"    [{row}]")

    eigvals_hess, eigvecs_hess = np.linalg.eigh(hess_a4)
    print(f"\n  Eigenvalues of ∂²a₄/∂φ²:")
    for i, ev in enumerate(eigvals_hess):
        print(f"    λ_{i} = {ev:.6f}")

    # The full mass matrix combines a₂ and a₄ contributions:
    # m² = -α · ∂²a₂/∂φ² + ∂²a₄/∂φ²
    # where α = f₂Λ²/(2f₄) > 0 determines the balance

    hess_a2 = 2 * M2  # ∂²a₂/∂φ_i∂φ_j = 2 M²_{ij}

    # For what value of α does SSB occur?
    # SSB when the mass matrix has a negative eigenvalue at φ=0
    # m²(α) = -α · hess_a2 + hess_a4
    # The critical α is when det(m²) = 0

    print(f"\n  SSB analysis:")
    print(f"    Mass matrix: m² = -α · (2M²) + ∂²a₄/∂φ²")
    print(f"    Finding critical α for SSB...")

    alphas = np.linspace(0, 0.5, 500)
    for alpha in alphas:
        mass_matrix = -alpha * hess_a2 + hess_a4
        evals = np.linalg.eigvalsh(mass_matrix)
        if evals[0] < 0:
            print(f"    Critical α ≈ {alpha:.4f} (first negative eigenvalue)")
            print(f"    At α = {alpha:.4f}: eigenvalues = {[f'{e:.4f}' for e in evals]}")

            # At slightly above critical, how many negative eigenvalues?
            mass_above = -(alpha + 0.01) * hess_a2 + hess_a4
            evals_above = np.linalg.eigvalsh(mass_above)
            n_neg = np.sum(evals_above < 0)
            print(f"    At α = {alpha+0.01:.4f}: {n_neg} negative eigenvalue(s)")
            print(f"      eigenvalues = {[f'{e:.4f}' for e in evals_above]}")

            # SM expectation: 1 negative eigenvalue → 1 direction breaks symmetry
            # (the physical Higgs direction), 3 remain positive (Goldstones become
            # massless only at the VEV, not at φ=0)
            break
    else:
        print(f"    No SSB in range α ∈ [0, 0.5]")
        # Try larger range
        for alpha in np.linspace(0.5, 50, 5000):
            mass_matrix = -alpha * hess_a2 + hess_a4
            evals = np.linalg.eigvalsh(mass_matrix)
            if evals[0] < 0:
                print(f"    Critical α ≈ {alpha:.4f}")
                print(f"    eigenvalues = {[f'{e:.4f}' for e in evals]}")
                n_neg = np.sum(evals < 0)
                print(f"    {n_neg} negative eigenvalue(s)")
                break

    # ═══════════════════════════════════════════════════════════
    # PART 5: Ratios (scale-independent)
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 5: Scale-Independent Ratios")
    print(f"{'='*60}")

    # The ratio that determines the Higgs mass (at unification scale):
    # m_H² / v² = 2λ where λ is the quartic coupling at the VEV
    # In our framework: λ_{eff} = diagonal quartic / (M²)²

    for i in range(higgs_rank):
        ratio = lam_sym[i,i,i,i] / M2[i,i]**2 if M2[i,i] > 0 else 0
        print(f"  H_{i}: λ_{{iiii}}/M⁴_{{ii}} = {ratio:.6f}")

    # Overall quartic / quadratic ratio
    tr_lam = sum(lam_sym[i,i,i,i] for i in range(higgs_rank))
    tr_M2 = np.trace(M2)
    print(f"\n  Σ λ_{{iiii}} / (Tr M²)² = {tr_lam / tr_M2**2:.6f}")
    print(f"  Mean λ/μ² = {np.mean([lam_sym[i,i,i,i]/M2[i,i] for i in range(higgs_rank)]):.6f}")

    # CCM comparison
    # In CCM (2012): m_H = √(2λ) v, at unification scale m_H/m_W ≈ √(8λ/g²)
    # Their value: m_H ≈ 170 GeV (tree level, before RG)
    # Our mean λ/μ² gives a relative self-coupling strength

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    print(f"""
  Higgs sector: {higgs_rank} dimensions (SM complex doublet)

  Mass matrix M²_{{ij}} = Tr(H_i H_j):
    Eigenvalues: {[f'{e:.4f}' for e in eigvals_M2]}
    Condition number: {eigvals_M2[-1]/eigvals_M2[0]:.2f}

  Quartic self-couplings λ_{{iiii}}:
    {[f'{lam_sym[i,i,i,i]:.6f}' for i in range(higgs_rank)]}

  Hessian eigenvalues (a₄ at φ=0 with background):
    {[f'{e:.4f}' for e in eigvals_hess]}

  Scale-independent:
    Mean λ/μ² = {np.mean([lam_sym[i,i,i,i]/M2[i,i] for i in range(higgs_rank)]):.6f}
""")


if __name__ == '__main__':
    main()
