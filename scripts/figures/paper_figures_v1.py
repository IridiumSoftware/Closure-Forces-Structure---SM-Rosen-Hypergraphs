#!/usr/bin/env python3
"""
paper_figures_v1.py — Generate publication-quality figures for the paper.

Aaron Stover — March 2026

Produces 7 PDF figures for §10 of ontology_v15.md:
  Fig 1: Born landscape (2D Gram slice)
  Fig 2: Periodic orbits (D₃ period-3, D₁ period-2)
  Fig 3: Born thinning histogram (W_cycle, 50k ICs)
  Fig 4: Confinement saturation (⟨σ₃⟩_bw vs generation)
  Fig 5: Multiway growth (Z_gen + ⟨μ⟩ dual axis)
  Fig 6: Causal cone growth (BW vs unweighted cumulative)
  Fig 7: D₃ dominance (Born share by daughter type)

Usage:
  python paper_figures_v1.py                  # generate all 7 figures
  python paper_figures_v1.py --only 1,4       # generate specific figures
  python paper_figures_v1.py --outdir ./figs  # custom output directory
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
from matplotlib import rcParams
import os, sys, time, argparse, gc

# ── Publication defaults ──────────────────────────────────────────────────────
rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'lines.linewidth': 1.2,
    'axes.linewidth': 0.8,
})

# Colour palette (colourblind-safe)
C_BLUE = '#0072B2'
C_ORANGE = '#E69F00'
C_GREEN = '#009E73'
C_RED = '#D55E00'
C_PURPLE = '#CC79A7'
C_GREY = '#999999'

# ── Import Layer cores ────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from p2_0_core import born_gram
from p2_0_layer4_cycles import run_haar_cycles, iterate_d3
from p2_0_layer5_sim_v1 import (
    build_G0, run_generation, born_weight_edge, cross_C3,
    HypergraphState, normalize, haar_C3,
)
from p2_c_causal_cones_v1 import compute_cone_profiles, compute_cone_by_daughter_type


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 1: Born landscape — 2D Gram slice
# ═══════════════════════════════════════════════════════════════════════════════

def fig1_born_landscape(outdir):
    """2D slice of Born landscape at z₃=0, all phases=0."""
    print("  Fig 1: Born landscape...", end=" ", flush=True)
    t0 = time.time()

    N = 300
    r1 = np.linspace(0, 0.999, N)
    r2 = np.linspace(0, 0.999, N)
    R1, R2 = np.meshgrid(r1, r2, indexing='ij')

    # Born weights at z₁=r₁, z₂=r₂, z₃=0 (real, all phases zero)
    mu_P = np.zeros_like(R1)
    mu3 = np.zeros_like(R1)
    viable = np.zeros_like(R1, dtype=bool)

    for i in range(N):
        for j in range(N):
            z1, z2, z3 = R1[i, j] + 0j, R2[i, j] + 0j, 0j + 0j
            # Parent Born = |det G|² = |1 - |z1|² - |z2|² - |z3|² + 2Re(z1 z2* z3)|²
            det_G = 1 - abs(z1)**2 - abs(z2)**2 - abs(z3)**2 + 2*np.real(z1 * z2.conjugate() * z3)
            mu_P[i, j] = det_G**2
            m1, m2, m3 = born_gram(z1, z2, z3)
            mu3[i, j] = m3  # D₃ Born = 1 - |z₁|²
            viable[i, j] = det_G > 0

    fig, ax = plt.subplots(1, 1, figsize=(4.5, 4))

    # Born weight heatmap (parent)
    im = ax.pcolormesh(r1, r2, mu_P.T, cmap='viridis', shading='auto',
                       vmin=0, vmax=1)
    plt.colorbar(im, ax=ax, label=r'$\mu_{\mathrm{parent}} = |\det G|^2$', shrink=0.8)

    # Viability boundary (det G = 0)
    ax.contour(r1, r2, mu_P.T, levels=[0.001], colors='white', linewidths=1.5,
               linestyles='--')

    # D₃ Born contours
    ax.contour(r1, r2, mu3.T, levels=[0.2, 0.4, 0.6, 0.8],
               colors='white', linewidths=0.6, alpha=0.5)

    ax.set_xlabel(r'$|z_1| = |\langle\psi_1|\psi_2\rangle|$')
    ax.set_ylabel(r'$|z_2| = |\langle\psi_1|\psi_3\rangle|$')
    ax.set_title(r'Born landscape ($z_3=0$ slice)')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')

    fig.savefig(os.path.join(outdir, 'fig1_born_landscape.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 2: Periodic orbits
# ═══════════════════════════════════════════════════════════════════════════════

def fig2_periodic_orbits(outdir):
    """D₃ period-3 and D₁ period-2 trajectories in Gram magnitude space."""
    print("  Fig 2: Periodic orbits...", end=" ", flush=True)
    t0 = time.time()

    rng = np.random.default_rng(42)
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))

    # D₃ period-3: show 5 ICs
    ax = axes[0]
    for ic in range(5):
        psi1, psi2, psi3 = [haar_C3(rng) for _ in range(3)]
        traj = iterate_d3(psi1, psi2, psi3, 12)
        az1 = [t['az1'] for t in traj]
        az2 = [t['az2'] for t in traj]
        depths = list(range(len(az1)))
        ax.plot(depths, az1, '-o', markersize=3, alpha=0.7, color=C_BLUE)
        ax.plot(depths, az2, '-s', markersize=3, alpha=0.7, color=C_ORANGE)

    ax.set_xlabel('Iteration depth')
    ax.set_ylabel('Gram magnitude')
    ax.set_title(r'$D_3$-always: period 3 (Thm A)')
    ax.legend([r'$|z_1|$', r'$|z_2|$'], loc='upper right', framealpha=0.8)
    ax.set_ylim(0, 1)

    # D₁ period-2: iterate D₁ always
    ax = axes[1]
    for ic in range(5):
        psi1, psi2, psi3 = [haar_C3(rng) for _ in range(3)]
        # D₁ composition: (w, psi2, psi3) where w = conj(cross(psi1, psi2))
        az1_list, az2_list = [], []
        p1, p2, p3 = psi1.copy(), psi2.copy(), psi3.copy()
        for step in range(12):
            z1 = np.vdot(p1, p2)
            z2 = np.vdot(p1, p3)
            az1_list.append(abs(z1))
            az2_list.append(abs(z2))
            w = normalize(np.conj(cross_C3(p1, p2)))
            # D₁: new triple is (w, p2, p3)
            p1, p2, p3 = w, p2, p3

        ax.plot(range(12), az1_list, '-o', markersize=3, alpha=0.7, color=C_BLUE)
        ax.plot(range(12), az2_list, '-s', markersize=3, alpha=0.7, color=C_ORANGE)

    ax.set_xlabel('Iteration depth')
    ax.set_ylabel('Gram magnitude')
    ax.set_title(r'$D_1$-always: period 2 (Thm B)')
    ax.set_ylim(0, 1)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig2_periodic_orbits.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 3: Born thinning histogram
# ═══════════════════════════════════════════════════════════════════════════════

def fig3_born_thinning(outdir):
    """W_cycle histogram from 50k Haar-random ICs."""
    print("  Fig 3: Born thinning histogram...", end=" ", flush=True)
    t0 = time.time()

    data = run_haar_cycles(n_samples=50000, seed=42, verbose=False)
    W = data['W_cycle']
    W = W[W > 1e-30]  # exclude exact zeros

    fig, ax = plt.subplots(1, 1, figsize=(4.5, 3.5))
    ax.hist(np.log10(W), bins=100, color=C_BLUE, alpha=0.8, edgecolor='none')
    ax.axvline(np.log10(np.median(W)), color=C_RED, linestyle='--', linewidth=1.5,
               label=f'Median = {np.median(W):.2e}')
    ax.set_xlabel(r'$\log_{10}(W_{\mathrm{cycle}})$')
    ax.set_ylabel('Count')
    ax.set_title(r'Born thinning per 3-cycle ($W < 1$ universally)')
    ax.legend(framealpha=0.8)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig3_born_thinning.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIGS 4-7: Multiway graph observables (single ensemble run)
# ═══════════════════════════════════════════════════════════════════════════════

def run_multiway_ensemble(n_ic=100, max_depth=7, seed=42):
    """Run Layer 5 ensemble and compute all observables for Figs 4-7."""
    print(f"  Running multiway ensemble ({n_ic} ICs × depth {max_depth})...")
    rng_master = np.random.default_rng(seed)
    n_gens = max_depth + 1

    # Accumulators
    Z_per_gen = np.zeros((n_ic, n_gens))
    N_per_gen = np.zeros((n_ic, n_gens))
    # Singlet overlap (sigma3) accumulators
    bw_sigma_sum = np.zeros((n_ic, n_gens))
    bw_sum = np.zeros((n_ic, n_gens))
    # By daughter type
    type_bw = np.zeros((n_ic, 4, n_gens))  # type 0=initial, 1=D1, 2=D2, 3=D3
    type_bw_sigma = np.zeros((n_ic, 4, n_gens))
    type_count = np.zeros((n_ic, 4, n_gens))
    # Causal cones
    bw_cones_all = np.zeros((n_ic, 6, n_gens))
    ct_cones_all = np.zeros((n_ic, 6, n_gens))
    bw_dtype_D1 = np.zeros((n_ic, 6, n_gens))
    bw_dtype_D2 = np.zeros((n_ic, 6, n_gens))
    bw_dtype_D3 = np.zeros((n_ic, 6, n_gens))

    t0 = time.time()
    for ic in range(n_ic):
        rng_i = np.random.default_rng(rng_master.integers(0, 2**31))
        state = build_G0(rng_i)

        for gen in range(max_depth):
            run_generation(state, gen, prune_threshold=0.0)

        # Collect per-edge data
        for e in state.edges.values():
            g = e.depth
            if g > max_depth:
                continue
            mu = e.born_weight
            Z_per_gen[ic, g] += mu
            N_per_gen[ic, g] += 1

            # Singlet overlap = mu for daughters (cross-product unit norm)
            # For gen 0: sigma3 = mu / |cross|^2 (need to compute)
            dec1 = state.vertices[e.src[0]].dec
            dec2 = state.vertices[e.src[1]].dec
            cross = cross_C3(dec1.psi, dec2.psi)
            cn2 = np.real(np.vdot(cross, cross))
            sigma3 = mu / cn2 if cn2 > 1e-30 else 0.0

            bw_sigma_sum[ic, g] += mu * sigma3
            bw_sum[ic, g] += mu

            dt = e.daughter_type  # 0=initial, 1,2,3=daughters
            type_bw[ic, dt, g] += mu
            type_bw_sigma[ic, dt, g] += mu * sigma3
            type_count[ic, dt, g] += 1

        # Causal cones
        cd = compute_cone_profiles(state, max_depth)
        bw_cones_all[ic] = cd['bw_cones']
        ct_cones_all[ic] = cd['ct_cones']
        dd = compute_cone_by_daughter_type(state, max_depth)
        bw_dtype_D1[ic] = dd['bw_D1']
        bw_dtype_D2[ic] = dd['bw_D2']
        bw_dtype_D3[ic] = dd['bw_D3']

        if (ic + 1) % 20 == 0:
            elapsed = time.time() - t0
            print(f"    IC {ic+1}/{n_ic} [{elapsed:.0f}s]")
        gc.collect()

    print(f"    Ensemble complete: {time.time()-t0:.0f}s")

    return {
        'Z_per_gen': Z_per_gen, 'N_per_gen': N_per_gen,
        'bw_sigma_sum': bw_sigma_sum, 'bw_sum': bw_sum,
        'type_bw': type_bw, 'type_bw_sigma': type_bw_sigma,
        'type_count': type_count,
        'bw_cones': bw_cones_all, 'ct_cones': ct_cones_all,
        'bw_D1': bw_dtype_D1, 'bw_D2': bw_dtype_D2, 'bw_D3': bw_dtype_D3,
        'n_ic': n_ic, 'max_depth': max_depth,
    }


def fig4_confinement(data, outdir):
    """⟨σ₃⟩_bw vs generation, with daughter-type decomposition."""
    print("  Fig 4: Confinement saturation...", end=" ", flush=True)
    t0 = time.time()
    n_gens = data['max_depth'] + 1

    # Overall Born-weighted sigma3
    sigma_bw = data['bw_sigma_sum'].sum(axis=0) / np.maximum(data['bw_sum'].sum(axis=0), 1e-30)
    # Unweighted
    sigma_uw_num = np.zeros(n_gens)
    sigma_uw_den = np.zeros(n_gens)
    for ic in range(data['n_ic']):
        for g in range(n_gens):
            if data['bw_sum'][ic, g] > 1e-30:
                sigma_uw_num[g] += data['bw_sigma_sum'][ic, g] / data['bw_sum'][ic, g]
                sigma_uw_den[g] += 1
    # Actually compute unweighted mean sigma3 properly
    # sigma_uw = <sigma3> unweighted = sum(sigma3) / N_edges
    # We stored bw_sigma_sum = sum(mu * sigma3). For unweighted we need sum(sigma3).
    # But sigma3 = mu for daughters (unit norm). So <sigma3>_uw = <mu>_uw = Z/N
    sigma_uw = data['Z_per_gen'].sum(axis=0) / np.maximum(data['N_per_gen'].sum(axis=0), 1)

    # By daughter type
    sigma_D1 = data['type_bw_sigma'][:, 1, :].sum(axis=0) / np.maximum(data['type_bw'][:, 1, :].sum(axis=0), 1e-30)
    sigma_D2 = data['type_bw_sigma'][:, 2, :].sum(axis=0) / np.maximum(data['type_bw'][:, 2, :].sum(axis=0), 1e-30)
    sigma_D3 = data['type_bw_sigma'][:, 3, :].sum(axis=0) / np.maximum(data['type_bw'][:, 3, :].sum(axis=0), 1e-30)

    gens = np.arange(n_gens)

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
    ax.plot(gens, sigma_bw, 'o-', color='black', linewidth=2, markersize=5,
            label=r'$\langle\sigma_3\rangle_{\mathrm{bw}}$ (all)')
    ax.plot(gens[1:], sigma_D3[1:], 's--', color=C_GREEN, markersize=4,
            label=r'$D_3$ (spectator)')
    ax.plot(gens[1:], sigma_D1[1:], '^--', color=C_BLUE, markersize=4,
            label=r'$D_1$')
    ax.plot(gens[1:], sigma_D2[1:], 'v--', color=C_ORANGE, markersize=4,
            label=r'$D_2$')
    ax.axhline(0.37, color=C_GREY, linestyle=':', linewidth=1,
               label=r'$\langle\sigma_3\rangle_{\mathrm{uw}} \approx 0.37$')

    ax.set_xlabel('Generation depth')
    ax.set_ylabel(r'Born-weighted singlet overlap $\langle\sigma_3\rangle$')
    ax.set_title('Confinement: singlet concentration saturates')
    ax.legend(loc='center right', framealpha=0.9)
    ax.set_xlim(-0.3, n_gens - 0.7)
    ax.set_ylim(0.3, 0.72)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig4_confinement.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


def fig5_multiway_growth(data, outdir):
    """Z_gen (log) and ⟨μ⟩ (linear) vs generation — dual axis."""
    print("  Fig 5: Multiway growth...", end=" ", flush=True)
    t0 = time.time()
    n_gens = data['max_depth'] + 1
    gens = np.arange(n_gens)

    Z_mean = data['Z_per_gen'].mean(axis=0)
    N_mean = data['N_per_gen'].mean(axis=0)
    mu_mean = Z_mean / np.maximum(N_mean, 1)

    fig, ax1 = plt.subplots(1, 1, figsize=(5, 3.5))
    ax2 = ax1.twinx()

    l1, = ax1.semilogy(gens, Z_mean, 'o-', color=C_BLUE, linewidth=2, markersize=5)
    l2, = ax2.plot(gens, mu_mean, 's-', color=C_RED, linewidth=2, markersize=5)

    ax1.set_xlabel('Generation depth')
    ax1.set_ylabel(r'$Z_{\mathrm{gen}}$ (total Born weight)', color=C_BLUE)
    ax2.set_ylabel(r'$\langle\mu\rangle = Z_{\mathrm{gen}}/N$ (mean per edge)', color=C_RED)
    ax1.tick_params(axis='y', labelcolor=C_BLUE)
    ax2.tick_params(axis='y', labelcolor=C_RED)

    ax1.set_title(r'Regime C: $Z$ grows $\sim 3^g$, $\langle\mu\rangle \to 0.36$')
    ax1.legend([l1, l2], [r'$Z_{\mathrm{gen}}$ (log scale)',
                          r'$\langle\mu\rangle$ (linear)'],
               loc='center left', framealpha=0.9)
    ax2.set_ylim(0, 0.6)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig5_multiway_growth.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


def fig6_causal_cones(data, outdir):
    """Born-weighted and unweighted cumulative cone sizes (log scale)."""
    print("  Fig 6: Causal cones...", end=" ", flush=True)
    t0 = time.time()
    n_gens = data['max_depth'] + 1
    gens = np.arange(n_gens)

    # Average over ICs and roots
    bw_avg = data['bw_cones'].mean(axis=(0, 1))  # (n_gens,)
    ct_avg = data['ct_cones'].mean(axis=(0, 1))

    bw_cumul = np.cumsum(bw_avg)
    ct_cumul = np.cumsum(ct_avg)

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
    ax.semilogy(gens, bw_cumul, 'o-', color=C_BLUE, linewidth=2, markersize=5,
                label='Born-weighted')
    ax.semilogy(gens, ct_cumul, 's-', color=C_ORANGE, linewidth=2, markersize=5,
                label='Unweighted (count)')

    # Reference: 3^g
    ref = bw_cumul[1] * (3.0 ** (gens - 1))
    ref[0] = bw_cumul[0]
    ax.semilogy(gens[1:], ref[1:], ':', color=C_GREY, linewidth=1.5,
                label=r'$\propto 3^g$ reference')

    ax.set_xlabel('Generation depth')
    ax.set_ylabel('Cumulative cone size')
    ax.set_title('Causal cone growth: tree-like (no dimensional reduction)')
    ax.legend(framealpha=0.9)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig6_causal_cones.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


def fig7_d3_dominance(data, outdir):
    """Born share by daughter type vs generation."""
    print("  Fig 7: D₃ dominance...", end=" ", flush=True)
    t0 = time.time()
    n_gens = data['max_depth'] + 1

    # Sum over ICs
    bw1 = data['type_bw'][:, 1, :].sum(axis=0)
    bw2 = data['type_bw'][:, 2, :].sum(axis=0)
    bw3 = data['type_bw'][:, 3, :].sum(axis=0)
    total = bw1 + bw2 + bw3
    total = np.maximum(total, 1e-30)

    gens = np.arange(1, n_gens)  # daughters only from gen 1

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))
    ax.plot(gens, (bw3 / total)[1:], 'o-', color=C_GREEN, linewidth=2, markersize=5,
            label=r'$D_3$ (spectator)')
    ax.plot(gens, (bw1 / total)[1:], '^-', color=C_BLUE, linewidth=1.5, markersize=4,
            label=r'$D_1$')
    ax.plot(gens, (bw2 / total)[1:], 'v-', color=C_ORANGE, linewidth=1.5, markersize=4,
            label=r'$D_2$')
    ax.axhline(1/3, color=C_GREY, linestyle=':', linewidth=1, label='1/3 (uniform)')

    ax.set_xlabel('Generation depth')
    ax.set_ylabel('Born weight share')
    ax.set_title(r'$D_3$ dominance: $\sim$43\% from gen 2')
    ax.legend(framealpha=0.9)
    ax.set_ylim(0.2, 0.5)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig7_d3_dominance.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate paper figures")
    parser.add_argument("--outdir", default=os.path.join(SCRIPT_DIR, "..", "figures"))
    parser.add_argument("--only", default=None, help="Comma-separated figure numbers (e.g., 1,4)")
    parser.add_argument("--n_ic", type=int, default=100)
    parser.add_argument("--depth", type=int, default=7)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    figs_to_make = set(range(1, 8))
    if args.only:
        figs_to_make = set(int(x) for x in args.only.split(','))

    print(f"{'='*60}")
    print(f"Paper Figure Generation")
    print(f"  Output: {args.outdir}")
    print(f"  Figures: {sorted(figs_to_make)}")
    print(f"{'='*60}\n")

    t_start = time.time()

    # Standalone figures (fast)
    if 1 in figs_to_make:
        fig1_born_landscape(args.outdir)
    if 2 in figs_to_make:
        fig2_periodic_orbits(args.outdir)
    if 3 in figs_to_make:
        fig3_born_thinning(args.outdir)

    # Multiway ensemble figures (need shared data)
    need_ensemble = figs_to_make & {4, 5, 6, 7}
    if need_ensemble:
        data = run_multiway_ensemble(n_ic=args.n_ic, max_depth=args.depth, seed=42)
        if 4 in figs_to_make:
            fig4_confinement(data, args.outdir)
        if 5 in figs_to_make:
            fig5_multiway_growth(data, args.outdir)
        if 6 in figs_to_make:
            fig6_causal_cones(data, args.outdir)
        if 7 in figs_to_make:
            fig7_d3_dominance(data, args.outdir)

    t_total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"All figures generated in {t_total:.0f}s")
    print(f"Output directory: {args.outdir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
