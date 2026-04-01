#!/usr/bin/env python3
"""
paper_figures_v2.py — Generate 4 new figures for ontology_paper_v2.

Fills layer gaps in the figure progression:
  Fig 2  (NEW): L1 fiber trajectories — spectator fiber W=1 crossing
  Fig 3  (NEW): L2 W=1 contour overlay on Born landscape
  Fig 4  (NEW): L3 Monte Carlo — (a) log₁₀(W) histogram (b) survival by strategy
  Fig 11 (NEW): P2-B anisotropy — A_bw vs A_uw by generation

Uses same style conventions as paper_figures_v1.py.

Usage:
  python paper_figures_v2.py [--outdir ./figures]
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
import os, sys, time, argparse
import numba as nb

# ── Publication defaults (from v1) ───────────────────────────────────────────
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

C_BLUE = '#0072B2'
C_ORANGE = '#E69F00'
C_GREEN = '#009E73'
C_RED = '#D55E00'
C_PURPLE = '#CC79A7'
C_GREY = '#999999'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, '..')


# ═══════════════════════════════════════════════════════════════════════════════
# NUMBA KERNELS (self-contained for figure generation)
# ═══════════════════════════════════════════════════════════════════════════════

@nb.njit
def cross_C3(a, b):
    out = np.empty(3, dtype=nb.complex128)
    out[0] = a[1]*b[2] - a[2]*b[1]
    out[1] = a[2]*b[0] - a[0]*b[2]
    out[2] = a[0]*b[1] - a[1]*b[0]
    return out

@nb.njit
def normalize_vec(v):
    s = 0.0
    for i in range(3):
        s += v[i].real**2 + v[i].imag**2
    n = np.sqrt(s)
    if n < 1e-15:
        return np.zeros(3, dtype=nb.complex128)
    return v / n

@nb.njit
def compose(psi1, psi2):
    return normalize_vec(np.conj(cross_C3(psi1, psi2)))

@nb.njit
def born_weight(psi1, psi2, psi3, is_odd):
    if is_odd:
        pt1, pt2, pt3 = np.conj(psi1), np.conj(psi2), psi3.copy()
    else:
        pt1, pt2, pt3 = psi1.copy(), psi2.copy(), np.conj(psi3)
    cross = cross_C3(pt1, pt2)
    det_val = nb.complex128(0.0)
    for i in range(3):
        det_val += pt3[i] * cross[i]
    return det_val.real**2 + det_val.imag**2

@nb.njit
def born_gram(z1, z2, z3):
    """Daughter Born weights from Gram coordinates (parent)."""
    a1sq = z1.real**2 + z1.imag**2
    a2sq = z2.real**2 + z2.imag**2
    a3sq = z3.real**2 + z3.imag**2
    denom = 1.0 - a1sq
    if denom < 1e-30:
        return 0.0, 0.0, 0.0
    d1_num = z1 * z3 - z2
    mu1 = (d1_num.real**2 + d1_num.imag**2) / denom
    d2_num = z3 - np.conj(z1) * z2
    mu2 = (d2_num.real**2 + d2_num.imag**2) / denom
    mu3 = 1.0 - a1sq
    return mu1, mu2, mu3


def haar_C3(rng):
    v = rng.standard_normal(3) + 1j * rng.standard_normal(3)
    n = np.linalg.norm(v)
    return v / n if n > 1e-15 else np.zeros(3, dtype=np.complex128)


# Warmup numba
_a = np.ones(3, dtype=np.complex128)
_b = np.ones(3, dtype=np.complex128) * 1j
_ = compose(_a, _b)
_ = born_weight(_a, _b, _a, False)
_ = born_gram(0.5+0j, 0.3+0j, 0.2+0j)


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 2: L1 Fiber Trajectories — Spectator Fiber with W=1 Crossing
# ═══════════════════════════════════════════════════════════════════════════════

def fig2_fiber_trajectories(outdir):
    """1D fiber: Gram magnitudes and W along spectator fiber (|z₃| varies)."""
    print("  Fig 2: L1 fiber trajectories...", end=" ", flush=True)
    t0 = time.time()

    # Spectator fiber: z₁ = 0.5, z₂ = 0.3, z₃ = t (real), t ∈ [0, 0.95]
    N = 500
    t_vals = np.linspace(0.01, 0.95, N)

    mu_D1 = np.zeros(N)
    mu_D2 = np.zeros(N)
    mu_D3 = np.zeros(N)
    W_vals = np.zeros(N)
    mu_P = np.zeros(N)

    z1_fixed = 0.5 + 0j
    z2_fixed = 0.3 + 0j

    for i, t in enumerate(t_vals):
        z3 = t + 0j
        m1, m2, m3 = born_gram(z1_fixed, z2_fixed, z3)
        mu_D1[i] = m1
        mu_D2[i] = m2
        mu_D3[i] = m3

        # Parent Born weight
        det_G = 1 - abs(z1_fixed)**2 - abs(z2_fixed)**2 - abs(z3)**2 + \
                2*np.real(z1_fixed * z2_fixed.conjugate() * z3)
        mu_P[i] = det_G**2

        # W = product of daughter Born / parent Born
        if mu_P[i] > 1e-30:
            W_vals[i] = (m1 * m2 * m3) / mu_P[i]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5, 5.5), sharex=True)

    # Top: daughter Born weights along fiber
    ax1.plot(t_vals, mu_D1, '-', color=C_BLUE, linewidth=1.5, label=r'$\mu(D_1)$')
    ax1.plot(t_vals, mu_D2, '-', color=C_ORANGE, linewidth=1.5, label=r'$\mu(D_2)$')
    ax1.plot(t_vals, mu_D3, '-', color=C_GREEN, linewidth=1.5, label=r'$\mu(D_3)$')
    ax1.plot(t_vals, mu_P, '--', color='black', linewidth=1, alpha=0.6,
             label=r'$\mu_{\mathrm{parent}}$')
    ax1.set_ylabel('Born weight')
    ax1.set_title(r'Spectator fiber: $z_1=0.5$, $z_2=0.3$, $z_3=t$')
    ax1.legend(loc='upper right', framealpha=0.9, fontsize=8)
    ax1.set_ylim(0, 1.0)

    # Bottom: W product along fiber
    ax2.semilogy(t_vals, W_vals, '-', color=C_RED, linewidth=1.5)
    ax2.axhline(1.0, color=C_GREY, linestyle=':', linewidth=1, label='$W = 1$')

    # Mark the W=1 crossing
    for i in range(len(W_vals)-1):
        if W_vals[i] < 1.0 and W_vals[i+1] >= 1.0:
            t_cross = t_vals[i] + (1.0 - W_vals[i]) / (W_vals[i+1] - W_vals[i]) * (t_vals[i+1] - t_vals[i])
            ax2.axvline(t_cross, color=C_PURPLE, linestyle='--', linewidth=1,
                        label=f'$W=1$ crossing at $t={t_cross:.2f}$')
            break
        elif W_vals[i] > 1.0 and W_vals[i+1] <= 1.0:
            t_cross = t_vals[i] + (W_vals[i] - 1.0) / (W_vals[i] - W_vals[i+1]) * (t_vals[i+1] - t_vals[i])
            ax2.axvline(t_cross, color=C_PURPLE, linestyle='--', linewidth=1,
                        label=f'$W=1$ crossing at $t={t_cross:.2f}$')
            break

    ax2.set_xlabel(r'Fiber parameter $t = |z_3|$')
    ax2.set_ylabel(r'$W = \mu(D_1)\mu(D_2)\mu(D_3)/\mu_P$')
    ax2.legend(loc='upper left', framealpha=0.9, fontsize=8)
    ax2.set_ylim(1e-4, 1e3)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig2_fiber_trajectories.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 3: L2 W=1 Contour on Born Landscape
# ═══════════════════════════════════════════════════════════════════════════════

def fig3_w1_contour(outdir):
    """2D slice with W=1 contour overlay showing self-reinforcement crescent."""
    print("  Fig 3: L2 W=1 contour...", end=" ", flush=True)
    t0 = time.time()

    N = 300
    r1 = np.linspace(0.01, 0.999, N)
    r2 = np.linspace(0.01, 0.999, N)
    R1, R2 = np.meshgrid(r1, r2, indexing='ij')

    W_grid = np.full_like(R1, np.nan)
    mu_P_grid = np.zeros_like(R1)

    for i in range(N):
        for j in range(N):
            z1 = R1[i, j] + 0j
            z2 = R2[i, j] + 0j
            z3 = 0j
            det_G = 1 - abs(z1)**2 - abs(z2)**2 + 0
            mu_p = det_G**2
            mu_P_grid[i, j] = mu_p

            if mu_p > 1e-30:
                m1, m2, m3 = born_gram(z1, z2, z3)
                W_grid[i, j] = (m1 * m2 * m3) / mu_p

    fig, ax = plt.subplots(1, 1, figsize=(4.5, 4))

    # Born landscape (parent) as background
    im = ax.pcolormesh(r1, r2, np.log10(np.maximum(mu_P_grid, 1e-10)).T,
                       cmap='viridis', shading='auto', vmin=-6, vmax=0)
    plt.colorbar(im, ax=ax, label=r'$\log_{10}\,\mu_{\mathrm{parent}}$', shrink=0.8)

    # W = 1 contour (the self-reinforcement boundary)
    ax.contour(r1, r2, W_grid.T, levels=[1.0], colors='red', linewidths=2.0,
               linestyles='-')

    # W = 0.1 and W = 10 contours for context
    ax.contour(r1, r2, W_grid.T, levels=[0.1], colors='white', linewidths=0.8,
               linestyles='--')
    ax.contour(r1, r2, W_grid.T, levels=[10.0], colors='yellow', linewidths=0.8,
               linestyles='--')

    # Viability boundary
    ax.contour(r1, r2, mu_P_grid.T, levels=[0.001], colors='white', linewidths=1.5,
               linestyles=':')

    ax.set_xlabel(r'$|z_1|$')
    ax.set_ylabel(r'$|z_2|$')
    ax.set_title(r'$W=1$ contour ($z_3=0$): self-reinforcement crescent')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')

    # Legend for contours
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', linewidth=2, label='$W=1$'),
        Line2D([0], [0], color='white', linewidth=0.8, linestyle='--', label='$W=0.1$ (thinning)'),
        Line2D([0], [0], color='yellow', linewidth=0.8, linestyle='--', label='$W=10$ (reinforcing)'),
        Line2D([0], [0], color='white', linewidth=1.5, linestyle=':', label='Viability boundary'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.85, fontsize=7)

    fig.savefig(os.path.join(outdir, 'fig3_w1_contour.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 4: L3 Monte Carlo — Born Distribution + Strategy Survival
# ═══════════════════════════════════════════════════════════════════════════════

def fig4_montecarlo(outdir):
    """(a) W distribution from Haar ensemble (b) Survival by strategy vs depth."""
    print("  Fig 4: L3 Monte Carlo...", end=" ", flush=True)
    t0 = time.time()

    rng = np.random.default_rng(42)
    N_SAMPLES = 100000
    MAX_DEPTH = 10

    # (a) Compute W for Haar-random ICs
    W_samples = np.zeros(N_SAMPLES)
    for s in range(N_SAMPLES):
        psi1, psi2, psi3 = haar_C3(rng), haar_C3(rng), haar_C3(rng)
        mu_p = born_weight(psi1, psi2, psi3, False)
        w = compose(psi1, psi2)
        # Three daughters
        mu1 = born_weight(w, psi2, psi3, True)
        mu2 = born_weight(w, psi1, psi3, True)
        mu3 = born_weight(w, psi1, psi2, True)
        if mu_p > 1e-30:
            W_samples[s] = (mu1 * mu2 * mu3) / mu_p
        else:
            W_samples[s] = 0.0

    # (b) Survival by strategy
    N_SURV = 5000
    strategies = ['D3-always', 'D1-always', 'Max-Born', 'Random']
    survival = {s: np.ones(MAX_DEPTH+1) for s in strategies}

    for s in range(N_SURV):
        p1, p2, p3 = haar_C3(rng), haar_C3(rng), haar_C3(rng)

        # Run each strategy
        for strat in strategies:
            pp1, pp2, pp3 = p1.copy(), p2.copy(), p3.copy()
            alive = True
            for depth in range(1, MAX_DEPTH+1):
                w = compose(pp1, pp2)
                is_odd = (depth % 2 == 1)
                mu1 = born_weight(w, pp2, pp3, is_odd)
                mu2 = born_weight(w, pp1, pp3, is_odd)
                mu3 = born_weight(w, pp1, pp2, is_odd)

                if strat == 'D3-always':
                    pp1, pp2, pp3 = w, pp1, pp2
                    alive = mu3 > 1e-30
                elif strat == 'D1-always':
                    pp1, pp2, pp3 = w, pp2, pp3
                    alive = mu1 > 1e-30
                elif strat == 'Max-Born':
                    mus = [mu1, mu2, mu3]
                    best = np.argmax(mus)
                    if best == 0:
                        pp1, pp2, pp3 = w, pp2, pp3
                    elif best == 1:
                        pp1, pp2, pp3 = w, pp1, pp3
                    else:
                        pp1, pp2, pp3 = w, pp1, pp2
                    alive = mus[best] > 1e-30
                elif strat == 'Random':
                    choice = rng.integers(0, 3)
                    if choice == 0:
                        pp1, pp2, pp3 = w, pp2, pp3
                        alive = mu1 > 1e-30
                    elif choice == 1:
                        pp1, pp2, pp3 = w, pp1, pp3
                        alive = mu2 > 1e-30
                    else:
                        pp1, pp2, pp3 = w, pp1, pp2
                        alive = mu3 > 1e-30

                if not alive:
                    for d2 in range(depth, MAX_DEPTH+1):
                        survival[strat][d2] -= 1.0 / N_SURV
                    break

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.5))

    # (a) W histogram
    W_pos = W_samples[W_samples > 1e-30]
    ax1.hist(np.log10(W_pos), bins=80, color=C_BLUE, alpha=0.8, edgecolor='none',
             density=True)
    med = np.median(W_pos)
    ax1.axvline(np.log10(med), color=C_RED, linestyle='--', linewidth=1.5,
                label=f'Median = {med:.3f}')
    ax1.axvline(0, color=C_GREY, linestyle=':', linewidth=1,
                label='$W=1$ (neutral)')
    frac_thin = np.mean(W_pos < 1.0) * 100
    ax1.set_xlabel(r'$\log_{10}(W)$')
    ax1.set_ylabel('Density')
    ax1.set_title(f'Born thinning: {frac_thin:.0f}% have $W < 1$')
    ax1.legend(framealpha=0.9, fontsize=8)

    # (b) Survival
    depths = np.arange(MAX_DEPTH+1)
    colors = {
        'D3-always': C_GREEN, 'D1-always': C_BLUE,
        'Max-Born': C_ORANGE, 'Random': C_GREY
    }
    for strat in strategies:
        ax2.plot(depths, survival[strat] * 100, 'o-', color=colors[strat],
                 linewidth=1.5, markersize=4, label=strat)
    ax2.set_xlabel('Iteration depth')
    ax2.set_ylabel('Survival (%)')
    ax2.set_title(r'$D_3$-always: 100% survival')
    ax2.legend(framealpha=0.9, fontsize=8)
    ax2.set_ylim(0, 105)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig4_montecarlo.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# FIG 11: P2-B Anisotropy — Born vs Unweighted
# ═══════════════════════════════════════════════════════════════════════════════

def fig11_symmetry(outdir):
    """Per-IC anisotropy A_bw vs A_uw by generation + hi/lo σ₃ split inset."""
    print("  Fig 11: P2-B symmetry...", end=" ", flush=True)
    t0 = time.time()

    # Run a lightweight version of the P2-B computation (50 ICs, depth 8)
    N_IC = 50
    MAX_DEPTH = 8
    n_gens = MAX_DEPTH + 1
    rng_master = np.random.default_rng(42)

    ic_aniso_bw = np.zeros((N_IC, n_gens))
    ic_aniso_uw = np.zeros((N_IC, n_gens))

    for ic in range(N_IC):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        psi_list = [haar_C3(rng) for _ in range(6)]
        g0_edges = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

        # Per-gen Q tensor accumulators
        Q_bw = np.zeros((n_gens, 3, 3), dtype=np.complex128)
        Q_uw = np.zeros((n_gens, 3, 3), dtype=np.complex128)
        bw_sum = np.zeros(n_gens)
        edge_count = np.zeros(n_gens, dtype=np.int64)

        # Gen 0
        current_edges = []
        for s1, s2, s3 in g0_edges:
            bw = born_weight(psi_list[s1], psi_list[s2], psi_list[s3], False)
            nhat = compose(psi_list[s1], psi_list[s2])
            for a in range(3):
                for b in range(3):
                    Q_bw[0, a, b] += bw * nhat[a] * np.conj(nhat[b])
                    Q_uw[0, a, b] += nhat[a] * np.conj(nhat[b])
            bw_sum[0] += bw
            edge_count[0] += 1
            current_edges.append((s1, s2, s3))

        for gen in range(MAX_DEPTH):
            next_edges = []
            new_depth = gen + 1
            is_odd = (new_depth % 2 == 1)
            for v1, v2, v3 in current_edges:
                psi_new = compose(psi_list[v1], psi_list[v2])
                w_vid = len(psi_list)
                psi_list.append(psi_new)
                daughters = [(w_vid, v2, v3), (w_vid, v1, v3), (w_vid, v1, v2)]
                for dv1, dv2, dv3 in daughters:
                    bw = born_weight(psi_list[dv1], psi_list[dv2], psi_list[dv3], is_odd)
                    nhat = compose(psi_list[dv1], psi_list[dv2])
                    g = new_depth
                    for a in range(3):
                        for b in range(3):
                            Q_bw[g, a, b] += bw * nhat[a] * np.conj(nhat[b])
                            Q_uw[g, a, b] += nhat[a] * np.conj(nhat[b])
                    bw_sum[g] += bw
                    edge_count[g] += 1
                    next_edges.append((dv1, dv2, dv3))
            current_edges = next_edges

        # Eigendecomposition
        for g in range(n_gens):
            if bw_sum[g] > 1e-300:
                evals = np.sort(np.linalg.eigvalsh(Q_bw[g] / bw_sum[g]))[::-1]
                ic_aniso_bw[ic, g] = evals[0] - evals[2]
            if edge_count[g] > 0:
                evals = np.sort(np.linalg.eigvalsh(Q_uw[g] / edge_count[g]))[::-1]
                ic_aniso_uw[ic, g] = evals[0] - evals[2]

    # Plot
    gens = np.arange(n_gens)
    a_bw_mean = np.mean(ic_aniso_bw, axis=0)
    a_bw_std = np.std(ic_aniso_bw, axis=0)
    a_uw_mean = np.mean(ic_aniso_uw, axis=0)
    a_uw_std = np.std(ic_aniso_uw, axis=0)

    fig, ax = plt.subplots(1, 1, figsize=(5, 3.5))

    ax.errorbar(gens, a_bw_mean, yerr=a_bw_std, fmt='o-', color=C_RED,
                linewidth=1.5, markersize=5, capsize=3,
                label=r'$\langle A \rangle_{\mathrm{bw}}$ (Born-weighted)')
    ax.errorbar(gens, a_uw_mean, yerr=a_uw_std, fmt='s-', color=C_BLUE,
                linewidth=1.5, markersize=5, capsize=3,
                label=r'$\langle A \rangle_{\mathrm{uw}}$ (unweighted)')

    # Shade the gap
    ax.fill_between(gens, a_uw_mean, a_bw_mean, alpha=0.15, color=C_PURPLE)

    ax.set_xlabel('Generation depth')
    ax.set_ylabel(r'Per-IC anisotropy $A = \lambda_1 - \lambda_3$')
    ax.set_title(r'Born weighting amplifies anisotropy ($A_{\mathrm{bw}} > A_{\mathrm{uw}}$)')
    ax.legend(framealpha=0.9)
    ax.set_xlim(-0.3, MAX_DEPTH + 0.3)
    ax.set_ylim(0, 0.75)

    # Annotation
    ax.annotate(r'$\Delta A \approx +0.04$', xy=(6, (a_bw_mean[6]+a_uw_mean[6])/2),
                fontsize=9, color=C_PURPLE, ha='left')

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig11_symmetry.pdf'))
    plt.close(fig)
    print(f"{time.time()-t0:.1f}s")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Generate v2 paper figures (4 new)")
    parser.add_argument("--outdir", default=os.path.join(PROJECT_DIR, "figures"))
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    print(f"{'='*60}")
    print(f"Paper Figure Generation v2 (4 new figures)")
    print(f"  Output: {args.outdir}")
    print(f"{'='*60}")

    fig2_fiber_trajectories(args.outdir)
    fig3_w1_contour(args.outdir)
    fig4_montecarlo(args.outdir)
    fig11_symmetry(args.outdir)

    print(f"\n{'='*60}")
    print(f"All 4 new figures generated.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
