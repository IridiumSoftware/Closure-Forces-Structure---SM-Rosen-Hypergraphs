#!/usr/bin/env python3
"""
q102_modular_eigenvector_structure_v1.py — K_ω eigenvector mode structure on Q102.

Per S182, K_ω (= β·D²/Λ² + log Z up to scale + constant) on Q98/Q102 has
98 distinct eigenvalues with a largest gap Δ = 723 between λ_91 and
λ_92.  This script decomposes each eigenvector into its sector content:
  - L-fraction:    ⟨v | L² | v⟩ / ⟨v | D² | v⟩    (gravity sector)
  - D_F-fraction:  ⟨v | (α·D_F)² | v⟩ / ⟨v | D² | v⟩  (gauge / Higgs)
  - Cross fraction: 1 - L_frac - DF_frac          (interaction)

For each mode we report (eigenvalue, L_frac, DF_frac, cross_frac) and
identify the SECTOR CHARACTER of the high-frequency cluster (top 6 modes
on Q98) that S182 found structurally distinct via the Δ=723 gap.

Observation-only per S180.  No state evolution, no time-stepping; only
the linear-algebraic mode decomposition of D on Q102's fixed Hilbert
space.

Aaron Green — May 5, 2026 — S182 follow-up: K_ω eigenvector structure.
"""

import sys, time
import numpy as np
from collections import Counter

sys.path.insert(0, '.')
from quotient_landscape_autopoiesis_v1 import (
    haar_C3, complete_edges, adjacent_edges,
)
from q102_build_v1 import build_c_closed_quotient, build_J
from g6a_multiscale_spectral_v1 import (
    G0_cyclic, adjacent_ternary, build_laplacian, build_sample_DF,
)


def sector_decomposition(name, seed_fn, psi_init, depth=4):
    """Build D, compute eigenvectors, decompose each into L / D_F / cross sectors."""
    print(f"\n{'═'*78}")
    print(f"  {name}")
    print(f"{'═'*78}")

    t0 = time.time()
    seed_edges = seed_fn()
    Q = build_c_closed_quotient(seed_edges, psi_init, depth=depth)
    n = Q['n_cl']
    print(f"  [build] Q: n={n}, ({time.time()-t0:.1f}s)")

    J, _ = build_J(Q)
    L, _, _ = build_laplacian(Q)
    D_F, dim_DF, _ = build_sample_DF(Q, J)
    if D_F is None:
        print("  [error] D_F construction failed"); return None

    tr_L2  = float(np.trace(L @ L).real)
    tr_DF2 = float(np.trace(D_F @ D_F).real)
    alpha = float(np.sqrt(tr_L2 / tr_DF2)) if tr_DF2 > 1e-15 else 1.0
    D_F_s = D_F * alpha

    D = L + D_F_s
    L2 = L @ L
    DF2_s = D_F_s @ D_F_s
    cross = L @ D_F_s + D_F_s @ L  # the "C" cross term — γ-odd

    # Eigendecompose D (full)
    print(f"  [spec] eigh on D ({n}×{n})...")
    t0 = time.time()
    eigvals, eigvecs = np.linalg.eigh(D)
    print(f"  [spec] done ({time.time()-t0:.1f}s)")

    # Sort by D² eigenvalue (= eigvals**2 since eigh gives sorted real)
    eig_D2 = eigvals**2
    order = np.argsort(eig_D2)
    eig_D2 = eig_D2[order]
    eigvecs = eigvecs[:, order]

    # Per-mode sector decomposition
    # ⟨v | M | v⟩ for each operator M
    L2_diag    = np.einsum('ij,jk,ki->i', eigvecs.conj().T, L2,    eigvecs).real
    DF2_diag   = np.einsum('ij,jk,ki->i', eigvecs.conj().T, DF2_s, eigvecs).real
    cross_diag = np.einsum('ij,jk,ki->i', eigvecs.conj().T, cross, eigvecs).real

    # Sector content normalised by the diagonal sum L² + (αD_F)²
    # (cross term is a phase / interaction marker, not a sector — report
    # its sign + magnitude separately).
    diag_sum   = L2_diag + DF2_diag
    L_frac     = L2_diag  / np.maximum(diag_sum, 1e-30)
    DF_frac    = DF2_diag / np.maximum(diag_sum, 1e-30)
    cross_rel  = cross_diag / np.maximum(diag_sum, 1e-30)
    # cross_frac retained for compatibility but read it as cross_rel
    cross_frac = cross_rel

    # Report
    print(f"  [report] D = L + α·D_F at α={alpha:.4f}, dim_DF={dim_DF}")
    print(f"          spec(D²): mean={eig_D2.mean():.2f}, "
          f"range=[{eig_D2[0]:.4f}, {eig_D2[-1]:.4f}]")
    print(f"\n  [decomp] mean sector content (across all {n} modes):")
    print(f"          L-fraction:     {L_frac.mean()*100:.2f}%")
    print(f"          D_F-fraction:   {DF_frac.mean()*100:.2f}%")
    print(f"          cross-fraction: {cross_frac.mean()*100:.2f}%")
    print(f"          (sum = {(L_frac.mean()+DF_frac.mean()+cross_frac.mean())*100:.2f}%)")

    # Bottom 6 modes (slowest morphogenesis) — sector character
    print(f"\n  [decomp] BOTTOM 6 modes (low-freq morphogenesis):")
    print(f"          {'idx':>3} {'λ_D²':>10} {'L_frac':>8} {'DF_frac':>8} {'cross':>8}  character")
    for k in range(6):
        char = classify(L_frac[k], DF_frac[k], cross_frac[k])
        print(f"          {k:>3} {eig_D2[k]:>10.4f} "
              f"{L_frac[k]*100:>7.2f}% {DF_frac[k]*100:>7.2f}% "
              f"{cross_frac[k]*100:>+7.2f}%  {char}")

    # Top 6 modes (highest morphogenesis frequencies — the "structurally distinct"
    # cluster S182 identified via the Δ=723 gap)
    print(f"\n  [decomp] TOP 6 modes (high-freq morphogenesis, post-Δ_max gap):")
    print(f"          {'idx':>3} {'λ_D²':>10} {'L_frac':>8} {'DF_frac':>8} {'cross':>8}  character")
    for k in range(n-6, n):
        char = classify(L_frac[k], DF_frac[k], cross_frac[k])
        print(f"          {k:>3} {eig_D2[k]:>10.4f} "
              f"{L_frac[k]*100:>7.2f}% {DF_frac[k]*100:>7.2f}% "
              f"{cross_frac[k]*100:>+7.2f}%  {char}")

    # Aggregate sector content of top vs bottom clusters
    if n >= 12:
        bot12_mean = {
            'L':     L_frac[:12].mean(),
            'DF':    DF_frac[:12].mean(),
            'cross': cross_frac[:12].mean(),
        }
        top12_mean = {
            'L':     L_frac[-12:].mean(),
            'DF':    DF_frac[-12:].mean(),
            'cross': cross_frac[-12:].mean(),
        }
        print(f"\n  [aggregate] BOTTOM 12 vs TOP 12 sector content:")
        print(f"          {'sector':<10} {'bot12':>10} {'top12':>10} {'top - bot':>11}")
        for s in ('L', 'DF', 'cross'):
            d = top12_mean[s] - bot12_mean[s]
            print(f"          {s:<10} {bot12_mean[s]*100:>9.2f}% "
                  f"{top12_mean[s]*100:>9.2f}% {d*100:>+10.2f}%")

    # Identify the largest spectral gap and characterize either side
    gaps = np.diff(eig_D2)
    if len(gaps) > 0:
        gap_idx = int(np.argmax(gaps))
        gap_size = float(gaps[gap_idx])
        print(f"\n  [gap] largest gap: Δ_max = {gap_size:.2f} at index {gap_idx} "
              f"(between λ_{gap_idx} and λ_{gap_idx+1})")
        # Aggregate sector content immediately below vs above the gap
        below_count = min(8, gap_idx + 1)
        above_count = min(8, n - gap_idx - 1)
        if below_count > 0 and above_count > 0:
            bel_L  = L_frac[gap_idx+1-below_count:gap_idx+1].mean()
            bel_DF = DF_frac[gap_idx+1-below_count:gap_idx+1].mean()
            bel_C  = cross_frac[gap_idx+1-below_count:gap_idx+1].mean()
            abv_L  = L_frac[gap_idx+1:gap_idx+1+above_count].mean()
            abv_DF = DF_frac[gap_idx+1:gap_idx+1+above_count].mean()
            abv_C  = cross_frac[gap_idx+1:gap_idx+1+above_count].mean()
            print(f"\n  [gap] Sector content immediately below ({below_count} modes) vs "
                  f"above ({above_count} modes) the largest gap:")
            print(f"          sector       below      above      Δ(above-below)")
            print(f"          L         {bel_L*100:>7.2f}% {abv_L*100:>7.2f}% "
                  f"{(abv_L-bel_L)*100:>+8.2f}%")
            print(f"          DF        {bel_DF*100:>7.2f}% {abv_DF*100:>7.2f}% "
                  f"{(abv_DF-bel_DF)*100:>+8.2f}%")
            print(f"          cross     {bel_C*100:>+7.2f}% {abv_C*100:>+7.2f}% "
                  f"{(abv_C-bel_C)*100:>+8.2f}%")

    return {
        'name': name, 'n': n, 'dim_DF': dim_DF, 'alpha': alpha,
        'eig_D2': eig_D2,
        'L_frac': L_frac, 'DF_frac': DF_frac, 'cross_frac': cross_frac,
    }


def classify(L_f, DF_f, cross_f):
    """Tag a mode by its dominant sector content."""
    if L_f > 0.7:
        return "GRAVITY (L-dominated)"
    if DF_f > 0.7:
        return "GAUGE/HIGGS (D_F-dominated)"
    if abs(cross_f) > 0.5:
        return f"INTERACTION ({cross_f*100:+.0f}% cross)"
    if L_f > DF_f:
        return f"mostly-L  ({L_f*100:.0f}/{DF_f*100:.0f}/{cross_f*100:+.0f})"
    return f"mostly-DF ({L_f*100:.0f}/{DF_f*100:.0f}/{cross_f*100:+.0f})"


def main():
    seed = 42
    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    print("=" * 78)
    print("  K_ω EIGENVECTOR MODE STRUCTURE on Q102 family")
    print("  S182 follow-up — observation-only")
    print("=" * 78)

    results = []
    res48 = sector_decomposition("Q48 = C(M(G₀))    [baseline]", G0_cyclic,
                                 psi_init, depth=5)
    if res48: results.append(res48)

    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}
    res84 = sector_decomposition("Q84 = C(M(Adjacent))    [baseline]",
                                 adjacent_ternary, psi_init, depth=4)
    if res84: results.append(res84)

    rng = np.random.default_rng(seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}
    res98 = sector_decomposition("Q98 / Q102 = C(M(K₆³))    [HEADLINE]",
                                 lambda: complete_edges(), psi_init, depth=4)
    if res98: results.append(res98)

    print(f"\n{'='*78}")
    print(f"  SUMMARY — sector character of K_ω modes across the family")
    print(f"{'='*78}")
    print(f"  {'Quotient':<26} {'L-fraction':>11} {'DF-fraction':>12} {'cross':>10}")
    for r in results:
        print(f"  {r['name'][:26]:<26} "
              f"{r['L_frac'].mean()*100:>10.2f}% "
              f"{r['DF_frac'].mean()*100:>11.2f}% "
              f"{r['cross_frac'].mean()*100:>+9.2f}%")

    print(f"\n  Notes on the high-frequency cluster (S182 Δ_max gap):")
    for r in results:
        if r['n'] < 12: continue
        gap_idx = int(np.argmax(np.diff(r['eig_D2'])))
        if gap_idx >= r['n'] - 8:
            # gap is near the top — characterize the high-freq cluster
            top_n = r['n'] - gap_idx - 1
            top_L  = r['L_frac'][-top_n:].mean()
            top_DF = r['DF_frac'][-top_n:].mean()
            top_C  = r['cross_frac'][-top_n:].mean()
            print(f"    {r['name'][:26]}: top {top_n} modes after Δ_max = "
                  f"L:{top_L*100:.0f}%, DF:{top_DF*100:.0f}%, cross:{top_C*100:+.0f}%")


if __name__ == '__main__':
    main()
