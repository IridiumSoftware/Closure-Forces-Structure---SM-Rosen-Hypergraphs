#!/usr/bin/env python3
"""
g3_higgs_c_factor_v1.py — Does the ℂ factor split the Higgs 2+2?

On ℂ¹⁴⁴ (quarks only), Y_C is trivial → all Higgs directions come from ℍ.
On ℂ¹⁶⁸ (with leptons, Connes rep), Y_C acts on νR(+1), eR(-1).
The inner fluctuation [D, Y_C] generates new lepton-sector Higgs directions.

Test: does the ℂ-factor projection f_ℂ(H_i) sort the 2+2 pairing?

Method:
  1. Build ℂ¹⁶⁸ Higgs subspace with full A_F = ℂ ⊕ ℍ ⊕ M₃(ℂ)
  2. For each Higgs direction, compute lepton-block fraction f_ℂ
  3. Compute quartic λ_{iiii} and check if f_ℂ sorts the pairing

Usage:
  python3 g3_higgs_c_factor_v1.py [--seed S]
"""

import numpy as np
import argparse
import os
from three_gen_orderone_v1 import build_3gen_q48, build_3gen_representation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("=" * 70)
    print("  G3: Does the ℂ Factor Split the Higgs 2+2?")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # Build ℂ¹⁶⁸ with Connes representation (Session 10d setup)
    # ═══════════════════════════════════════════════════════════
    n48, n_total_q, qp48, qt, cl_origin, J_q, gamma_q, j_map_q = build_3gen_q48(args.seed)
    n_gen = 3
    rep_q, _ = build_3gen_representation(n48, n_total_q, qp48, qt, cl_origin, J_q, gamma_q, j_map_q)

    n_lep = 24; n_total = n_total_q + n_lep
    nuL = list(range(0, 3)); eL = list(range(3, 6))
    nuR = list(range(6, 9)); eR = list(range(9, 12))
    nuLc = list(range(12, 15)); eLc = list(range(15, 18))
    nuRc = list(range(18, 21)); eRc = list(range(21, 24))

    # Connes chirality + C-involution J + particle-only algebra
    gamma_lep = np.zeros(n_lep)
    for g in range(n_gen):
        gamma_lep[nuL[g]] = -1; gamma_lep[eL[g]] = -1
        gamma_lep[nuR[g]] = +1; gamma_lep[eR[g]] = +1
        gamma_lep[nuLc[g]] = +1; gamma_lep[eLc[g]] = +1
        gamma_lep[nuRc[g]] = -1; gamma_lep[eRc[g]] = -1
    gamma_full = np.concatenate([gamma_q, gamma_lep])

    J_C_lep = np.zeros((n_lep, n_lep))
    for g in range(n_gen):
        J_C_lep[nuLc[g], nuL[g]] = 1; J_C_lep[nuL[g], nuLc[g]] = 1
        J_C_lep[eLc[g], eL[g]] = 1; J_C_lep[eL[g], eLc[g]] = 1
        J_C_lep[nuRc[g], nuR[g]] = 1; J_C_lep[nuR[g], nuRc[g]] = 1
        J_C_lep[eRc[g], eR[g]] = 1; J_C_lep[eR[g], eRc[g]] = 1
    J_full = np.zeros((n_total, n_total))
    J_full[:n_total_q, :n_total_q] = J_q
    J_full[n_total_q:, n_total_q:] = J_C_lep
    J_inv = J_full.T

    sigma1 = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    sigma2 = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    sigma3 = np.array([[1, 0], [0, -1]], dtype=np.complex128)

    rep = {}
    for gi in range(3):
        for gj in range(3):
            E = np.zeros((n_total, n_total), dtype=np.complex128)
            E[:n_total_q, :n_total_q] = rep_q[f'E_{gi}{gj}']
            if gi == gj:
                for k in range(n_lep): E[n_total_q + k, n_total_q + k] = 1.0
            rep[f'E_{gi}{gj}'] = E

    for name, sigma in [('sigma1', sigma1), ('sigma2', sigma2), ('sigma3', sigma3)]:
        S = np.zeros((n_total, n_total), dtype=np.complex128)
        S[:n_total_q, :n_total_q] = rep_q[name]
        for g in range(n_gen):
            i0, i1 = n_total_q + nuL[g], n_total_q + eL[g]
            S[i0, i0] += sigma[0, 0]; S[i0, i1] += sigma[0, 1]
            S[i1, i0] += sigma[1, 0]; S[i1, i1] += sigma[1, 1]
        rep[name] = S

    # ℂ factor: particle-only (νR=+1, eR=-1, antiparticles=0)
    Y_C = np.zeros((n_total, n_total), dtype=np.complex128)
    for g in range(n_gen):
        Y_C[n_total_q + nuR[g], n_total_q + nuR[g]] = 1
        Y_C[n_total_q + eR[g], n_total_q + eR[g]] = -1
    rep['Y_C'] = Y_C

    # Also need I_H (identity on weak doublet, for inner fluctuation basis)
    I_H = np.zeros((n_total, n_total), dtype=np.complex128)
    tier_B = [c for c in range(n48) if qt.get(c) == 'B']
    for v in tier_B:
        for g in range(n_gen): I_H[v * n_gen + g, v * n_gen + g] = 1.0
    # Lepton doublet
    for g in range(n_gen):
        I_H[n_total_q + nuL[g], n_total_q + nuL[g]] = 1.0
        I_H[n_total_q + eL[g], n_total_q + eL[g]] = 1.0
    rep['I_H'] = I_H

    gen_names = [f'E_{i}{j}' for i in range(3) for j in range(3)] + \
                ['sigma1', 'sigma2', 'sigma3', 'Y_C']
    opp = {name: J_full @ rep[name].conj() @ J_inv for name in gen_names}

    orig_idx = np.array([i for i in range(n_total) if gamma_full[i] > 0])
    conj_idx = np.array([i for i in range(n_total) if gamma_full[i] < 0])
    n_orig = len(orig_idx); n_conj = len(conj_idx)

    # ═══════════════════════════════════════════════════════════
    # Compute D_F basis on ℂ¹⁶⁸ (order-one kernel)
    # ═══════════════════════════════════════════════════════════
    print(f"\n  Computing order-one kernel on ℂ^{n_total}...")
    dim_M = n_conj * n_orig
    basis = np.eye(dim_M); current_dim = dim_M
    for ai, a_name in enumerate(gen_names):
        pi_a = rep[a_name]
        for b_name in gen_names:
            if current_dim == 0: break
            violations = []
            for k in range(current_dim):
                M = basis[k].reshape(n_conj, n_orig)
                D = np.zeros((n_total, n_total), dtype=np.complex128)
                D[np.ix_(conj_idx, orig_idx)] = M
                D[np.ix_(orig_idx, conj_idx)] = M.T
                comm = D @ pi_a - pi_a @ D
                dcomm = comm @ opp[b_name] - opp[b_name] @ comm
                violations.append(dcomm.real.flatten())
            V = np.array(violations)
            if np.max(np.abs(V)) < 1e-12: continue
            G = V @ V.T; eigvals, eigvecs = np.linalg.eigh(G)
            ker = eigvals < 1e-12; nd = int(np.sum(ker))
            if nd < current_dim and nd > 0:
                basis = eigvecs[:, ker].T @ basis; current_dim = basis.shape[0]
            elif nd == 0: current_dim = 0; break
        if current_dim == 0: break
        if (ai + 1) % 4 == 0: print(f"    gen {ai + 1}/{len(gen_names)}: dim={current_dim}")

    print(f"  Order-one kernel: {current_dim}")

    # JD=DJ
    jd_rows = []
    for k in range(current_dim):
        M = basis[k].reshape(n_conj, n_orig)
        D_k = np.zeros((n_total, n_total), dtype=np.complex128)
        D_k[np.ix_(conj_idx, orig_idx)] = M
        D_k[np.ix_(orig_idx, conj_idx)] = M.T
        jd_rows.append((J_full @ D_k - D_k @ J_full).real.flatten())
    JD = np.array(jd_rows); G_jd = JD @ JD.T
    ev, ec = np.linalg.eigh(G_jd); km = ev < 1e-12
    df_basis = ec[:, km].T @ basis
    dim_df = df_basis.shape[0]
    print(f"  JD=DJ: {dim_df}")

    # Build D_F matrices
    def vec_to_D(v):
        M = v.reshape(n_conj, n_orig)
        D = np.zeros((n_total, n_total), dtype=np.complex128)
        D[np.ix_(conj_idx, orig_idx)] = M
        D[np.ix_(orig_idx, conj_idx)] = M.T
        return D

    D_matrices = [vec_to_D(df_basis[k]) for k in range(dim_df)]

    # ═══════════════════════════════════════════════════════════
    # Higgs subspace: inner fluctuations with FULL A_F
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  Higgs Subspace (Inner Fluctuations with ℂ ⊕ ℍ ⊕ M₃)")
    print("=" * 70)

    # Reference D₀
    D0 = np.zeros((n_total, n_total), dtype=np.complex128)
    for D_k in D_matrices:
        D0 += D_k
    D0 /= max(np.linalg.norm(D0, 'fro'), 1e-15)

    # ALL algebra generators (including Y_C!)
    all_gens = ['I_H', 'sigma1', 'sigma2', 'sigma3', 'Y_C']
    all_gen_mats = [rep[name] for name in all_gens]

    # Commutators [D₀, π(a)] for each generator
    print(f"\n  Commutators [D₀, π(a)]:")
    comms = {}
    for name, gen in zip(all_gens, all_gen_mats):
        C = D0 @ gen - gen @ D0
        norm = np.linalg.norm(C, 'fro')
        comms[name] = C
        lepton_norm = np.linalg.norm(C[n_total_q:, n_total_q:], 'fro')
        quark_norm = np.linalg.norm(C[:n_total_q, :n_total_q], 'fro')
        print(f"    [D₀, {name:8s}]: ||total||={norm:.4f}  "
              f"||quark||={quark_norm:.4f}  ||lepton||={lepton_norm:.4f}")

    # Inner fluctuation space: span{π(a₁) · [D₀, π(a₂)]}
    fluct = []
    fluct_labels = []
    for a1_name, a1 in zip(all_gens, all_gen_mats):
        for a2_name in all_gens:
            A = a1 @ comms[a2_name]
            if np.linalg.norm(A, 'fro') > 1e-12:
                fluct.append(A.flatten().real)
                fluct_labels.append(f"{a1_name}·[D,{a2_name}]")

    fluct = np.array(fluct)
    _, S_f, Vt_f = np.linalg.svd(fluct, full_matrices=False)
    higgs_dim = int(np.sum(S_f > 1e-10 * S_f[0]))
    print(f"\n  Inner fluctuation dimension: {higgs_dim}")

    # Project the fluctuation matrices onto D_F basis directly
    df_full = np.array([D.flatten().real for D in D_matrices])
    fluct_in_df = []
    for i, A_flat in enumerate(fluct):
        # Project A onto span of D_F matrices
        coeffs = np.array([np.dot(A_flat, df_full[k]) for k in range(dim_df)])
        norm_A = np.linalg.norm(A_flat)
        proj_norm = np.linalg.norm(df_full.T @ coeffs)
        if norm_A > 1e-12:
            fluct_in_df.append(coeffs)

    if not fluct_in_df:
        print("  No fluctuation directions project onto D_F space!")
        return

    fluct_in_df = np.array(fluct_in_df)
    _, S_proj, Vt_proj = np.linalg.svd(fluct_in_df, full_matrices=False)
    n_higgs = int(np.sum(S_proj > 1e-8 * S_proj[0]))
    higgs_dirs = Vt_proj[:n_higgs]  # n_higgs × dim_df

    print(f"  Higgs directions in D_F: {n_higgs}")

    # Build Higgs D_F matrices
    higgs_Ds = []
    for k in range(n_higgs):
        D_h = np.zeros((n_total, n_total), dtype=np.complex128)
        for j in range(dim_df):
            D_h += higgs_dirs[k, j] * D_matrices[j]
        D_h /= max(np.linalg.norm(D_h, 'fro'), 1e-15)
        higgs_Ds.append(D_h)

    # ═══════════════════════════════════════════════════════════
    # f_ℂ: lepton-block fraction for each Higgs direction
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  ℂ-Factor Analysis: Lepton-Block Fraction f_ℂ")
    print("=" * 70)

    lep_idx = list(range(n_total_q, n_total))
    quark_idx = list(range(n_total_q))

    for i in range(n_higgs):
        H = higgs_Ds[i]
        total_norm2 = np.linalg.norm(H, 'fro') ** 2
        lep_norm2 = np.linalg.norm(H[n_total_q:, :], 'fro') ** 2 + \
                    np.linalg.norm(H[:, n_total_q:], 'fro') ** 2 - \
                    np.linalg.norm(H[n_total_q:, n_total_q:], 'fro') ** 2
        # Actually: just compute the lepton-lepton block + quark-lepton cross blocks
        lep_only = np.linalg.norm(H[n_total_q:, n_total_q:], 'fro') ** 2
        quark_only = np.linalg.norm(H[:n_total_q, :n_total_q], 'fro') ** 2
        cross = total_norm2 - lep_only - quark_only

        f_c = (lep_only + cross) / max(total_norm2, 1e-30)
        f_lep = lep_only / max(total_norm2, 1e-30)
        f_quark = quark_only / max(total_norm2, 1e-30)

        print(f"  H_{i}: f_quark={f_quark:.4f}  f_lepton={f_lep:.4f}  f_cross={cross/max(total_norm2,1e-30):.4f}  f_ℂ={f_c:.4f}")

    # ═══════════════════════════════════════════════════════════
    # Quartic coupling λ_{iiii}
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  Quartic Coupling λ_{iiii}")
    print("=" * 70)

    if n_higgs >= 2:
        lam_diag = []
        for i in range(n_higgs):
            H = higgs_Ds[i]
            H2 = H @ H
            lam = np.trace(H2 @ H2).real
            lam_diag.append(lam)
            print(f"  H_{i}: λ_{i}{i}{i}{i} = {lam:.6f}")

        # Mass matrix
        print(f"\n  Mass matrix M²_ij = Tr(H_i†H_j):")
        M2 = np.zeros((n_higgs, n_higgs))
        for i in range(n_higgs):
            for j in range(n_higgs):
                M2[i, j] = np.trace(higgs_Ds[i].conj().T @ higgs_Ds[j]).real
        for i in range(n_higgs):
            print(f"    [{', '.join(f'{M2[i,j]:.4f}' for j in range(n_higgs))}]")

        # σ₃ and Y_C projections
        print(f"\n  σ₃ and Y_C projections:")
        for i in range(n_higgs):
            H = higgs_Ds[i]
            s3_proj = np.trace(H.conj().T @ rep['sigma3']).real / max(np.linalg.norm(H, 'fro'), 1e-15)
            yc_proj = np.trace(H.conj().T @ Y_C).real / max(np.linalg.norm(H, 'fro'), 1e-15)
            print(f"    H_{i}: σ₃={s3_proj:.6f}  Y_C={yc_proj:.6f}")

    # ═══════════════════════════════════════════════════════════
    # Does f_ℂ sort the 2+2?
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  THE TEST: Does f_ℂ sort the quartic pairing?")
    print("=" * 70)

    if n_higgs >= 4 and len(lam_diag) >= 4:
        lam = np.array(lam_diag[:4])
        f_c_vals = []
        for i in range(4):
            H = higgs_Ds[i]
            total_norm2 = np.linalg.norm(H, 'fro') ** 2
            lep_norm2 = np.linalg.norm(H[n_total_q:, n_total_q:], 'fro') ** 2
            f_c_vals.append(lep_norm2 / max(total_norm2, 1e-30))
        f_c_arr = np.array(f_c_vals)

        # Sort by quartic
        sorted_by_lam = np.argsort(lam)
        pair_low = sorted_by_lam[:2]   # lower λ pair
        pair_high = sorted_by_lam[2:]  # higher λ pair

        f_c_low = np.mean(f_c_arr[pair_low])
        f_c_high = np.mean(f_c_arr[pair_high])

        print(f"\n  Lower-λ pair (H_{pair_low[0]}, H_{pair_low[1]}): "
              f"λ̄={np.mean(lam[pair_low]):.6f}, f̄_ℂ={f_c_low:.6f}")
        print(f"  Higher-λ pair (H_{pair_high[0]}, H_{pair_high[1]}): "
              f"λ̄={np.mean(lam[pair_high]):.6f}, f̄_ℂ={f_c_high:.6f}")

        if abs(f_c_low - f_c_high) > 0.01:
            print(f"\n  ★ f_ℂ SEPARATES the pairs! Δf_ℂ = {abs(f_c_low - f_c_high):.4f}")
            if f_c_low > f_c_high:
                print(f"  → Hypercharge-aligned (more lepton content) = weaker quartic")
                print(f"  → The ℂ factor dilutes the quartic through the lepton sector")
            else:
                print(f"  → Hypercharge-aligned (more lepton content) = stronger quartic")
                print(f"  → The ℂ factor concentrates the quartic")

            # Check ratio
            if np.mean(lam[pair_high]) > 1e-10:
                lam_ratio = np.mean(lam[pair_low]) / np.mean(lam[pair_high])
                print(f"\n  λ ratio = {lam_ratio:.4f}")
                print(f"  SM sin²θ_W = 0.231")
                print(f"  Correlation: {'suggestive' if abs(lam_ratio - 0.231) < 0.1 else 'no direct match'}")
        else:
            print(f"\n  f_ℂ does NOT separate the pairs (Δf_ℂ = {abs(f_c_low - f_c_high):.4f})")
            print(f"  The ℂ factor is not the pairing mechanism")
    elif n_higgs < 4:
        print(f"\n  Only {n_higgs} Higgs directions (need 4 for pairing analysis)")
        print(f"  Checking f_ℂ distribution:")
        for i in range(n_higgs):
            H = higgs_Ds[i]
            total = np.linalg.norm(H, 'fro') ** 2
            lep = np.linalg.norm(H[n_total_q:, n_total_q:], 'fro') ** 2
            print(f"    H_{i}: f_ℂ = {lep/max(total,1e-30):.6f}, λ = {lam_diag[i]:.6f}")


if __name__ == '__main__':
    main()
