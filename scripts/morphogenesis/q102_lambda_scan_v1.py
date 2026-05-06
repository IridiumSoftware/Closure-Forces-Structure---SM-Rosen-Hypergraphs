#!/usr/bin/env python3
"""
q102_lambda_scan_v1.py — Λ-cutoff scan of the spectral-action sector content.

Per S184, K_ω eigenmode architecture on Q102 has two clusters:
  - bottom 6 modes are destructively-balanced (L≈50/DF≈50/cross≈-99%)
  - top 6 post-gap modes are gravity-dominated constructive (L≈73/DF≈27/+44%)

The spectral action Tr(f(D²/Λ²)) at cutoff Λ weights each mode by
f(λ_k/Λ²); for f = e^{-x²} (Gaussian regulator), modes with λ_k << Λ²
contribute ≈1, modes with λ_k >> Λ² contribute ≈0.  As Λ scans:
  - small Λ: only the slow destructively-balanced modes "turn on"
  - large Λ: the fast gravity-dominated modes also contribute
There is a TRANSITION SCALE Λ_t where the action's character shifts.

This script computes, for each Λ in a log-spaced range:
  - effective dimension D_eff(Λ) = Σ_k f(λ_k/Λ²)
  - per-sector content
      L_content(Λ)  = Σ_k f(λ_k/Λ²) · ⟨v_k|L²|v_k⟩
      DF_content(Λ) = Σ_k f(λ_k/Λ²) · ⟨v_k|(αD_F)²|v_k⟩
      C_content(Λ)  = Σ_k f(λ_k/Λ²) · ⟨v_k|cross|v_k⟩
  - sector fractions (normalised to L+DF, with cross as signed % rel)
  - mode "turn-on" boundary: which modes are weighted >0.5 at this Λ

Reports the transition scale + the cluster character at each end.

Observation-only per S180.  Linear algebra on fixed Q102 structure;
no state evolution.

Aaron Green — May 5, 2026 — S184 follow-up: Λ-scan, scale emergence.
"""

import sys, time
import numpy as np

sys.path.insert(0, '.')
from quotient_landscape_autopoiesis_v1 import haar_C3, complete_edges
from q102_build_v1 import build_c_closed_quotient, build_J
from g6a_multiscale_spectral_v1 import build_laplacian, build_sample_DF


def main():
    seed = 42
    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("=" * 78)
    print("  Λ-SCAN of the spectral-action sector content on Q102")
    print("  S184 follow-up — scale-emergence morphogenesis observation")
    print("=" * 78)

    # Build Q102
    print(f"\n[build] Q102 = C(M(K₆³)) at canonical seed=42 ...")
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
    L2 = L @ L
    DF2_s = D_F_s @ D_F_s
    cross = L @ D_F_s + D_F_s @ L

    eigvals, eigvecs = np.linalg.eigh(D)
    eig_D2 = eigvals ** 2
    order  = np.argsort(eig_D2)
    eig_D2 = eig_D2[order]
    eigvecs = eigvecs[:, order]

    L2_diag    = np.einsum('ij,jk,ki->i', eigvecs.conj().T, L2,    eigvecs).real
    DF2_diag   = np.einsum('ij,jk,ki->i', eigvecs.conj().T, DF2_s, eigvecs).real
    cross_diag = np.einsum('ij,jk,ki->i', eigvecs.conj().T, cross, eigvecs).real

    print(f"[build] Q102: n={n}, dim_DF={dim_DF}, α={alpha:.4f}, "
          f"({time.time()-t0:.1f}s)")
    print(f"[spec]  spec(D²) range: [{eig_D2[0]:.4f}, {eig_D2[-1]:.4f}], "
          f"mean={eig_D2.mean():.2f}, distinct={len(np.unique(np.round(eig_D2,8)))}")

    # ──────────────────────────────────────────────────────────────────
    # Λ-scan
    # ──────────────────────────────────────────────────────────────────
    # Λ² should span from << min(λ_D²) to >> max(λ_D²).
    # spec(D²) ∈ [0.135, 4032], so log(Λ²) from -2 to +5 (Λ² ∈ [0.01, 1e5])
    # Equivalently log(Λ) from -1 to +2.5 (Λ ∈ [0.1, ~316])
    Lambdas = np.logspace(-1, 2.5, 36)

    f = lambda x: np.exp(-x**2)  # Gaussian cutoff regulator

    print(f"\n[scan]  cutoff f(x) = exp(-x²) at {len(Lambdas)} log-spaced Λ ∈ "
          f"[{Lambdas[0]:.3f}, {Lambdas[-1]:.1f}]")
    print(f"\n  {'Λ':>9} {'Λ²':>11} {'D_eff':>7} {'L%':>6} {'DF%':>6} {'cross%':>8} "
          f"{'modes>0.5':>10}")
    print("  " + "─" * 78)

    rows = []
    for Lam in Lambdas:
        weights = f(eig_D2 / (Lam**2))
        D_eff   = float(weights.sum())
        L_w     = float((weights * L2_diag).sum())
        DF_w    = float((weights * DF2_diag).sum())
        cross_w = float((weights * cross_diag).sum())
        diag    = L_w + DF_w
        L_frac  = L_w / max(diag, 1e-30)
        DF_frac = DF_w / max(diag, 1e-30)
        cross_rel = cross_w / max(diag, 1e-30)
        modes_on = int((weights > 0.5).sum())
        rows.append({
            'Lambda': Lam, 'Lambda2': Lam**2, 'D_eff': D_eff,
            'L_frac': L_frac, 'DF_frac': DF_frac, 'cross_rel': cross_rel,
            'modes_on': modes_on,
        })
        print(f"  {Lam:>9.4f} {Lam**2:>11.2f} {D_eff:>7.2f} "
              f"{L_frac*100:>5.1f}% {DF_frac*100:>5.1f}% {cross_rel*100:>+7.1f}% "
              f"{modes_on:>10d}")

    # ──────────────────────────────────────────────────────────────────
    # Identify transition scales
    # ──────────────────────────────────────────────────────────────────
    print(f"\n{'─'*78}")
    print(f"  TRANSITION SCALES")
    print(f"{'─'*78}")

    # 1) When does cross_rel cross zero (destructive → constructive)?
    cross_signs = np.sign([r['cross_rel'] for r in rows])
    zero_cross_idx = np.where(np.diff(cross_signs) > 0)[0]
    if len(zero_cross_idx) > 0:
        i = zero_cross_idx[0]
        Lam_lo, Lam_hi = rows[i]['Lambda'], rows[i+1]['Lambda']
        c_lo, c_hi = rows[i]['cross_rel'], rows[i+1]['cross_rel']
        # Linear interpolate the zero-crossing in log-Λ
        if c_hi != c_lo:
            t = -c_lo / (c_hi - c_lo)
            Lam_zero = float(np.exp((1-t)*np.log(Lam_lo) + t*np.log(Lam_hi)))
        else:
            Lam_zero = float(Lam_lo)
        print(f"\n  Cross-term sign change (destructive → constructive):")
        print(f"    Λ_t (cross=0) ≈ {Lam_zero:.4f}  (Λ_t² ≈ {Lam_zero**2:.4f})")
        print(f"    Below Λ_t: gravity and gauge cancel destructively (slow modes dominate)")
        print(f"    Above Λ_t: gravity and gauge interfere constructively (fast modes contribute)")

    # 2) When do >50% of modes turn on (D_eff > n/2)?
    half_idx = next((i for i, r in enumerate(rows) if r['D_eff'] > n/2), None)
    if half_idx is not None:
        Lam_half = rows[half_idx]['Lambda']
        print(f"\n  Mode-half-turn-on (D_eff > n/2 = {n/2}):")
        print(f"    Λ_½ ≈ {Lam_half:.4f}  (Λ_½² ≈ {Lam_half**2:.4f})")

    # 3) Sector-dominance crossover (L_frac vs DF_frac)
    # Compare to the un-cutoff full-spectrum aggregate (L≈48%, DF≈52%)
    # Look for where the sector character flips (if it does)
    L_vs_DF = [r['L_frac'] - r['DF_frac'] for r in rows]
    flip_idx = np.where(np.diff(np.sign(L_vs_DF)) != 0)[0]
    if len(flip_idx) > 0:
        for fi in flip_idx:
            Lam_lo = rows[fi]['Lambda']
            Lam_hi = rows[fi+1]['Lambda']
            print(f"\n  Sector-dominance flip (L_frac vs DF_frac crossing):")
            print(f"    Λ ∈ [{Lam_lo:.3f}, {Lam_hi:.3f}]")
            print(f"    L-DF: {rows[fi]['L_frac']-rows[fi]['DF_frac']:+.3f} → "
                  f"{rows[fi+1]['L_frac']-rows[fi+1]['DF_frac']:+.3f}")
    else:
        print(f"\n  Sector-dominance: no L↔DF crossover across the scanned Λ range")
        print(f"    {'→ ' + ('L always dominant' if rows[0]['L_frac'] > rows[0]['DF_frac'] else 'DF always dominant')}")

    # ──────────────────────────────────────────────────────────────────
    # Asymptotic limits
    # ──────────────────────────────────────────────────────────────────
    print(f"\n{'─'*78}")
    print(f"  ASYMPTOTIC LIMITS")
    print(f"{'─'*78}")
    print(f"\n  Λ → 0 limit (no modes pass cutoff):")
    print(f"    Λ = {rows[0]['Lambda']:.4f}: D_eff = {rows[0]['D_eff']:.4e}, "
          f"L:{rows[0]['L_frac']*100:.1f}%, DF:{rows[0]['DF_frac']*100:.1f}%, "
          f"cross:{rows[0]['cross_rel']*100:+.1f}%")
    print(f"\n  Λ → ∞ limit (all modes pass — full spectrum aggregate):")
    print(f"    Λ = {rows[-1]['Lambda']:.2f}: D_eff = {rows[-1]['D_eff']:.2f}, "
          f"L:{rows[-1]['L_frac']*100:.1f}%, DF:{rows[-1]['DF_frac']*100:.1f}%, "
          f"cross:{rows[-1]['cross_rel']*100:+.1f}%")

    # ──────────────────────────────────────────────────────────────────
    # Interpretation summary
    # ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  SUMMARY — what scale emergence the Λ-scan reveals")
    print(f"{'='*78}")
    print(f"""
  At small Λ (Λ² ≪ min spec(D²) = 0.135), the spectral-action
  cutoff suppresses all modes uniformly — D_eff ≈ 0; the 'visible'
  morphogenesis content is empty.

  As Λ rises through the low-eigenvalue band (λ_D² ∈ [0.135, 14.7]
  — bottom 12 modes), the destructively-balanced modes dominate
  the spectral action.  The cross-term contribution is large and
  NEGATIVE: gauge and gravity sectors cancel each other.  This is
  the slow-morphogenesis regime.

  At the cross-zero transition Λ_t (reported above), the spectral
  action's character flips from destructive interference to
  constructive.  This is the SCALE-EMERGENCE BOUNDARY between the
  slow-mode regime (closure-preserving deformations dominate) and
  the fast-mode regime (closure perturbations dominate).

  As Λ rises further, the fast gravity-dominated modes (top cluster
  after Δ_max=723 gap) increasingly contribute.  At Λ → ∞ the
  spectral action recovers the full-spectrum aggregate
  L:48%/DF:52%/cross:-20% (S184).

  The Λ-scan thus identifies the structural emergence scale at
  which Q102's morphogenesis transitions from slow-cancellation
  modes to fast-constructive modes — observable analytically from
  the operator content alone, no state evolution required.
""")

    return 0


if __name__ == '__main__':
    sys.exit(main())
