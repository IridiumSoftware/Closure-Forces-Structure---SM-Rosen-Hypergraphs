#!/usr/bin/env python3
"""
q102_per_sector_lambda_scan_v1.py — per-sector Λ-cutoff scan.

S185 found that the joint K_ω = K_+ ⊕ K_- spectrum's cross-term
content is negative at every scanned Λ, asymptotically vanishing by
S125 at large Λ, with mode-half-turn-on at Λ_½ ≈ 19.95.  S189 then
showed the cross-term sign-flip is per-sector INTRINSIC (each sector
shifts +70 to +108% bot12→top12), while the L-dominance shift is a
joint mixing effect.

This script asks: in each J-sector individually, where is the
mode-half-turn-on Λ_½, and does the per-sector cross-term cross
zero (constructive regime) at any finite Λ?

Per S180 observation-only: linear algebra on Q102's J-decomposed
operators.  No state evolution.

Aaron Green — May 5, 2026 — S189 follow-up.
"""

import sys, time
import numpy as np

sys.path.insert(0, '.')
from quotient_landscape_autopoiesis_v1 import haar_C3, complete_edges
from q102_build_v1 import build_c_closed_quotient, build_J
from g6a_multiscale_spectral_v1 import build_laplacian, build_sample_DF


def per_sector_lambda_scan(name, eigvals, L_diag, DF_diag, cross_diag,
                            Lambdas, f):
    """Compute weighted sector contents at each Λ for one sector."""
    rows = []
    for Lam in Lambdas:
        weights = f(eigvals / (Lam**2))
        D_eff   = float(weights.sum())
        L_w     = float((weights * L_diag).sum())
        DF_w    = float((weights * DF_diag).sum())
        cross_w = float((weights * cross_diag).sum())
        diag    = L_w + DF_w
        L_frac  = L_w / max(diag, 1e-30)
        DF_frac = DF_w / max(diag, 1e-30)
        cross_rel = cross_w / max(diag, 1e-30)
        modes_on = int((weights > 0.5).sum())
        rows.append({
            'Lambda': Lam, 'D_eff': D_eff,
            'L_frac': L_frac, 'DF_frac': DF_frac, 'cross_rel': cross_rel,
            'modes_on': modes_on,
        })
    return rows


def find_zero_crossing(rows, key='cross_rel'):
    """Locate sign change of the named quantity; linear-interpolate Λ."""
    signs = np.sign([r[key] for r in rows])
    idxs = np.where(np.diff(signs) > 0)[0]
    if len(idxs) == 0: return None
    i = int(idxs[0])
    Lam_lo, Lam_hi = rows[i]['Lambda'], rows[i+1]['Lambda']
    v_lo, v_hi = rows[i][key], rows[i+1][key]
    if v_hi == v_lo: return float(Lam_lo)
    t = -v_lo / (v_hi - v_lo)
    return float(np.exp((1-t)*np.log(Lam_lo) + t*np.log(Lam_hi)))


def find_half_turn_on(rows, n_total):
    """Λ at which D_eff > n_total / 2."""
    for r in rows:
        if r['D_eff'] > n_total / 2:
            return float(r['Lambda'])
    return None


def main():
    seed = 42
    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("=" * 78)
    print("  PER-SECTOR (J=±1) Λ-SCAN on Q102")
    print("  S185 + S189 follow-up — observation-only morphogenesis")
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

    # J → ±1 sectors
    eig_J, vec_J = np.linalg.eigh(J.astype(np.float64))
    P_plus  = vec_J[:, eig_J > 0.5]
    P_minus = vec_J[:, eig_J < -0.5]
    n_plus  = P_plus.shape[1]
    n_minus = P_minus.shape[1]
    print(f"[J-sector] J=+1: {n_plus}-dim, J=-1: {n_minus}-dim")

    # Per-sector eigendecomposition + projection of mode quadratic forms
    def sector_data(P_sec, label):
        K_sec = P_sec.T @ K_omega @ P_sec
        eigvals_sec, sec_vec = np.linalg.eigh(K_sec)
        order = np.argsort(eigvals_sec)
        eigvals_sec = eigvals_sec[order]
        sec_vec = sec_vec[:, order]
        full_vec = P_sec @ sec_vec
        L_diag  = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, L2,    full_vec).real
        DF_diag = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, DF2_s, full_vec).real
        C_diag  = np.einsum('ij,jk,ki->i',
                            full_vec.conj().T, cross, full_vec).real
        print(f"  {label}: spec range [{eigvals_sec[0]:.4f}, "
              f"{eigvals_sec[-1]:.4f}], mean={eigvals_sec.mean():.2f}")
        return eigvals_sec, L_diag, DF_diag, C_diag

    print(f"\n[sectors]")
    eig_p, Lp, DFp, Cp = sector_data(P_plus, "K_+ (J=+1)")
    eig_m, Lm, DFm, Cm = sector_data(P_minus, "K_- (J=-1)")

    # Λ-scan per sector
    Lambdas = np.logspace(-1, 2.5, 36)
    f = lambda x: np.exp(-x**2)

    print(f"\n[scan] Gaussian f(x)=exp(-x²) at {len(Lambdas)} log-spaced "
          f"Λ ∈ [{Lambdas[0]:.3f}, {Lambdas[-1]:.1f}]")

    rows_p = per_sector_lambda_scan(
        "K_+", eig_p, Lp, DFp, Cp, Lambdas, f)
    rows_m = per_sector_lambda_scan(
        "K_-", eig_m, Lm, DFm, Cm, Lambdas, f)

    # Print Λ-scan tables
    for label, rows, n_sec in [("K_+ (J=+1, particle)", rows_p, n_plus),
                                ("K_- (J=-1, antiparticle)", rows_m, n_minus)]:
        print(f"\n  {'─'*72}")
        print(f"  {label}: {n_sec} modes")
        print(f"  {'Λ':>9} {'Λ²':>11} {'D_eff':>7} {'L%':>6} {'DF%':>6} "
              f"{'cross%':>8} {'modes>0.5':>10}")
        for r in rows:
            print(f"  {r['Lambda']:>9.4f} {r['Lambda']**2:>11.2f} "
                  f"{r['D_eff']:>7.2f} "
                  f"{r['L_frac']*100:>5.1f}% {r['DF_frac']*100:>5.1f}% "
                  f"{r['cross_rel']*100:>+7.1f}% {r['modes_on']:>10d}")

    # Transition scales per sector
    print(f"\n{'─'*78}")
    print(f"  PER-SECTOR TRANSITION SCALES")
    print(f"{'─'*78}")
    for label, rows, n_sec in [("K_+ (J=+1)", rows_p, n_plus),
                                ("K_- (J=-1)", rows_m, n_minus)]:
        Lam_half = find_half_turn_on(rows, n_sec)
        Lam_zero = find_zero_crossing(rows, 'cross_rel')
        L_DF_diff = [r['L_frac'] - r['DF_frac'] for r in rows]
        flip_idxs = np.where(np.diff(np.sign(L_DF_diff)) != 0)[0]
        n_flips = len(flip_idxs)
        print(f"\n  {label}:")
        print(f"    Mode-half-turn-on Λ_½: "
              f"{Lam_half:.4f}  (Λ_½² = {Lam_half**2:.2f})" if Lam_half else "—")
        if Lam_zero:
            print(f"    Cross-rel zero crossing: Λ_t = {Lam_zero:.4f}  "
                  f"(Λ_t² = {Lam_zero**2:.2f})")
        else:
            print(f"    Cross-rel zero crossing: NEVER (always negative across scan)")
        print(f"    L-DF dominance flips: {n_flips}")

    # Comparison to joint K_ω (S185 results, recomputed for consistency)
    print(f"\n{'─'*78}")
    print(f"  COMPARISON: per-sector vs joint K_ω")
    print(f"{'─'*78}")

    # Recompute joint scan for direct comparison
    eig_full, vec_full = np.linalg.eigh(K_omega)
    order = np.argsort(eig_full)
    eig_full = eig_full[order]
    vec_full = vec_full[:, order]
    L_diag_full  = np.einsum('ij,jk,ki->i', vec_full.conj().T, L2,    vec_full).real
    DF_diag_full = np.einsum('ij,jk,ki->i', vec_full.conj().T, DF2_s, vec_full).real
    C_diag_full  = np.einsum('ij,jk,ki->i', vec_full.conj().T, cross, vec_full).real
    rows_full = per_sector_lambda_scan(
        "joint K_ω", eig_full, L_diag_full, DF_diag_full, C_diag_full, Lambdas, f)

    Lam_half_full = find_half_turn_on(rows_full, n)
    Lam_zero_full = find_zero_crossing(rows_full, 'cross_rel')
    Lam_half_p = find_half_turn_on(rows_p, n_plus)
    Lam_half_m = find_half_turn_on(rows_m, n_minus)
    Lam_zero_p = find_zero_crossing(rows_p, 'cross_rel')
    Lam_zero_m = find_zero_crossing(rows_m, 'cross_rel')

    print(f"\n  {'Sector':<22} {'modes':>7} {'Λ_½':>9} {'Λ_t (cross=0)':>15}")
    print(f"  {'─'*60}")
    print(f"  {'joint K_ω (S185)':<22} {n:>7} "
          f"{Lam_half_full:>9.4f} "
          f"{(f'{Lam_zero_full:.4f}' if Lam_zero_full else 'never'):>15s}")
    print(f"  {'K_+ (J=+1)':<22} {n_plus:>7} "
          f"{Lam_half_p:>9.4f} "
          f"{(f'{Lam_zero_p:.4f}' if Lam_zero_p else 'never'):>15s}")
    print(f"  {'K_- (J=-1)':<22} {n_minus:>7} "
          f"{Lam_half_m:>9.4f} "
          f"{(f'{Lam_zero_m:.4f}' if Lam_zero_m else 'never'):>15s}")

    print(f"\n{'='*78}")
    print(f"  INTERPRETATION")
    print(f"{'='*78}")
    print(f"""
  Per-sector mode-half-turn-on Λ_½ should be slightly smaller than
  the joint Λ_½ ≈ 19.95 (S185), because each sector has fewer modes
  but similar overall range.

  The interesting question is whether the cross-term zero-crossing
  Λ_t is finite per-sector — i.e., whether each J-sector's Λ-scan
  transitions through a destructive→constructive regime, or whether
  it remains destructive throughout (as the joint scan does).

  Per S189, the cross-term shift bot12→top12 is +70 to +108%
  per-sector — STRONG enough to potentially produce a finite Λ_t
  in each sector.  If so, per-sector Λ_t identifies sector-specific
  emergence scales.

  Critical scope per S180: pure linear algebra on per-sector
  eigendecompositions of K_ω.  No state evolution, no time-stepping.
""")


if __name__ == '__main__':
    main()
