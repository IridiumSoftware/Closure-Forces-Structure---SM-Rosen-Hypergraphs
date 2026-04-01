#!/usr/bin/env python3
"""
g1_gravity_spectral_v1.py — Gravitational dynamics from spectral action on Q₁₀₂

Computes:
  1. Spectral action decomposition on Q₁₀₂: a₀, a₂, a₄ by sector (L, D_F, cross)
  2. Local curvature: vertex-resolved [D²]_{vv} decomposed into L² + D_F² + cross
  3. Ollivier-Ricci curvature on Q₁₀₂ edges (independent geometric quantity)
  4. Correlation: local spectral curvature vs Ollivier-Ricci
  5. Discrete Einstein equation: δTr(D⁴)/δL_{ij} structure

Key result from S97: a₂ = Tr(D²) = Tr(L²) + Tr(D_F²) = Tr(L²) + const.
So the gravitational content at a₂ level is entirely Tr(L²) = graph geometry.
Interaction enters at a₄ through C = LD_F + D_FL.

Usage:
  python3 g1_gravity_spectral_v1.py [--seed S]
"""

import numpy as np
import argparse
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from q102_build_v1 import (
    build_c_closed_quotient, complete_ternary, haar_C3, fidelity,
    build_J, build_multiway
)
from q102_orderone_v1 import (
    j_compatible_triplets, build_representation,
    incremental_order_one
)


def build_laplacian(Q):
    """Build unnormalised graph Laplacian from hyperedges."""
    n = Q['n_cl']
    adj = np.zeros((n, n))
    for c1, c2, c3 in Q['q_he']:
        adj[c1,c2] = adj[c2,c1] = 1
        adj[c1,c3] = adj[c3,c1] = 1
        adj[c2,c3] = adj[c3,c2] = 1
    np.fill_diagonal(adj, 0)
    deg = adj.sum(axis=1)
    L = np.diag(deg) - adj
    return L, adj, deg


def build_sample_DF(Q, psi_init):
    """Build a representative D_F on Q₁₀₂."""
    n = Q['n_cl']
    J, j_map = build_J(Q)
    gamma = np.array([1.0 if Q['cl_origin'][c]=='orig_only' else -1.0 for c in range(n)])
    orig_idx = [c for c in range(n) if gamma[c] > 0]
    conj_idx = [c for c in range(n) if gamma[c] < 0]

    triplets, v2c, v2f = j_compatible_triplets(Q, J, gamma)
    rep = build_representation(Q, triplets, v2c)
    oo_basis, oo_dim = incremental_order_one(n, orig_idx, conj_idx, rep, J)

    if oo_dim == 0:
        return None, None, gamma, J, orig_idx, conj_idx, 0

    # JD = +DJ constraint
    jd_rows = []
    for k in range(oo_dim):
        M = oo_basis[k].reshape(len(conj_idx), len(orig_idx))
        D_k = np.zeros((n, n), dtype=np.complex128)
        ci_arr = np.array(conj_idx); oi_arr = np.array(orig_idx)
        D_k[np.ix_(ci_arr, oi_arr)] = M
        D_k[np.ix_(oi_arr, ci_arr)] = M.T
        jd_rows.append((J @ D_k - D_k @ J).real.flatten())

    JD_mat = np.array(jd_rows)
    G_jd = JD_mat @ JD_mat.T
    eigvals_jd, eigvecs_jd = np.linalg.eigh(G_jd)
    ker_mask = eigvals_jd < 1e-14
    final_coords = eigvecs_jd[:, ker_mask].T
    final_basis = final_coords @ oo_basis
    dim_DF = final_basis.shape[0]

    # Build representative D_F (normalised sum of basis)
    n_conj = len(conj_idx); n_orig = len(orig_idx)
    M_rep = np.zeros((n_conj, n_orig))
    for k in range(dim_DF):
        M_rep += final_basis[k].reshape(n_conj, n_orig)
    M_rep /= np.linalg.norm(M_rep)

    D_F = np.zeros((n, n))
    ci_arr = np.array(conj_idx); oi_arr = np.array(orig_idx)
    D_F[np.ix_(ci_arr, oi_arr)] = M_rep
    D_F[np.ix_(oi_arr, ci_arr)] = M_rep.T

    return D_F, final_basis, gamma, J, orig_idx, conj_idx, dim_DF


def ollivier_ricci(adj, i, j):
    """Compute Ollivier-Ricci curvature on edge (i,j) using optimal transport."""
    n = adj.shape[0]
    d_i = adj[i].sum()
    d_j = adj[j].sum()
    if d_i == 0 or d_j == 0:
        return 0.0

    # Lazy random walk measures
    mu_i = np.zeros(n)
    mu_i[i] = 0.5
    for k in range(n):
        if adj[i,k] > 0:
            mu_i[k] = 0.5 / d_i

    mu_j = np.zeros(n)
    mu_j[j] = 0.5
    for k in range(n):
        if adj[j,k] > 0:
            mu_j[k] = 0.5 / d_j

    # Wasserstein-1 distance via optimal transport
    # Cost matrix = shortest path distances (use BFS for unweighted graph)
    from scipy.sparse.csgraph import shortest_path
    from scipy.sparse import csr_matrix
    dist = shortest_path(csr_matrix(adj), directed=False)

    # Solve optimal transport
    supp_i = np.where(mu_i > 1e-15)[0]
    supp_j = np.where(mu_j > 1e-15)[0]

    cost = dist[np.ix_(supp_i, supp_j)]
    mass_i = mu_i[supp_i]
    mass_j = mu_j[supp_j]

    # Use linear programming for exact W1
    from scipy.optimize import linprog
    ni, nj = len(supp_i), len(supp_j)
    c = cost.flatten()
    # Constraints: row sums = mass_i, col sums = mass_j
    A_eq = np.zeros((ni + nj, ni * nj))
    for ii in range(ni):
        A_eq[ii, ii*nj:(ii+1)*nj] = 1
    for jj in range(nj):
        A_eq[ni+jj, jj::nj] = 1
    b_eq = np.concatenate([mass_i, mass_j])

    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0, None), method='highs')
    W1 = res.fun if res.success else 0.0

    kappa = 1 - W1 / dist[i,j] if dist[i,j] > 0 else 0.0
    return kappa


def ollivier_ricci_all(adj):
    """Compute Ollivier-Ricci curvature for all edges using precomputed distances."""
    from scipy.sparse.csgraph import shortest_path
    from scipy.sparse import csr_matrix
    from scipy.optimize import linprog

    n = adj.shape[0]
    dist = shortest_path(csr_matrix(adj), directed=False)

    edges = []
    curvatures = []
    for i in range(n):
        for j in range(i+1, n):
            if adj[i,j] > 0:
                d_i = adj[i].sum()
                d_j = adj[j].sum()

                mu_i = np.zeros(n); mu_i[i] = 0.5
                for k in range(n):
                    if adj[i,k] > 0: mu_i[k] = 0.5 / d_i

                mu_j = np.zeros(n); mu_j[j] = 0.5
                for k in range(n):
                    if adj[j,k] > 0: mu_j[k] = 0.5 / d_j

                supp_i = np.where(mu_i > 1e-15)[0]
                supp_j = np.where(mu_j > 1e-15)[0]
                cost = dist[np.ix_(supp_i, supp_j)]
                mass_i = mu_i[supp_i]; mass_j = mu_j[supp_j]

                ni, nj = len(supp_i), len(supp_j)
                c = cost.flatten()
                A_eq = np.zeros((ni + nj, ni * nj))
                for ii in range(ni):
                    A_eq[ii, ii*nj:(ii+1)*nj] = 1
                for jj in range(nj):
                    A_eq[ni+jj, jj::nj] = 1
                b_eq = np.concatenate([mass_i, mass_j])

                res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=(0, None), method='highs')
                W1 = res.fun if res.success else 0.0
                kappa = 1 - W1 / dist[i,j] if dist[i,j] > 0 else 0.0

                edges.append((i,j))
                curvatures.append(kappa)

    return edges, curvatures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("="*60)
    print("  G1: Gravitational Dynamics from Spectral Action on Q₁₀₂")
    print("="*60)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    # Build Q₁₀₂
    print(f"\n  Building Q₁₀₂...")
    Q = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)
    n = Q['n_cl']
    print(f"  Q₁₀₂: {n} vertices")

    # Build L (graph Laplacian)
    L, adj, deg = build_laplacian(Q)
    print(f"  Edges: {int(adj.sum()//2)}")
    print(f"  Degree range: {int(deg.min())}–{int(deg.max())}, mean={deg.mean():.1f}")

    # Build D_F
    print(f"\n  Building D_F...")
    D_F, df_basis, gamma, J, orig_idx, conj_idx, dim_DF = build_sample_DF(Q, psi_init)
    print(f"  D_F dimension: {dim_DF}")
    Gamma = np.diag(gamma)

    if D_F is None:
        print("  ERROR: D_F construction failed")
        return

    # ═══════════════════════════════════════════════════════════
    # PART 1: Spectral action decomposition
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 1: Spectral Action Decomposition")
    print(f"{'='*60}")

    # Scale D_F to match L (natural scale)
    scale = np.sqrt(np.trace(L @ L) / np.trace(D_F @ D_F)) if np.trace(D_F @ D_F) > 0 else 1.0
    D_F_scaled = D_F * scale
    print(f"  Scale factor α = ||L||/||D_F|| = {scale:.2f}")

    D = L + D_F_scaled
    C = L @ D_F_scaled + D_F_scaled @ L  # cross term

    # a₀ = Tr(I) = n
    a0 = n
    # a₂ = Tr(D²)
    D2 = D @ D; L2 = L @ L; DF2 = D_F_scaled @ D_F_scaled; C2 = C @ C
    a2_L = np.trace(L2).real
    a2_DF = np.trace(DF2).real
    a2_cross = np.trace(L @ D_F_scaled + D_F_scaled @ L).real  # should be 0 by γ-orthogonality
    a2_full = np.trace(D2).real

    print(f"\n  a₀ = {a0}")
    print(f"  a₂ decomposition:")
    print(f"    Tr(L²) = {a2_L:.2f}  (gravity)")
    print(f"    Tr(D_F²) = {a2_DF:.2f}  (gauge)")
    print(f"    Tr(LD_F + D_FL) = {a2_cross:.2e}  (cross, should be 0)")
    print(f"    Tr(D²) = {a2_full:.2f}  (total)")
    print(f"    Gravity fraction: {a2_L/a2_full:.1%}")

    # a₄ = Tr(D⁴)
    D4 = D2 @ D2; L4 = L2 @ L2; DF4 = DF2 @ DF2
    a4_L = np.trace(L4).real
    a4_DF = np.trace(DF4).real
    a4_C2 = np.trace(C2).real
    a4_mixed = np.trace(L2 @ DF2 + DF2 @ L2).real
    a4_full = np.trace(D4).real

    print(f"\n  a₄ decomposition:")
    print(f"    Tr(L⁴) = {a4_L:.0f}  (gravity)")
    print(f"    Tr(D_F⁴) = {a4_DF:.2f}  (Higgs)")
    print(f"    Tr(C²) = {a4_C2:.0f}  (interaction)")
    print(f"    Tr(L²D_F²+D_F²L²) = {a4_mixed:.0f}  (mixed)")
    print(f"    Tr(D⁴) = {a4_full:.0f}  (total)")
    print(f"    Gravity: {a4_L/a4_full:.1%}, Higgs: {a4_DF/a4_full:.1%}, "
          f"Interaction: {(a4_C2+a4_mixed)/a4_full:.1%}")

    # ═══════════════════════════════════════════════════════════
    # PART 2: Local curvature from spectral action
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 2: Local Spectral Curvature")
    print(f"{'='*60}")

    # Vertex-resolved a₂: [D²]_{vv} = [L²]_{vv} + [D_F²]_{vv}
    L2_diag = np.diag(L2).real
    DF2_diag = np.diag(DF2).real
    D2_diag = np.diag(D2).real

    print(f"\n  Vertex-resolved [L²]_{'{vv}'}:")
    print(f"    Range: {L2_diag.min():.1f} – {L2_diag.max():.1f}")
    print(f"    Mean: {L2_diag.mean():.1f}, Std: {L2_diag.std():.1f}")

    # [L²]_{vv} = d_v² + d_v (for standard Laplacian L = D - A)
    # This is the "local curvature" at each vertex
    R_spectral = L2_diag  # local a₂ contribution from geometry

    # Walk overlap (from S73)
    walk_overlap = np.zeros(n)
    for v in range(n):
        neighbors_v = set(np.where(adj[v] > 0)[0])
        if len(neighbors_v) == 0:
            continue
        overlaps = []
        for u in neighbors_v:
            neighbors_u = set(np.where(adj[u] > 0)[0])
            overlaps.append(len(neighbors_v & neighbors_u) / max(len(neighbors_v), len(neighbors_u)))
        walk_overlap[v] = np.mean(overlaps)

    # Correlation
    corr_spectral_walk = np.corrcoef(R_spectral, walk_overlap)[0,1]
    print(f"\n  Correlation R_spectral vs walk_overlap: r = {corr_spectral_walk:.4f}")
    print(f"  R² = {corr_spectral_walk**2:.4f}")

    # ═══════════════════════════════════════════════════════════
    # PART 3: Ollivier-Ricci curvature
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 3: Ollivier-Ricci Curvature on Q₁₀₂")
    print(f"{'='*60}")

    print(f"  Computing Ollivier-Ricci on all edges...")
    edges, kappas = ollivier_ricci_all(adj)
    kappas = np.array(kappas)
    print(f"  Edges: {len(edges)}")
    print(f"  κ range: {kappas.min():.4f} – {kappas.max():.4f}")
    print(f"  κ mean: {kappas.mean():.4f}, std: {kappas.std():.4f}")

    # Walk overlap per edge
    walk_overlap_edges = []
    for i, j in edges:
        ni = set(np.where(adj[i] > 0)[0])
        nj = set(np.where(adj[j] > 0)[0])
        wo = len(ni & nj) / max(len(ni), len(nj)) if max(len(ni), len(nj)) > 0 else 0
        walk_overlap_edges.append(wo)
    walk_overlap_edges = np.array(walk_overlap_edges)

    corr_kappa_walk = np.corrcoef(kappas, walk_overlap_edges)[0,1]
    print(f"\n  Correlation κ_OR vs walk_overlap (edges): r = {corr_kappa_walk:.4f}")
    print(f"  R² = {corr_kappa_walk**2:.4f}  (S73 reported R²≈0.91)")

    # Edge-resolved spectral curvature: [L²]_{ij} for edges
    L2_edges = np.array([L2[i,j].real for i,j in edges])
    corr_kappa_L2 = np.corrcoef(kappas, L2_edges)[0,1]
    print(f"\n  Correlation κ_OR vs [L²]_{{ij}}: r = {corr_kappa_L2:.4f}")
    print(f"  R² = {corr_kappa_L2**2:.4f}")

    # Vertex-averaged curvature
    kappa_vertex = np.zeros(n)
    kappa_count = np.zeros(n)
    for (i,j), k in zip(edges, kappas):
        kappa_vertex[i] += k; kappa_count[i] += 1
        kappa_vertex[j] += k; kappa_count[j] += 1
    kappa_vertex_avg = np.divide(kappa_vertex, kappa_count, where=kappa_count>0, out=np.zeros(n))

    corr_spectral_OR = np.corrcoef(R_spectral, kappa_vertex_avg)[0,1]
    print(f"\n  Correlation R_spectral vs ⟨κ_OR⟩_vertex: r = {corr_spectral_OR:.4f}")
    print(f"  R² = {corr_spectral_OR**2:.4f}")

    # ═══════════════════════════════════════════════════════════
    # PART 4: Discrete Einstein equation
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  PART 4: Discrete Einstein Equation")
    print(f"{'='*60}")

    # At a₂ level: Tr(D²) = Tr(L²) + Tr(D_F²)
    # Since Tr(D_F²) = const (S97), varying L:
    # δTr(D²)/δL = 2L (matrix equation)
    # Setting this to zero gives L = 0 (trivial — empty graph)
    # → a₂ level gives NO non-trivial Einstein equation

    print(f"\n  a₂ level: δTr(D²)/δL = 2L")
    print(f"  Setting to zero: L = 0 (trivial, empty graph)")
    print(f"  → No non-trivial Einstein equation at a₂")

    # At a₄ level: Tr(D⁴) = Tr(L⁴) + Tr(D_F⁴) + Tr(C²) + Tr(L²D_F² + D_F²L²)
    # The L-dependent terms are: Tr(L⁴) + Tr(C²) + Tr(L²D_F² + D_F²L²)
    #
    # δTr(D⁴)/δL_{ij} involves:
    # δTr(L⁴)/δL_{ij} = 4[L³]_{ji}
    # δTr(C²)/δL_{ij}: C = LD_F + D_FL, so δC/δL_{ij} = e_i e_j^T D_F + D_F e_i e_j^T
    #   Tr(C δC/δL + δC/δL C) = ... complex
    #
    # Simpler: compute the gradient numerically

    print(f"\n  a₄ level: numerical gradient δTr(D⁴)/δL_{'{ij}'}")

    # Compute dTr(D^4)/dL_{ij} for each edge by finite difference
    eps = 1e-6
    grad_a4 = np.zeros((n, n))
    for i, j in edges[:50]:  # sample 50 edges for speed
        L_pert = L.copy()
        L_pert[i,j] += eps; L_pert[j,i] += eps
        L_pert[i,i] += eps; L_pert[j,j] += eps  # maintain Laplacian structure
        D_pert = L_pert + D_F_scaled
        D2_pert = D_pert @ D_pert
        a4_pert = np.trace(D2_pert @ D2_pert).real
        grad_a4[i,j] = (a4_pert - a4_full) / eps
        grad_a4[j,i] = grad_a4[i,j]

    grad_edges = np.array([grad_a4[i,j] for i,j in edges[:50]])
    print(f"  |∇a₄| range: {np.abs(grad_edges).min():.1f} – {np.abs(grad_edges).max():.1f}")
    print(f"  |∇a₄| mean: {np.abs(grad_edges).mean():.1f}")

    # Is Q₁₀₂ an extremum? Check if gradient correlates with curvature
    kappas_sample = kappas[:50]
    corr_grad_kappa = np.corrcoef(grad_edges, kappas_sample)[0,1]
    print(f"\n  Correlation ∇a₄ vs κ_OR: r = {corr_grad_kappa:.4f}")

    # Check if gradient is uniform (would mean Q₁₀₂ is a critical point of a₄
    # up to an overall rescaling)
    cv_grad = np.std(grad_edges) / np.abs(np.mean(grad_edges)) if np.abs(np.mean(grad_edges)) > 0 else float('inf')
    print(f"  CV of ∇a₄: {cv_grad:.4f}")
    print(f"  Uniform gradient (CV < 0.1): {'✓' if cv_grad < 0.1 else '✗'}")

    # The discrete "Einstein equation" is: ∇_L Tr(D⁴) = λ · L
    # (the gradient of a₄ with respect to L is proportional to L itself)
    # Check this by correlating ∇a₄ on edges with L values on edges
    L_edges = np.array([L[i,j] for i,j in edges[:50]])
    if np.std(L_edges) > 0:
        corr_grad_L = np.corrcoef(grad_edges, L_edges)[0,1]
        print(f"  Correlation ∇a₄ vs L_{'{ij}'}: r = {corr_grad_L:.4f}")

    # ═══════════════════════════════════════════════════════════
    # PART 5: Summary
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    print(f"""
  Spectral action on Q₁₀₂ (n={n}, D_F dim={dim_DF}):
    a₀ = {a0}
    a₂ = {a2_full:.1f}  (L²: {a2_L:.1f} [{a2_L/a2_full:.0%}] + D_F²: {a2_DF:.1f} [{a2_DF/a2_full:.0%}])
    a₄ = {a4_full:.0f}  (L⁴: {a4_L:.0f} [{a4_L/a4_full:.0%}] + D_F⁴: {a4_DF:.0f} [{a4_DF/a4_full:.0%}] + cross: {a4_C2+a4_mixed:.0f} [{(a4_C2+a4_mixed)/a4_full:.0%}])

  Curvature correlations:
    Walk overlap ↔ κ_OR (edges):    R² = {corr_kappa_walk**2:.3f}  (S73: R²≈0.91)
    Spectral R_v ↔ ⟨κ_OR⟩ (vertex): R² = {corr_spectral_OR**2:.3f}
    [L²]_ij ↔ κ_OR (edges):          R² = {corr_kappa_L2**2:.3f}

  Discrete Einstein equations:
    At a₂: trivial (δa₂/δL = 2L → L=0)
    At a₄: gradient CV = {cv_grad:.3f}, ∇a₄ ↔ κ_OR: r = {corr_grad_kappa:.3f}
""")


if __name__ == '__main__':
    main()
