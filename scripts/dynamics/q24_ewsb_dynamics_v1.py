#!/usr/bin/env python3
"""
q24_ewsb_dynamics_v1.py — S62 weak inconsistency resolution + inverse Born

Session 3 of the Dynamics on Q₂₄ work program.

Key questions:
  1. Why C_total ≈ 17? What determines this value algebraically?
  2. What is the global minimum of C_total(w)? Does it match the dynamical attractor?
  3. What is the Tier-B internal structure? Uniform across 6 vertices or not?
  4. Inverse Born: what is the pre-image of the EWSB pattern?
  5. What are the SU(2) rotation angles at each vertex?

Usage:
  python q24_ewsb_dynamics_v1.py [--n_ic N] [--seed S]
"""

import numpy as np
import argparse
import time
from collections import defaultdict, Counter

# ═══════════════════════════════════════════════════════════════════════════════
# CORE ALGEBRA (same as Sessions 1-2)
# ═══════════════════════════════════════════════════════════════════════════════

def cross_C3(a, b):
    return np.array([
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    ], dtype=np.complex128)

def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-15 else np.zeros_like(v)

def compose_colour(psi1, psi2):
    return normalize(np.conj(cross_C3(psi1, psi2)))

def haar_C3(rng):
    return normalize(rng.standard_normal(3) + 1j * rng.standard_normal(3))

def haar_C2(rng):
    return normalize(rng.standard_normal(2) + 1j * rng.standard_normal(2))

def born_weight(psi1, psi2, psi3, depth):
    if depth % 2 == 1:
        pt1, pt2, pt3 = np.conj(psi1), np.conj(psi2), psi3.copy()
    else:
        pt1, pt2, pt3 = psi1.copy(), psi2.copy(), np.conj(psi3)
    M = np.column_stack([pt1, pt2, pt3])
    return abs(np.linalg.det(M))**2

def fidelity(a, b):
    return abs(np.vdot(a, b))**2

_SIGMA = [
    np.array([[0, 1], [1, 0]], dtype=np.complex128),
    np.array([[0, -1j], [1j, 0]], dtype=np.complex128),
    np.array([[1, 0], [0, -1]], dtype=np.complex128),
]

def su2_rotation(theta, n_real):
    I2 = np.eye(2, dtype=np.complex128)
    sigma_dot_n = sum(n_real[k] * _SIGMA[k] for k in range(3))
    return np.cos(theta) * I2 + 1j * np.sin(theta) * sigma_dot_n

def get_rotation_params(psi1, psi2):
    """Extract SU(2) rotation axis and angle from colour pair."""
    n_hat_C3 = cross_C3(psi1, psi2)
    norm_n = np.linalg.norm(n_hat_C3)
    if norm_n < 1e-15:
        return np.array([0, 0, 1.0]), 0.0, np.eye(2, dtype=np.complex128)
    n_hat_C3 = n_hat_C3 / norm_n
    n_real = np.array([n_hat_C3[0].real, n_hat_C3[1].real, n_hat_C3[2].real])
    nr_norm = np.linalg.norm(n_real)
    if nr_norm < 1e-15:
        n_real = np.array([n_hat_C3[0].imag, n_hat_C3[1].imag, n_hat_C3[2].imag])
        nr_norm = np.linalg.norm(n_real)
        if nr_norm < 1e-15:
            return np.array([0, 0, 1.0]), 0.0, np.eye(2, dtype=np.complex128)
    n_real = n_real / nr_norm
    z12 = np.vdot(psi1, psi2)
    theta = np.angle(z12) if abs(z12) > 1e-15 else 0.0
    R = su2_rotation(theta, n_real)
    return n_real, theta, R


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₂₄ + SOURCE MAP (from Sessions 1-2)
# ═══════════════════════════════════════════════════════════════════════════════

def build_Q24(rng, depth=5):
    G0_topo = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]
    psi = {}
    for v in range(6):
        psi[v] = haar_C3(rng)
    next_vid = 6
    vertex_gen = {v: 0 for v in range(6)}
    edges = []
    for s1, s2, s3 in G0_topo:
        edges.append((0, s1, s2, s3))
    compose_cache = {}
    for gen in range(depth):
        parent_edges = [(i, e) for i, e in enumerate(edges) if e[0] == gen]
        for idx, (d, v1, v2, v3) in parent_edges:
            key = (v1, v2)
            if key not in compose_cache:
                compose_cache[key] = next_vid
                psi[next_vid] = compose_colour(psi[v1], psi[v2])
                vertex_gen[next_vid] = gen + 1
                next_vid += 1
            w = compose_cache[key]
            edges.append((gen+1, w, v2, v3))
            edges.append((gen+1, w, v1, v3))
            edges.append((gen+1, w, v1, v2))
    all_vids = sorted(psi.keys())
    n_verts = len(all_vids)
    parent_uf = list(range(n_verts))
    vid_to_idx = {v: i for i, v in enumerate(all_vids)}
    def find(x):
        while parent_uf[x] != parent_uf[parent_uf[x]]:
            parent_uf[x] = parent_uf[parent_uf[x]]
        while parent_uf[x] != x:
            parent_uf[x] = parent_uf[parent_uf[x]]
            x = parent_uf[x]
        return x
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent_uf[px] = py
    THRESHOLD = 0.999
    psi_arr = np.array([psi[v] for v in all_vids])
    G = psi_arr @ psi_arr.conj().T
    fid_matrix = np.abs(G)**2
    for i in range(n_verts):
        for j in range(i+1, n_verts):
            if fid_matrix[i, j] > THRESHOLD:
                union(i, j)
    cluster_map = defaultdict(list)
    for v in all_vids:
        cluster_map[find(vid_to_idx[v])].append(v)
    cluster_roots = sorted(cluster_map.keys())
    root_to_cid = {r: i for i, r in enumerate(cluster_roots)}
    vertex_to_cluster = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        for v in vids:
            vertex_to_cluster[v] = cid
    n_clusters = len(cluster_roots)
    q_psi = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        q_psi[cid] = psi[min(vids, key=lambda v: vertex_gen[v])]
    original_clusters = set(vertex_to_cluster[v] for v in range(6))
    gen1_clusters = set()
    for v, g in vertex_gen.items():
        if g == 1:
            c = vertex_to_cluster[v]
            if c not in original_clusters:
                gen1_clusters.add(c)
    remaining = set(range(n_clusters)) - original_clusters - gen1_clusters
    cluster_earliest_gen = {}
    for root, vids in cluster_map.items():
        cid = root_to_cid[root]
        cluster_earliest_gen[cid] = min(vertex_gen[v] for v in vids)
    q_tier = {}
    for c in original_clusters: q_tier[c] = 'A'
    for c in gen1_clusters: q_tier[c] = 'B'
    for c in remaining:
        q_tier[c] = 'C_even' if cluster_earliest_gen[c] % 2 == 0 else 'C_odd'
    unique_he = defaultdict(list)
    for depth_e, v1, v2, v3 in edges:
        c1, c2, c3 = vertex_to_cluster[v1], vertex_to_cluster[v2], vertex_to_cluster[v3]
        unique_he[(c1, c2, c3)].append((depth_e, born_weight(psi[v1], psi[v2], psi[v3], depth_e)))
    tier_info = {'A': sorted(original_clusters), 'B': sorted(gen1_clusters),
                 'C_even': sorted(c for c in remaining if cluster_earliest_gen[c] % 2 == 0),
                 'C_odd': sorted(c for c in remaining if cluster_earliest_gen[c] % 2 == 1)}
    return q_psi, q_tier, unique_he, vertex_to_cluster, tier_info, n_clusters


def build_source_map(q_psi, unique_he):
    he_born = {he: np.mean([bw for (_, bw) in unique_he[he]]) for he in unique_he}
    source_map = defaultdict(list)
    for (c1, c2, c3) in unique_he:
        w_psi = compose_colour(q_psi[c1], q_psi[c2])
        best_cid, best_fid = None, 0.0
        for cid, psi_rep in q_psi.items():
            f = fidelity(w_psi, psi_rep)
            if f > best_fid:
                best_fid = f
                best_cid = cid
        if best_fid > 0.999:
            source_map[best_cid].append((c1, c2, c3, he_born[(c1, c2, c3)]))
    return source_map, he_born


# ═══════════════════════════════════════════════════════════════════════════════
# ROTATION ANGLE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_rotation_angles(q_psi, q_tier, source_map, n_v):
    """Analyse the SU(2) rotation angles at each vertex from all source pairs."""
    print(f"\n{'='*70}")
    print(f"  SU(2) ROTATION ANGLE STRUCTURE")
    print(f"{'='*70}")

    vertex_angles = {}
    vertex_axes = {}
    vertex_rotations = {}

    for v in range(n_v):
        sources = source_map.get(v, [])
        angles = []
        axes = []
        rotations = []
        seen_pairs = set()
        for (c1, c2, c3, bw) in sources:
            pair = (c1, c2)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            n_real, theta, R = get_rotation_params(q_psi[c1], q_psi[c2])
            angles.append(theta)
            axes.append(n_real)
            rotations.append(R)
        vertex_angles[v] = angles
        vertex_axes[v] = axes
        vertex_rotations[v] = rotations

    # Per-vertex angle analysis
    print(f"\n  {'Vtx':>4} {'Tier':>6} {'#Pairs':>7} {'θ values (rad)':>40} {'Var(θ)':>10}")
    for v in range(n_v):
        tier = q_tier.get(v, '?')
        angles = vertex_angles[v]
        if angles:
            angle_str = ', '.join(f'{a:.4f}' for a in angles[:6])
            var_theta = np.var(angles) if len(angles) > 1 else 0.0
            print(f"  {v:>4d} {tier:>6} {len(angles):>7d} {angle_str:>40} {var_theta:>10.6f}")

    # Per-tier angle variance
    print(f"\n  Per-tier angle variance:")
    for t in ['A', 'B', 'C_even']:
        vids = [v for v in range(n_v) if q_tier.get(v) == t]
        vars_theta = [np.var(vertex_angles[v]) if len(vertex_angles[v]) > 1 else 0.0 for v in vids]
        print(f"    Tier {t:>6}: mean Var(θ) = {np.mean(vars_theta):.6f} ± {np.std(vars_theta):.6f}")

    # Check axis consistency at each vertex
    print(f"\n  Rotation axis consistency (are all axes parallel at each vertex?):")
    for v in range(n_v):
        axes = vertex_axes[v]
        if len(axes) > 1:
            dots = [abs(np.dot(axes[0], axes[i])) for i in range(1, len(axes))]
            min_dot = min(dots)
            tier = q_tier.get(v, '?')
            if min_dot < 0.999:
                print(f"    v{v} ({tier}): axes NOT parallel (min |dot| = {min_dot:.6f})")

    return vertex_angles, vertex_axes, vertex_rotations


# ═══════════════════════════════════════════════════════════════════════════════
# COST FUNCTION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_cost(w, q_psi, source_map, n_v):
    """Compute per-vertex and total weak consistency cost."""
    costs = {}
    for v in range(n_v):
        c = 0.0
        for (c1, c2, c3, bw) in source_map.get(v, []):
            _, _, R = get_rotation_params(q_psi[c1], q_psi[c2])
            w_desired = normalize(R @ w[c2])
            c += np.linalg.norm(w[v] - w_desired)**2
        costs[v] = c
    return costs


def compute_cost_total(w_flat, q_psi, source_map, n_v):
    """Cost function for optimization (flat input vector)."""
    w = {}
    for v in range(n_v):
        w[v] = normalize(w_flat[2*v:2*v+2].astype(np.complex128))
    costs = compute_cost(w, q_psi, source_map, n_v)
    return sum(costs.values())


# ═══════════════════════════════════════════════════════════════════════════════
# GRADIENT DESCENT ON (CP¹)²⁴
# ═══════════════════════════════════════════════════════════════════════════════

def optimize_weak(q_psi, source_map, n_v, rng, n_steps=500):
    """Best-response iteration to minimize C_total on (CP¹)²⁴.

    At each step, set w[v] = normalize(Σ R_i @ w[c2_i]) — the best response
    to the current w of all other vertices. This is equivalent to the
    Born-weighted evolution from Session 2 but framed as optimization.
    """
    w = {v: haar_C2(rng) for v in range(n_v)}

    costs_history = []
    for step in range(n_steps):
        costs = compute_cost(w, q_psi, source_map, n_v)
        c_total = sum(costs.values())
        costs_history.append(c_total)

        # Best response: w[v] = normalize(weighted sum of desired values)
        w_new = {}
        for v in range(n_v):
            sources = source_map.get(v, [])
            if not sources:
                w_new[v] = w[v].copy()
                continue
            acc = np.zeros(2, dtype=np.complex128)
            for (c1, c2, c3, bw) in sources:
                _, _, R = get_rotation_params(q_psi[c1], q_psi[c2])
                acc += bw * normalize(R @ w[c2])
            w_new[v] = normalize(acc) if np.linalg.norm(acc) > 1e-15 else w[v].copy()
        w = w_new

        if step % 100 == 0:
            print(f"    Step {step:>5d}: C_total = {c_total:.6f}")

    return w, costs_history


# ═══════════════════════════════════════════════════════════════════════════════
# ALGEBRAIC COST LOWER BOUND
# ═══════════════════════════════════════════════════════════════════════════════

def compute_algebraic_bound(q_psi, q_tier, source_map, n_v):
    """Compute the algebraic lower bound on C_total.

    For each vertex v with source pairs having rotations R_1, R_2, ..., R_k
    applied to w[c2_1], w[c2_2], ..., w[c2_k], the minimum cost at v is:

    For the SAME c2 (same source vertex), different R_i:
    min_w Σ_i ‖w - R_i @ w_c2‖² — this has an algebraic minimum when R_i differ.

    The key insight: if all rotations share the SAME AXIS (which S62 proves),
    then the inconsistency is purely angular: Σ_i |θ_v - θ_i|² where θ_i are
    the rotation angles and θ_v is the "chosen" angle.
    """
    print(f"\n{'='*70}")
    print(f"  ALGEBRAIC COST BOUND")
    print(f"{'='*70}")

    for v in range(n_v):
        tier = q_tier.get(v, '?')
        sources = source_map.get(v, [])
        if not sources:
            continue

        # Get unique source pairs and their rotation angles
        seen = set()
        angles_by_pair = []
        c2_vertices = []
        for (c1, c2, c3, bw) in sources:
            pair = (c1, c2)
            if pair in seen:
                continue
            seen.add(pair)
            _, theta, _ = get_rotation_params(q_psi[c1], q_psi[c2])
            angles_by_pair.append(theta)
            c2_vertices.append(c2)

        if len(angles_by_pair) <= 1:
            continue

        # The minimum angular cost: min_θ Σ_i (θ - θ_i)²
        # Optimal: θ* = mean(θ_i), min cost = Σ(θ_i - mean)² = k*Var(θ)
        mean_theta = np.mean(angles_by_pair)
        min_angular_cost = sum((t - mean_theta)**2 for t in angles_by_pair)

        if tier == 'B':
            print(f"  v{v:>2d} ({tier}): {len(angles_by_pair)} unique pairs, "
                  f"θ = [{', '.join(f'{a:.4f}' for a in angles_by_pair)}], "
                  f"Var(θ)={np.var(angles_by_pair):.6f}, "
                  f"min angular cost={min_angular_cost:.6f}")

    # NOTE: The actual cost is more complex because different source pairs
    # have different c2 vertices (so the w[c2] being rotated differs).
    # The angular bound is a LOWER bound on the actual cost.


# ═══════════════════════════════════════════════════════════════════════════════
# INVERSE BORN PRE-IMAGE
# ═══════════════════════════════════════════════════════════════════════════════

def inverse_born_analysis(q_psi, q_tier, source_map, n_v, rng, n_ic=100):
    """Map the pre-image of the EWSB pattern.

    Question: what fraction of random w-configurations naturally have
    C_B/C_total > threshold? How constrained is the EWSB pattern?
    """
    print(f"\n{'='*70}")
    print(f"  INVERSE BORN PRE-IMAGE ANALYSIS ({n_ic} random configs)")
    print(f"{'='*70}")

    ratios = []
    c_totals = []
    c_by_tier = defaultdict(list)

    for ic in range(n_ic):
        rng_ic = np.random.default_rng(rng.integers(0, 2**31) + ic)
        w = {v: haar_C2(rng_ic) for v in range(n_v)}
        costs = compute_cost(w, q_psi, source_map, n_v)

        c_total = sum(costs.values())
        c_totals.append(c_total)

        for t in ['A', 'B', 'C_even']:
            vids = [v for v in range(n_v) if q_tier.get(v) == t]
            c_by_tier[t].append(sum(costs[v] for v in vids))

        c_b = c_by_tier['B'][-1]
        ratio = c_b / c_total if c_total > 1e-15 else 0
        ratios.append(ratio)

    print(f"\n  Random w-configurations (no evolution):")
    print(f"    C_total: {np.mean(c_totals):.2f} ± {np.std(c_totals):.2f}")
    print(f"    C_B/C_total: {np.mean(ratios):.4f} ± {np.std(ratios):.4f}")

    # What fraction have C_B/C_total > 0.95?
    for thresh in [0.5, 0.7, 0.9, 0.95, 0.98]:
        frac = sum(1 for r in ratios if r > thresh) / len(ratios)
        print(f"    Pr(C_B/C_total > {thresh}): {frac:.4f}")

    # Per-tier cost distribution
    print(f"\n  Per-tier cost (random configs):")
    for t in ['A', 'B', 'C_even']:
        vals = c_by_tier[t]
        frac = np.mean(vals) / np.mean(c_totals)
        print(f"    {t:>6}: {np.mean(vals):.2f} ± {np.std(vals):.2f} (fraction: {frac:.4f})")

    return ratios, c_totals


# ═══════════════════════════════════════════════════════════════════════════════
# TIER-B INTERNAL STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

def analyse_tier_b_internal(q_psi, q_tier, source_map, n_v, rng, n_ic=50, n_steps=100):
    """After evolution, is cost uniform across the 6 Tier B vertices?"""
    print(f"\n{'='*70}")
    print(f"  TIER B INTERNAL STRUCTURE (after {n_steps} steps, {n_ic} ICs)")
    print(f"{'='*70}")

    tier_b_vids = [v for v in range(n_v) if q_tier.get(v) == 'B']

    # Run evolution for each IC and collect final per-vertex costs
    per_vertex_costs = defaultdict(list)

    for ic in range(n_ic):
        rng_ic = np.random.default_rng(rng.integers(0, 2**31) + ic + 5000)
        w = {v: haar_C2(rng_ic) for v in range(n_v)}

        for step in range(n_steps):
            w_new = {}
            for v in range(n_v):
                sources = source_map.get(v, [])
                if not sources:
                    w_new[v] = w[v].copy()
                    continue
                acc = np.zeros(2, dtype=np.complex128)
                for (c1, c2, c3, bw) in sources:
                    _, _, R = get_rotation_params(q_psi[c1], q_psi[c2])
                    acc += bw * normalize(R @ w[c2])
                w_new[v] = normalize(acc) if np.linalg.norm(acc) > 1e-15 else w[v].copy()
            w = w_new

        costs = compute_cost(w, q_psi, source_map, n_v)
        for v in range(n_v):
            per_vertex_costs[v].append(costs[v])

    # Report
    print(f"\n  Per-vertex cost after evolution:")
    print(f"  {'Vtx':>4} {'Tier':>6} {'Mean C':>10} {'Std C':>10} {'Frac of total':>15}")
    total_mean = sum(np.mean(per_vertex_costs[v]) for v in range(n_v))
    for v in range(n_v):
        tier = q_tier.get(v, '?')
        mean_c = np.mean(per_vertex_costs[v])
        std_c = np.std(per_vertex_costs[v])
        frac = mean_c / total_mean if total_mean > 0 else 0
        print(f"  {v:>4d} {tier:>6} {mean_c:>10.4f} {std_c:>10.4f} {frac:>15.4f}")

    # Tier B uniformity
    tier_b_means = [np.mean(per_vertex_costs[v]) for v in tier_b_vids]
    cv_b = np.std(tier_b_means) / np.mean(tier_b_means) if np.mean(tier_b_means) > 0 else 0
    print(f"\n  Tier B uniformity: CV = {cv_b:.4f}")
    print(f"  Tier B vertices: {tier_b_vids}")
    print(f"  Tier B costs: {[f'{c:.4f}' for c in tier_b_means]}")

    # Tier A and C costs
    for t in ['A', 'C_even']:
        vids = [v for v in range(n_v) if q_tier.get(v) == t]
        means = [np.mean(per_vertex_costs[v]) for v in vids]
        print(f"  Tier {t} costs: {[f'{c:.4f}' for c in means]}")

    return per_vertex_costs


# ═══════════════════════════════════════════════════════════════════════════════
# C_TOTAL ≈ 17 EXPLANATION
# ═══════════════════════════════════════════════════════════════════════════════

def explain_c_total(q_psi, q_tier, source_map, n_v, rng, n_ic=50):
    """Investigate why C_total converges to ~17."""
    print(f"\n{'='*70}")
    print(f"  WHY C_total ≈ 17?")
    print(f"{'='*70}")

    # Count source entries per tier
    for t in ['A', 'B', 'C_even']:
        vids = [v for v in range(n_v) if q_tier.get(v) == t]
        n_src = sum(len(source_map.get(v, [])) for v in vids)
        print(f"  Tier {t}: {len(vids)} vertices, {n_src} source entries, "
              f"{n_src/len(vids):.1f}/vertex")

    # For unit vectors w1, w2 on CP¹, E[‖w1 - w2‖²] = ?
    # ‖w1 - w2‖² = 2 - 2Re⟨w1|w2⟩ for unit vectors
    # If w1, w2 are independent Haar-random on CP¹: E[|⟨w1|w2⟩|²] = 1/2
    # So E[‖w1 - R@w2‖²] = 2 - 2Re⟨w1|R@w2⟩
    # For random w1, w2: E[Re⟨w1|w2⟩] = 0, so E[‖w1-w2‖²] = 2

    # After evolution, w[v] aligns with the "average" R_i @ w[c2_i].
    # The residual cost at Tier B depends on HOW MUCH the R_i disagree.

    # Compute the "disagreement matrix" at each Tier B vertex
    tier_b_vids = [v for v in range(n_v) if q_tier.get(v) == 'B']
    print(f"\n  Tier B disagreement analysis:")
    for v in tier_b_vids:
        sources = source_map.get(v, [])
        seen = {}
        for (c1, c2, c3, bw) in sources:
            pair = (c1, c2)
            if pair not in seen:
                _, theta, R = get_rotation_params(q_psi[c1], q_psi[c2])
                seen[pair] = (theta, R, c2)

        unique_pairs = list(seen.values())
        if len(unique_pairs) <= 1:
            continue

        # For each pair of rotations, compute ‖R_i - R_j‖_F
        print(f"\n    v{v} ({len(unique_pairs)} unique pairs):")
        for i in range(len(unique_pairs)):
            for j in range(i+1, len(unique_pairs)):
                theta_i, R_i, c2_i = unique_pairs[i]
                theta_j, R_j, c2_j = unique_pairs[j]
                R_diff = R_i - R_j
                frob = np.linalg.norm(R_diff, 'fro')
                # Also check if same c2
                same_c2 = 'SAME' if c2_i == c2_j else 'DIFF'
                print(f"      R_{i} vs R_{j}: ‖R_i-R_j‖_F = {frob:.4f}, "
                      f"Δθ = {abs(theta_i-theta_j):.4f}, c2: {same_c2}")

    # Compute: what is the MINIMUM POSSIBLE cost at a single Tier B vertex,
    # given its rotation structure?
    print(f"\n  Single-vertex minimum cost (numerical, 200 random w):")
    for v in tier_b_vids[:3]:
        sources = source_map.get(v, [])
        min_cost = float('inf')
        for trial in range(200):
            rng_t = np.random.default_rng(rng.integers(0, 2**31) + trial)
            w_trial = {u: haar_C2(rng_t) for u in range(n_v)}
            c = 0.0
            for (c1, c2, c3, bw) in sources:
                _, _, R = get_rotation_params(q_psi[c1], q_psi[c2])
                w_desired = normalize(R @ w_trial[c2])
                c += np.linalg.norm(w_trial[v] - w_desired)**2
            min_cost = min(min_cost, c)
        print(f"    v{v}: min C(v) over 200 trials = {min_cost:.4f} "
              f"({len(sources)} source entries)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Q₂₄ EWSB Dynamics + Inverse Born')
    parser.add_argument('--n_ic', type=int, default=50, help='ICs for analyses')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    t0 = time.time()
    rng = np.random.default_rng(args.seed)

    print("=" * 70)
    print("  Q₂₄ EWSB DYNAMICS + INVERSE BORN — SESSION 3")
    print("=" * 70)

    q_psi, q_tier, unique_he, vtc, tier_info, n_v = build_Q24(rng, depth=5)
    source_map, he_born = build_source_map(q_psi, unique_he)
    print(f"\n  Q₂₄: {n_v} vertices, {len(unique_he)} hyperedges")

    # 1. Rotation angle structure
    vertex_angles, vertex_axes, vertex_rotations = \
        analyse_rotation_angles(q_psi, q_tier, source_map, n_v)

    # 2. Algebraic cost bound
    compute_algebraic_bound(q_psi, q_tier, source_map, n_v)

    # 3. Inverse Born pre-image
    ratios, c_totals = inverse_born_analysis(q_psi, q_tier, source_map, n_v, rng, n_ic=500)

    # 4. Why C_total ≈ 17
    explain_c_total(q_psi, q_tier, source_map, n_v, rng, n_ic=50)

    # 5. Tier B internal structure
    per_vertex_costs = analyse_tier_b_internal(q_psi, q_tier, source_map, n_v, rng,
                                                n_ic=args.n_ic, n_steps=100)

    # 6. Gradient descent optimization (find true minimum)
    print(f"\n{'='*70}")
    print(f"  GRADIENT DESCENT OPTIMIZATION (3 random starts)")
    print(f"{'='*70}")
    opt_results = []
    for trial in range(3):
        rng_opt = np.random.default_rng(rng.integers(0, 2**31) + trial + 9000)
        print(f"\n  Trial {trial}:")
        w_opt, cost_hist = optimize_weak(q_psi, source_map, n_v, rng_opt,
                                          n_steps=500)
        final_cost = cost_hist[-1]
        costs_opt = compute_cost(w_opt, q_psi, source_map, n_v)
        c_b = sum(costs_opt[v] for v in range(n_v) if q_tier.get(v) == 'B')
        c_a = sum(costs_opt[v] for v in range(n_v) if q_tier.get(v) == 'A')
        c_c = sum(costs_opt[v] for v in range(n_v) if q_tier.get(v) in ('C_even', 'C_odd'))
        print(f"    Final: C_total={final_cost:.6f}, C_A={c_a:.6f}, C_B={c_b:.6f}, "
              f"C_C={c_c:.6f}")
        print(f"    C_B/C_total={c_b/final_cost:.4f}" if final_cost > 1e-15 else "")
        opt_results.append((final_cost, c_a, c_b, c_c, w_opt))

    # Summary
    elapsed = time.time() - t0
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"\n  Inverse Born (random configs, no evolution):")
    print(f"    C_B/C_total = {np.mean(ratios):.4f} ± {np.std(ratios):.4f}")
    print(f"    Pr(C_B/C_total > 0.95) = {sum(1 for r in ratios if r > 0.95)/len(ratios):.4f}")

    print(f"\n  After 100-step evolution (from Session 2):")
    print(f"    C_B/C_total → 0.989 (Born), 0.968 (Uniform)")

    print(f"\n  Gradient descent minima:")
    for i, (ct, ca, cb, cc, _) in enumerate(opt_results):
        print(f"    Trial {i}: C_total={ct:.4f}, C_B/C_total={cb/ct:.4f}")

    # Tier B internal uniformity
    tier_b_vids = [v for v in range(n_v) if q_tier.get(v) == 'B']
    tier_b_means = [np.mean(per_vertex_costs[v]) for v in tier_b_vids]
    print(f"\n  Tier B internal structure (after evolution):")
    print(f"    Per-vertex costs: {[f'{c:.4f}' for c in tier_b_means]}")
    print(f"    CV: {np.std(tier_b_means)/np.mean(tier_b_means):.4f}")

    print(f"\n  Elapsed: {elapsed:.1f}s")


if __name__ == '__main__':
    main()
