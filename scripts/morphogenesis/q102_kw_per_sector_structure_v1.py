#!/usr/bin/env python3
"""
q102_kw_per_sector_structure_v1.py — per-sector (J=±1) mode architecture.

S187 established K_ω = K_+ ⊕ K_- on the J = ±1 eigenspaces.  S184
established the family-wide two-cluster architecture (slow modes
destructively-balanced, fast modes gravity-dominated constructive).

This script asks: does each J-sector INHERIT the two-cluster
architecture, or is the gravity-dominated top cluster a property of
only one sector?

Method:
  1. Build Q102, compute D = L + α·D_F, K_ω = D²
  2. Diagonalise J → ±1 eigenspaces (49 + 49 dims per S187)
  3. Restrict K_ω to each sector → K_+, K_-
  4. Diagonalise each: spec(K_+), spec(K_-) and per-sector eigenvectors
  5. For each eigenvector in each sector, compute L²/DF²/cross diagonal
     content (sector-restricted)
  6. Identify per-sector spectral gaps
  7. Compare top/bottom-6 mode character per sector

Per S180 observation-only: pure linear algebra on Q102's fixed
Hilbert space.  No state evolution.

Aaron Green — May 5, 2026 — S187/S188 follow-up.
"""

import sys, time
import numpy as np

sys.path.insert(0, '.')
from quotient_landscape_autopoiesis_v1 import haar_C3, complete_edges
from q102_build_v1 import build_c_closed_quotient, build_J
from g6a_multiscale_spectral_v1 import build_laplacian, build_sample_DF


def per_sector_decomp(K_omega_sector, P_sector, L2, DF2_s, cross,
                       sector_name, sector_eigvecs):
    """For each eigenmode in this J-sector, decompose by L/DF/cross.

    sector_eigvecs is in the sector's local basis (n_sector × n_sector);
    we lift to the full n-dim space via P_sector @ sector_eigvecs to
    compute the operator quadratic forms.
    """
    eigvals, sec_vec = np.linalg.eigh(K_omega_sector)
    order = np.argsort(eigvals)
    eigvals = eigvals[order]
    sec_vec = sec_vec[:, order]

    # Lift sector eigenvectors to full Hilbert space
    full_vec = P_sector @ sec_vec  # shape (n, n_sector)

    L2_diag    = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, L2,    full_vec).real
    DF2_diag   = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, DF2_s, full_vec).real
    cross_diag = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, cross, full_vec).real

    diag_sum = L2_diag + DF2_diag
    L_frac    = L2_diag  / np.maximum(diag_sum, 1e-30)
    DF_frac   = DF2_diag / np.maximum(diag_sum, 1e-30)
    cross_rel = cross_diag / np.maximum(diag_sum, 1e-30)

    return eigvals, L_frac, DF_frac, cross_rel


def report_sector(name, eigvals, L_frac, DF_frac, cross_rel, n_top=6):
    n = len(eigvals)
    gaps = np.diff(eigvals)
    gap_idx = int(np.argmax(gaps)) if len(gaps) > 0 else -1
    gap_max = float(gaps[gap_idx]) if gap_idx >= 0 else 0.0

    print(f"\n  {name}: {n} eigenvalues")
    print(f"    range:        [{eigvals[0]:.4f}, {eigvals[-1]:.4f}]")
    print(f"    mean:         {eigvals.mean():.2f}")
    print(f"    median:       {np.median(eigvals):.2f}")
    print(f"    largest gap:  Δ_max = {gap_max:.2f} at idx {gap_idx} "
          f"(between λ_{gap_idx} and λ_{gap_idx+1})")

    print(f"    BOTTOM {n_top} modes (low-freq morphogenesis):")
    print(f"      {'idx':>3} {'λ':>10} {'L%':>6} {'DF%':>6} {'cross%':>8}")
    for k in range(min(n_top, n)):
        print(f"      {k:>3} {eigvals[k]:>10.4f} "
              f"{L_frac[k]*100:>5.1f}% {DF_frac[k]*100:>5.1f}% "
              f"{cross_rel[k]*100:>+7.1f}%")

    print(f"    TOP {n_top} modes (high-freq morphogenesis):")
    print(f"      {'idx':>3} {'λ':>10} {'L%':>6} {'DF%':>6} {'cross%':>8}")
    for k in range(max(0, n - n_top), n):
        print(f"      {k:>3} {eigvals[k]:>10.4f} "
              f"{L_frac[k]*100:>5.1f}% {DF_frac[k]*100:>5.1f}% "
              f"{cross_rel[k]*100:>+7.1f}%")

    # Aggregate top vs bottom
    if n >= 12:
        bot12 = (L_frac[:12].mean(), DF_frac[:12].mean(), cross_rel[:12].mean())
        top12 = (L_frac[-12:].mean(), DF_frac[-12:].mean(), cross_rel[-12:].mean())
        print(f"    AGGREGATE bot12 → top12: "
              f"L {bot12[0]*100:.1f}% → {top12[0]*100:.1f}%, "
              f"DF {bot12[1]*100:.1f}% → {top12[1]*100:.1f}%, "
              f"cross {bot12[2]*100:+.1f}% → {top12[2]*100:+.1f}%")
        return {
            'gap_max': gap_max, 'gap_idx': gap_idx,
            'bot12': bot12, 'top12': top12,
            'mean': float(eigvals.mean()),
            'min':  float(eigvals[0]), 'max': float(eigvals[-1]),
        }
    return {}


def main():
    seed = 42
    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("=" * 78)
    print("  PER-SECTOR (J=±1) mode architecture on Q102")
    print("  S187/S188 follow-up — observation-only morphogenesis")
    print("=" * 78)

    # Build Q102
    print(f"\n[build] Q102 = C(M(K_6^3))  seed={seed}")
    t0 = time.time()
    Q = build_c_closed_quotient(complete_edges(), psi_init, depth=4)
    n = Q['n_cl']
    J, _ = build_J(Q)
    L, _, _ = build_laplacian(Q)
    D_F, dim_DF, _ = build_sample_DF(Q, J)
    if D_F is None:
        print("[error] D_F failed"); return 1

    tr_L2  = float(np.trace(L @ L).real)
    tr_DF2 = float(np.trace(D_F @ D_F).real)
    alpha = float(np.sqrt(tr_L2 / tr_DF2))
    D_F_s = D_F * alpha
    D = L + D_F_s
    K_omega = D @ D
    L2 = L @ L
    DF2_s = D_F_s @ D_F_s
    cross = L @ D_F_s + D_F_s @ L
    print(f"[build] n={n}, dim_DF={dim_DF}, α={alpha:.4f}, "
          f"({time.time()-t0:.1f}s)")

    # Diagonalise J → ±1 sectors
    J_real = J.astype(np.float64)
    eig_J, vec_J = np.linalg.eigh(J_real)
    plus_mask  = eig_J > 0.5
    minus_mask = eig_J < -0.5
    P_plus  = vec_J[:, plus_mask]   # n × n_plus
    P_minus = vec_J[:, minus_mask]  # n × n_minus
    n_plus  = int(plus_mask.sum())
    n_minus = int(minus_mask.sum())
    print(f"[J-sector] J=+1: {n_plus}-dim, J=-1: {n_minus}-dim")

    # Restrict K_ω to each sector
    K_plus  = P_plus.T  @ K_omega @ P_plus
    K_minus = P_minus.T @ K_omega @ P_minus

    # Per-sector eigenstructure + sector content
    print(f"\n{'─'*78}")
    print(f"  SECTOR DECOMPOSITION")
    print(f"{'─'*78}")

    eig_p, Lf_p, DFf_p, Cr_p = per_sector_decomp(
        K_plus, P_plus, L2, DF2_s, cross, "K_+ (J=+1)", None)
    summary_p = report_sector("K_+ (J=+1, particle sector)",
                              eig_p, Lf_p, DFf_p, Cr_p)

    eig_m, Lf_m, DFf_m, Cr_m = per_sector_decomp(
        K_minus, P_minus, L2, DF2_s, cross, "K_- (J=-1)", None)
    summary_m = report_sector("K_- (J=-1, antiparticle sector)",
                              eig_m, Lf_m, DFf_m, Cr_m)

    # ──────────────────────────────────────────────────────────────────
    # Comparison: does the two-cluster architecture appear in BOTH sectors?
    # ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PER-SECTOR TWO-CLUSTER ARCHITECTURE COMPARISON")
    print(f"{'='*78}")

    print(f"\n  {'Sector':<24} {'gap_max':>10} {'gap_idx':>8} "
          f"{'bot12 L%':>9} {'top12 L%':>9} {'shift':>10}")
    print(f"  {'─'*72}")
    for nm, s in [("K_+ (J=+1, particle)",     summary_p),
                  ("K_- (J=-1, antiparticle)", summary_m)]:
        if not s: continue
        L_shift = (s['top12'][0] - s['bot12'][0]) * 100
        print(f"  {nm:<24} {s['gap_max']:>10.2f} {s['gap_idx']:>8d} "
              f"{s['bot12'][0]*100:>8.1f}% {s['top12'][0]*100:>8.1f}% "
              f"{L_shift:>+9.1f}%")

    print(f"\n  {'Sector':<24} {'bot12 cross':>12} {'top12 cross':>12} "
          f"{'shift':>10}")
    for nm, s in [("K_+ (J=+1, particle)",     summary_p),
                  ("K_- (J=-1, antiparticle)", summary_m)]:
        if not s: continue
        c_shift = (s['top12'][2] - s['bot12'][2]) * 100
        print(f"  {nm:<24} {s['bot12'][2]*100:>+11.1f}% "
              f"{s['top12'][2]*100:>+11.1f}% {c_shift:>+9.1f}%")

    print(f"\n{'='*78}")
    print(f"  INTERPRETATION")
    print(f"{'='*78}")

    # Is there a significant top-cluster post-gap structure in each sector?
    if summary_p and summary_m:
        gap_p_position = summary_p['gap_idx'] / max(n_plus - 1, 1)
        gap_m_position = summary_m['gap_idx'] / max(n_minus - 1, 1)
        top_in_p = summary_p['top12'][0] - summary_p['bot12'][0]
        top_in_m = summary_m['top12'][0] - summary_m['bot12'][0]
        print(f"""
  K_+ (J=+1, particle sector):
    spectral gap at relative position {gap_p_position:.2%}
    L-fraction shift bot12→top12: {top_in_p*100:+.1f}%
    {"two-cluster architecture PRESENT" if top_in_p > 0.15 else "two-cluster architecture WEAK or ABSENT"}

  K_- (J=-1, antiparticle sector):
    spectral gap at relative position {gap_m_position:.2%}
    L-fraction shift bot12→top12: {top_in_m*100:+.1f}%
    {"two-cluster architecture PRESENT" if top_in_m > 0.15 else "two-cluster architecture WEAK or ABSENT"}

  Per-sector reading: each J-sector carries its own spectrum and its
  own structural cluster organization.  Whether the family-wide
  two-cluster architecture (S184) is per-sector or only emerges in
  the joint K_ω depends on whether each sector independently exhibits
  the slow→fast destructive→constructive pattern.

  Critical scope per S180: pure linear algebra — restrict K_ω to
  J-sectors, diagonalise, decompose by L/DF/cross.  No dynamics.
""")


if __name__ == '__main__':
    main()
