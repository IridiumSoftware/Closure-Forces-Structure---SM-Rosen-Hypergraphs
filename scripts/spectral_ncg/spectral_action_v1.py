#!/usr/bin/env python3
"""
spectral_action_v1.py — Phase B2: Spectral Action on Q₄₈ × 3_gen

Computes heat trace S(t) = Tr(e^{-tD²}), extracts Seeley-DeWitt coefficients,
generates publication-quality figures.

Usage:
  python3 spectral_action_v1.py [--seed S]
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
import argparse
import time
from collections import defaultdict

# Publication style
rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['legend.fontsize'] = 9
rcParams['figure.figsize'] = (7, 5)
rcParams['savefig.dpi'] = 300
rcParams['savefig.bbox'] = 'tight'

def cross_C3(a, b):
    return np.array([a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]], dtype=np.complex128)
def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-15 else v
def compose(a, b):
    return normalize(np.conj(cross_C3(a, b)))
def haar(rng):
    return normalize(rng.standard_normal(3) + 1j * rng.standard_normal(3))
def fid(a, b):
    return abs(np.vdot(a, b))**2

G0 = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

# ═══════════════════════════════════════════════════════════════════════════════
# BUILD THE 3-GEN Q₄₈ WITH D_F
# ═══════════════════════════════════════════════════════════════════════════════

def build_3gen_system(seed):
    """Build Q₄₈ × 3_gen: Laplacian + D_F."""
    from three_gen_orderone_v1 import build_3gen_q48, build_3gen_representation
    from three_gen_orderone_v1 import compute_violations_batch

    n48, n_total, qp48, qt, cl_origin, J, gamma, j_map = build_3gen_q48(seed)
    rep, triplets = build_3gen_representation(n48, n_total, qp48, qt, cl_origin, J, gamma, j_map)

    Gamma = np.diag(gamma)
    orig_idx = np.array([i for i in range(n_total) if gamma[i] > 0], dtype=np.int64)
    conj_idx = np.array([i for i in range(n_total) if gamma[i] < 0], dtype=np.int64)

    # Build graph Laplacian on Q₄₈ extended to 3-gen
    # Adjacency from hyperedges (need to rebuild)
    rng = np.random.default_rng(seed)
    psi = {v: haar(rng) for v in range(6)}
    for _ in range(3):  # skip generation Haar draws
        for v in range(6): haar(rng)
    nv=6; ae=[(0,s1,s2,s3) for s1,s2,s3 in G0]; cc={}
    for d in range(5):
        for _,v1,v2,v3 in [e for e in ae if e[0]==d]:
            key=(v1,v2)
            if key not in cc:
                psi[nv]=compose(psi[v1],psi[v2]); cc[key]=nv; nv+=1
            w=cc[key]; ae.append((d+1,w,v2,v3)); ae.append((d+1,w,v1,v3)); ae.append((d+1,w,v1,v2))
    vids=sorted(psi.keys()); cl=[]; vc={}
    for v in vids:
        m=False
        for ci,(_,rp) in enumerate(cl):
            if fid(psi[v],rp)>0.999: vc[v]=ci; m=True; break
        if not m: vc[v]=len(cl); cl.append((v,psi[v]))

    # Also need conjugate sector adjacency
    psi_c = {v: np.conj(psi[v]) for v in range(6)}
    psi2=dict(psi_c); nv2=6; ae2=[(0,s1,s2,s3) for s1,s2,s3 in G0]; cc2={}
    for d in range(5):
        for _,v1,v2,v3 in [e for e in ae2 if e[0]==d]:
            key=(v1,v2)
            if key not in cc2:
                psi2[nv2]=compose(psi2[v1],psi2[v2]); cc2[key]=nv2; nv2+=1
            w=cc2[key]; ae2.append((d+1,w,v2,v3)); ae2.append((d+1,w,v1,v3)); ae2.append((d+1,w,v1,v2))

    off=max(psi.keys())+1
    all_psi=dict(psi)
    for v in psi2: all_psi[v+off]=psi2[v]
    avids=sorted(all_psi.keys()); acl=[]; avc={}
    for v in avids:
        m=False
        for ci,(_,rp) in enumerate(acl):
            if fid(all_psi[v],rp)>0.999: avc[v]=ci; m=True; break
        if not m: avc[v]=len(acl); acl.append((v,all_psi[v]))

    nn48 = len(acl)
    adj48 = np.zeros((nn48, nn48))
    for edges_list in [ae, [(d,v1+off,v2+off,v3+off) for d,v1,v2,v3 in ae2]]:
        for _,v1,v2,v3 in edges_list:
            if v1 in avc and v2 in avc and v3 in avc:
                c1,c2,c3=avc[v1],avc[v2],avc[v3]
                adj48[c1,c2]=adj48[c2,c1]=1;adj48[c1,c3]=adj48[c3,c1]=1;adj48[c2,c3]=adj48[c3,c2]=1
    np.fill_diagonal(adj48, 0)
    deg48 = adj48.sum(axis=1)
    L48 = np.diag(deg48) - adj48

    # Extend L to 3-gen: L acts identically on each generation slot
    n_gen = 3
    L = np.zeros((n_total, n_total))
    for i in range(nn48):
        for j in range(nn48):
            if L48[i,j] != 0:
                for g in range(n_gen):
                    L[i*n_gen+g, j*n_gen+g] = L48[i,j]

    return n_total, L, J, Gamma, gamma, orig_idx, conj_idx, rep, n48


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD D_F FROM THE 271-DIM FAMILY
# ═══════════════════════════════════════════════════════════════════════════════

def build_df(seed, n_total, J, Gamma, gamma, orig_idx, conj_idx, rep):
    """Build a representative D_F from the order-one kernel."""
    from three_gen_orderone_v1 import compute_violations_batch

    J_inv = J.T
    opp = {name: J @ pi.conj() @ J_inv for name, pi in rep.items()}
    gen_names = [f'E_{i}{j}' for i in range(3) for j in range(3)] + ['sigma1','sigma2','sigma3']

    n_orig = len(orig_idx); n_conj = len(conj_idx)
    dim_M = n_conj * n_orig

    # Incremental order-one
    basis = np.eye(dim_M)
    current_dim = dim_M

    for a_name in gen_names:
        pi_a = rep[a_name].astype(np.complex128)
        for b_name in gen_names:
            pi_b_opp = opp[b_name].astype(np.complex128)
            if current_dim == 0: break
            V = compute_violations_batch(basis, conj_idx, orig_idx, pi_a, pi_b_opp, n_total)
            if np.max(np.abs(V)) < 1e-12: continue
            G = V @ V.T
            eigvals, eigvecs = np.linalg.eigh(G)
            ker_mask = eigvals < 1e-14
            new_dim = int(np.sum(ker_mask))
            if new_dim < current_dim and new_dim > 0:
                basis = eigvecs[:, ker_mask].T @ basis
                current_dim = basis.shape[0]
            elif new_dim == 0:
                current_dim = 0; break
        if current_dim == 0: break

    # JD = +DJ
    jd_rows = []
    for k in range(current_dim):
        M = basis[k].reshape(n_conj, n_orig)
        D_k = np.zeros((n_total, n_total), dtype=np.complex128)
        D_k[np.ix_(conj_idx, orig_idx)] = M; D_k[np.ix_(orig_idx, conj_idx)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())
    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd, eigvecs_jd = np.linalg.eigh(G_jd)
    ker_mask = eigvals_jd < 1e-14
    final_coords = eigvecs_jd[:, ker_mask].T
    final_basis = final_coords @ basis
    final_dim = final_basis.shape[0]

    # Build representative D_F (sum of basis, normalised)
    M_rep = np.zeros((n_conj, n_orig))
    for k in range(final_dim):
        M_rep += final_basis[k].reshape(n_conj, n_orig)

    D_F = np.zeros((n_total, n_total))
    D_F[np.ix_(conj_idx, orig_idx)] = M_rep
    D_F[np.ix_(orig_idx, conj_idx)] = M_rep.T

    return D_F, final_dim, final_basis


# ═══════════════════════════════════════════════════════════════════════════════
# HEAT TRACE AND SEELEY-DEWITT
# ═══════════════════════════════════════════════════════════════════════════════

def compute_heat_trace(D_sq_evals, t_range):
    """S(t) = Σ exp(-t λ) where λ are eigenvalues of D²."""
    S = np.zeros_like(t_range)
    for i, t in enumerate(t_range):
        S[i] = np.sum(np.exp(-t * D_sq_evals))
    return S

def spectral_dimension(S, t_range):
    """d_s(t) = -2 d(ln S)/d(ln t)"""
    ln_t = np.log(t_range)
    ln_S = np.log(np.maximum(S, 1e-300))
    return -2 * np.gradient(ln_S, ln_t)

def extract_seeley_dewitt(S, t_range, n_terms=3):
    """Fit S(t) ≈ a₀ + a₂·t + a₄·t² for small t."""
    # Use only the small-t regime
    mask = t_range < np.median(t_range)
    t_fit = t_range[mask]
    S_fit = S[mask]

    # Polynomial fit: S(t) = a₀ + a₂·t + a₄·t²
    A = np.column_stack([np.ones_like(t_fit), t_fit, t_fit**2])
    coeffs, _, _, _ = np.linalg.lstsq(A, S_fit, rcond=None)
    return coeffs  # [a₀, a₂, a₄]


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURES
# ═══════════════════════════════════════════════════════════════════════════════

def make_figures(t_range, S_L, S_DF, S_full, ds_L, ds_DF, ds_full,
                 evals_L, evals_DF, evals_full, coeffs_L, coeffs_DF, coeffs_full,
                 figdir):
    """Generate publication-quality figures."""

    # Fig 1: Heat trace S(t) vs t
    fig, ax = plt.subplots()
    ax.loglog(t_range, S_L, 'b-', lw=1.5, label='$L$ (geometry)')
    ax.loglog(t_range, S_DF, 'r-', lw=1.5, label='$D_F$ (gauge)')
    ax.loglog(t_range, S_full, 'purple', lw=2, label='$D_{\\rm full} = L + \\alpha D_F$')
    ax.set_xlabel('$t$ (diffusion time)')
    ax.set_ylabel('$S(t) = {\\rm Tr}(e^{-tD^2})$')
    ax.set_title('Heat Trace: Spectral Action')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(f'{figdir}/fig_heat_trace.pdf')
    plt.close()

    # Fig 2: Spectral dimension d_s(t)
    fig, ax = plt.subplots()
    margin = 10
    ax.semilogx(t_range[margin:-margin], ds_L[margin:-margin], 'b-', lw=1.5, label='$L$ (geometry)')
    ax.semilogx(t_range[margin:-margin], ds_DF[margin:-margin], 'r-', lw=1.5, label='$D_F$ (gauge)')
    ax.semilogx(t_range[margin:-margin], ds_full[margin:-margin], 'purple', lw=2, label='$D_{\\rm full}$')
    ax.axhline(y=4, color='gray', ls='--', alpha=0.5, label='$d=4$')
    ax.set_xlabel('$t$ (diffusion time)')
    ax.set_ylabel('$d_s(t) = -2\\, d(\\ln S)/d(\\ln t)$')
    ax.set_title('Spectral Dimension')
    ax.legend()
    ax.set_ylim(-1, 20)
    ax.grid(True, alpha=0.3)
    fig.savefig(f'{figdir}/fig_spectral_dimension.pdf')
    plt.close()

    # Fig 3: Seeley-DeWitt coefficients
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['$a_0$\n(cosmo)', '$a_2$\n(EH+YM)', '$a_4$\n(Higgs)']
    x = np.arange(3)
    w = 0.25
    ax.bar(x-w, [coeffs_L[0], coeffs_L[1], coeffs_L[2]], w, color='steelblue', label='$L^2$ (gravity)')
    ax.bar(x, [coeffs_DF[0], coeffs_DF[1], coeffs_DF[2]], w, color='indianred', label='$D_F^2$ (SM)')
    ax.bar(x+w, [coeffs_full[0], coeffs_full[1], coeffs_full[2]], w, color='mediumpurple', label='$D_{\\rm full}^2$')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Coefficient value')
    ax.set_title('Seeley-DeWitt Coefficients')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    fig.savefig(f'{figdir}/fig_seeley_dewitt.pdf')
    plt.close()

    # Fig 4: D_F eigenvalue spectrum
    fig, ax = plt.subplots()
    nz_DF = sorted([abs(e) for e in evals_DF if abs(e) > 1e-12], reverse=True)
    nz_full = sorted([abs(e) for e in evals_full if abs(e) > 1e-12], reverse=True)
    ax.semilogy(range(len(nz_DF)), nz_DF, 'r.-', ms=3, label='$D_F^2$ eigenvalues')
    ax.semilogy(range(len(nz_full)), nz_full, 'purple', alpha=0.5, label='$D_{\\rm full}^2$ eigenvalues')
    ax.set_xlabel('Index')
    ax.set_ylabel('$|\\lambda|$ (eigenvalue of $D^2$)')
    ax.set_title('Dirac Operator Spectrum')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(f'{figdir}/fig_spectrum.pdf')
    plt.close()

    # Fig 5: Sector decomposition of D²
    fig, ax = plt.subplots(figsize=(5, 5))
    norm_L2 = np.linalg.norm(coeffs_L)
    norm_DF2 = np.linalg.norm(coeffs_DF)
    norm_cross = np.linalg.norm(np.array(coeffs_full) - np.array(coeffs_L) - np.array(coeffs_DF))
    total = norm_L2 + norm_DF2 + norm_cross
    if total > 0:
        sizes = [norm_L2/total, norm_DF2/total, norm_cross/total]
    else:
        sizes = [1/3, 1/3, 1/3]
    colors = ['steelblue', 'indianred', 'mediumpurple']
    labels_pie = ['$L^2$ (gravity)', '$D_F^2$ (SM)', 'Cross (interaction)']
    ax.pie(sizes, labels=labels_pie, colors=colors, autopct='%1.0f%%', startangle=90)
    ax.set_title('Sector Decomposition of $D^2$')
    fig.savefig(f'{figdir}/fig_sector_pie.pdf')
    plt.close()

    print(f'  5 figures saved to {figdir}/')


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    figdir = '/Users/aarongreen/Desktop/Research Papers/Relational_Closure_and_Emergent Gauge_Structure/Closure v5/figures_spectral'

    import os
    os.makedirs(figdir, exist_ok=True)

    print("="*60)
    print("  B2: Spectral Action on Q₄₈ × 3_gen")
    print("="*60)

    t0 = time.time()

    print("\n  Building 3-gen system...")
    n_total, L, J, Gamma, gamma, orig_idx, conj_idx, rep, n48 = build_3gen_system(args.seed)
    print(f"  ℂ^{n_total}, Q₄₈ = {n48} vertices")

    print("\n  Building D_F (order-one + JD)...")
    D_F, df_dim, df_basis = build_df(args.seed, n_total, J, Gamma, gamma, orig_idx, conj_idx, rep)
    print(f"  D_F dimension: {df_dim}")

    # Scale D_F to match L
    norm_L = np.linalg.norm(L, 'fro')
    norm_DF = np.linalg.norm(D_F, 'fro')
    alpha = norm_L / norm_DF if norm_DF > 1e-15 else 1.0
    D_F_scaled = D_F * alpha
    print(f"  ||L|| = {norm_L:.2f}, ||D_F|| = {norm_DF:.4f}, α = {alpha:.2f}")

    # Full Dirac
    D_full = L + D_F_scaled

    # Eigenvalues of D²
    print("\n  Computing D² eigenvalues...")
    evals_L = np.linalg.eigvalsh((L @ L).real)
    evals_DF = np.linalg.eigvalsh((D_F_scaled @ D_F_scaled).real)
    evals_full = np.linalg.eigvalsh((D_full @ D_full).real)

    print(f"  L² nonzero: {np.sum(evals_L > 1e-12)}/{n_total}")
    print(f"  D_F² nonzero: {np.sum(evals_DF > 1e-12)}/{n_total}")
    print(f"  D_full² nonzero: {np.sum(evals_full > 1e-12)}/{n_total}")

    # Heat trace
    print("\n  Computing heat traces...")
    t_range = np.logspace(-4, 2, 500)

    S_L = compute_heat_trace(evals_L, t_range)
    S_DF = compute_heat_trace(evals_DF, t_range)
    S_full = compute_heat_trace(evals_full, t_range)

    # Spectral dimension
    ds_L = spectral_dimension(S_L, t_range)
    ds_DF = spectral_dimension(S_DF, t_range)
    ds_full = spectral_dimension(S_full, t_range)

    # Seeley-DeWitt
    print("\n  Extracting Seeley-DeWitt coefficients...")
    coeffs_L = extract_seeley_dewitt(S_L, t_range)
    coeffs_DF = extract_seeley_dewitt(S_DF, t_range)
    coeffs_full = extract_seeley_dewitt(S_full, t_range)

    print(f"\n  Seeley-DeWitt coefficients:")
    print(f"  {'':>12s}  {'a₀':>12s}  {'a₂':>12s}  {'a₄':>12s}")
    print(f"  {'L (gravity)':>12s}  {coeffs_L[0]:12.4f}  {coeffs_L[1]:12.4f}  {coeffs_L[2]:12.4f}")
    print(f"  {'D_F (SM)':>12s}  {coeffs_DF[0]:12.4f}  {coeffs_DF[1]:12.4f}  {coeffs_DF[2]:12.4f}")
    print(f"  {'D_full':>12s}  {coeffs_full[0]:12.4f}  {coeffs_full[1]:12.4f}  {coeffs_full[2]:12.4f}")

    # Cross terms
    cross_a0 = coeffs_full[0] - coeffs_L[0] - coeffs_DF[0]
    cross_a2 = coeffs_full[1] - coeffs_L[1] - coeffs_DF[1]
    cross_a4 = coeffs_full[2] - coeffs_L[2] - coeffs_DF[2]
    print(f"  {'Cross':>12s}  {cross_a0:12.4f}  {cross_a2:12.4f}  {cross_a4:12.4f}")

    # Sector percentages
    total_a2 = abs(coeffs_L[1]) + abs(coeffs_DF[1]) + abs(cross_a2)
    if total_a2 > 0:
        print(f"\n  a₂ sector decomposition:")
        print(f"    L² (gravity): {100*abs(coeffs_L[1])/total_a2:.1f}%")
        print(f"    D_F² (SM):    {100*abs(coeffs_DF[1])/total_a2:.1f}%")
        print(f"    Cross:        {100*abs(cross_a2)/total_a2:.1f}%")

    # d_s peaks
    margin = 20
    ds_L_peak = np.max(ds_L[margin:-margin])
    ds_DF_peak = np.max(ds_DF[margin:-margin])
    ds_full_peak = np.max(ds_full[margin:-margin])
    print(f"\n  Spectral dimension peaks:")
    print(f"    d_s(L):     {ds_L_peak:.2f}")
    print(f"    d_s(D_F):   {ds_DF_peak:.2f}")
    print(f"    d_s(D_full): {ds_full_peak:.2f}")

    # Figures
    print("\n  Generating figures...")
    make_figures(t_range, S_L, S_DF, S_full, ds_L, ds_DF, ds_full,
                 evals_L, evals_DF, evals_full, coeffs_L, coeffs_DF, coeffs_full,
                 figdir)

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.0f}s")

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Space: ℂ^{n_total} (Q₄₈ × 3_gen)")
    print(f"  D_F: {df_dim} parameters")
    print(f"  a₀ (cosmo):  L={coeffs_L[0]:.1f}, D_F={coeffs_DF[0]:.1f}, full={coeffs_full[0]:.1f}")
    print(f"  a₂ (EH+YM):  L={coeffs_L[1]:.1f}, D_F={coeffs_DF[1]:.1f}, full={coeffs_full[1]:.1f}")
    print(f"  a₄ (Higgs):  L={coeffs_L[2]:.2f}, D_F={coeffs_DF[2]:.2f}, full={coeffs_full[2]:.2f}")
    print(f"  d_s peaks: L={ds_L_peak:.1f}, D_F={ds_DF_peak:.1f}, full={ds_full_peak:.1f}")


if __name__ == '__main__':
    main()
