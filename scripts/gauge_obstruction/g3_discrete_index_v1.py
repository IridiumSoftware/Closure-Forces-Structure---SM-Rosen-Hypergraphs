#!/usr/bin/env python3
"""
g3_discrete_index_v1.py — Discrete Dirac index on Q₂₄

Defines a Dirac-type operator using the tier-parity Z₂ grading
(Set_odd = Tier B, Set_even = Tiers A∪C) and computes its index.

The Z₂-graded adjacency gives off-diagonal blocks:
  D_+: odd → even   (6 × 18 matrix)
  D_-: even → odd   (18 × 6 matrix)

The analytic index is ind(D_+) = dim ker(D_+) - dim coker(D_+)
                                = dim ker(D_+) - dim ker(D_-†)

Multiple operator definitions tested:
  1. Unweighted adjacency (structural)
  2. Born-weighted adjacency
  3. Born-weighted with ternary hyperedge structure

Usage:
  python3 g3_discrete_index_v1.py [--n_ic N] [--seed S] [--depth D]
"""

import numpy as np
import time
import argparse
from collections import defaultdict, Counter
from g3_tier_coupling_v1 import build_Q24, compose_colour, born_weight


def build_z2_dirac(q_psi, q_tier, unique_he, tier_info, n_cl, weight='unweighted'):
    """Build the Z₂-graded Dirac operator on Q₂₄.

    Z₂ grading: Set_odd = Tier B (6 vertices), Set_even = Tiers A∪C (18 vertices).

    The full adjacency A decomposes as:
        A = [[A_ee, D_-], [D_+, A_oo]]
    where D_+: odd→even (18×6), D_-: even→odd (6×18).

    Returns D_plus, D_minus, A_ee, A_oo, even_ids, odd_ids.
    """
    even_ids = sorted(tier_info['A'] + tier_info.get('C_even', tier_info.get('C', [])))
    odd_ids = sorted(tier_info['B'])

    n_even = len(even_ids)
    n_odd = len(odd_ids)

    even_idx = {v: i for i, v in enumerate(even_ids)}
    odd_idx = {v: i for i, v in enumerate(odd_ids)}

    # Build adjacency from hyperedges
    # For unweighted: A_ij = number of hyperedges containing both i and j
    # For Born-weighted: A_ij = sum of Born weights over hyperedges containing both i,j

    he_borns = {}
    for (c1, c2, c3), instances in unique_he.items():
        he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])

    A = np.zeros((n_cl, n_cl))
    for (c1, c2, c3), bw in he_borns.items():
        if weight == 'unweighted':
            w = 1.0
        elif weight == 'born':
            w = bw
        elif weight == 'born_sqrt':
            w = np.sqrt(bw)
        else:
            w = 1.0

        for i, j in [(c1, c2), (c1, c3), (c2, c3)]:
            A[i, j] += w
            A[j, i] += w

    # Extract Z₂ blocks
    # D_+: maps from odd (Tier B) to even (Tier A∪C)
    # D_-: maps from even to odd
    D_plus = np.zeros((n_even, n_odd))  # even × odd
    D_minus = np.zeros((n_odd, n_even))  # odd × even
    A_ee = np.zeros((n_even, n_even))
    A_oo = np.zeros((n_odd, n_odd))

    for i in range(n_cl):
        for j in range(n_cl):
            if A[i, j] == 0:
                continue
            i_even = i in even_idx
            j_even = j in even_idx
            i_odd = i in odd_idx
            j_odd = j in odd_idx

            if i_even and j_even:
                A_ee[even_idx[i], even_idx[j]] = A[i, j]
            elif i_odd and j_odd:
                A_oo[odd_idx[i], odd_idx[j]] = A[i, j]
            elif i_even and j_odd:
                D_plus[even_idx[i], odd_idx[j]] = A[i, j]
            elif i_odd and j_even:
                D_minus[odd_idx[i], even_idx[j]] = A[i, j]

    return D_plus, D_minus, A_ee, A_oo, even_ids, odd_ids


def compute_index(D_plus, D_minus):
    """Compute the analytic index of D_+.

    ind(D_+) = dim ker(D_+) - dim ker(D_+†)
             = dim ker(D_+) - dim ker(D_minus)  [if D_minus = D_+†]

    For a general (non-square) matrix:
    ind = dim ker(D_+) - dim coker(D_+)
        = dim ker(D_+) - dim ker(D_+†)

    D_+ is n_even × n_odd (18 × 6).
    D_+† is n_odd × n_even (6 × 18).
    """
    # SVD of D_+
    U, s, Vt = np.linalg.svd(D_plus, full_matrices=True)

    tol = 1e-10
    rank = np.sum(s > tol)
    dim_ker_D_plus = D_plus.shape[1] - rank  # null space of D_+ (right null)
    dim_ker_D_plus_dag = D_plus.shape[0] - rank  # null space of D_+† (left null)

    index = dim_ker_D_plus - dim_ker_D_plus_dag

    return index, rank, dim_ker_D_plus, dim_ker_D_plus_dag, s


def build_ternary_dirac(q_psi, q_tier, unique_he, tier_info, n_cl, weight='born'):
    """Build a Dirac operator that respects the TERNARY hyperedge structure.

    Instead of reducing to pairwise adjacency, define the operator via
    the ternary hyperedge structure directly:

    For each hyperedge (c1, c2, c3) with c_i ∈ Set_even and c_j ∈ Set_odd,
    the operator maps c_j → c_i with weight proportional to the Born weight
    times the "third vertex" contribution.

    Specifically: D_+(odd→even) has entry (even_i, odd_j) =
    Σ_{hyperedges containing both} μ × (contribution from third vertex)
    """
    even_ids = sorted(tier_info['A'] + tier_info.get('C_even', tier_info.get('C', [])))
    odd_ids = sorted(tier_info['B'])

    n_even = len(even_ids)
    n_odd = len(odd_ids)

    even_idx = {v: i for i, v in enumerate(even_ids)}
    odd_idx = {v: i for i, v in enumerate(odd_ids)}

    he_borns = {}
    for (c1, c2, c3), instances in unique_he.items():
        he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])

    # Ternary Dirac: for each hyperedge (c1,c2,c3), if exactly one vertex is odd
    # and the others are even, create a coupling between odd and even vertices
    # weighted by the Born weight

    D_plus = np.zeros((n_even, n_odd))   # even × odd
    D_minus = np.zeros((n_odd, n_even))  # odd × even

    for (c1, c2, c3), bw in he_borns.items():
        verts = [c1, c2, c3]
        even_v = [v for v in verts if v in even_idx]
        odd_v = [v for v in verts if v in odd_idx]

        if weight == 'born':
            w = bw
        elif weight == 'born_sqrt':
            w = np.sqrt(bw)
        else:
            w = 1.0

        # Couple each odd vertex to each even vertex in the same hyperedge
        for ov in odd_v:
            for ev in even_v:
                D_plus[even_idx[ev], odd_idx[ov]] += w
                D_minus[odd_idx[ov], even_idx[ev]] += w

    return D_plus, D_minus


def analyse_index(n_ic, seed, depth):
    """Full index analysis across multiple operator definitions and ICs."""

    print(f"{'='*70}")
    print(f"  DISCRETE DIRAC INDEX ON Q₂₄")
    print(f"  {n_ic} ICs, depth {depth}, seed {seed}")
    print(f"{'='*70}")

    rng_master = np.random.default_rng(seed)

    # ═══════════════════════════════════════════════════════════════════
    # OPERATOR 1: Unweighted pairwise adjacency
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*70}")
    print(f"  OPERATOR 1: Unweighted pairwise adjacency")
    print(f"{'─'*70}")

    indices_uw = []
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)
        D_p, D_m, A_ee, A_oo, ev, od = build_z2_dirac(
            q_psi, q_tier, unique_he, tier_info, n_cl, weight='unweighted')
        idx, rank, dk, dkd, s = compute_index(D_p, D_m)
        indices_uw.append(idx)

        if ic == 0:
            print(f"\n  D_+ shape: {D_p.shape} (even × odd)")
            print(f"  D_+ rank: {rank}")
            print(f"  dim ker(D_+): {dk}")
            print(f"  dim ker(D_+†): {dkd}")
            print(f"  Index: {idx}")
            print(f"  Singular values: [{', '.join(f'{x:.3f}' for x in s[:8])}]")
            print(f"  D_+ == D_-†? {np.allclose(D_p, D_m.T)}")

    print(f"\n  Index across {n_ic} ICs: {Counter(indices_uw)}")
    print(f"  (Constant = structural; varying = IC-dependent)")

    # ═══════════════════════════════════════════════════════════════════
    # OPERATOR 2: Born-weighted pairwise adjacency
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*70}")
    print(f"  OPERATOR 2: Born-weighted pairwise adjacency")
    print(f"{'─'*70}")

    indices_bw = []
    rng_master2 = np.random.default_rng(seed)
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master2.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)
        D_p, D_m, A_ee, A_oo, ev, od = build_z2_dirac(
            q_psi, q_tier, unique_he, tier_info, n_cl, weight='born')
        idx, rank, dk, dkd, s = compute_index(D_p, D_m)
        indices_bw.append(idx)

        if ic == 0:
            print(f"\n  D_+ rank: {rank}")
            print(f"  dim ker(D_+): {dk}, dim ker(D_+†): {dkd}")
            print(f"  Index: {idx}")
            print(f"  Singular values: [{', '.join(f'{x:.3f}' for x in s[:8])}]")
            print(f"  D_+ == D_-†? {np.allclose(D_p, D_m.T)}")

    print(f"\n  Index across {n_ic} ICs: {Counter(indices_bw)}")

    # ═══════════════════════════════════════════════════════════════════
    # OPERATOR 3: Ternary hyperedge Dirac (unweighted)
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*70}")
    print(f"  OPERATOR 3: Ternary hyperedge Dirac (unweighted)")
    print(f"{'─'*70}")

    indices_t_uw = []
    rng_master3 = np.random.default_rng(seed)
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master3.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)
        D_p, D_m = build_ternary_dirac(
            q_psi, q_tier, unique_he, tier_info, n_cl, weight='unweighted')
        idx, rank, dk, dkd, s = compute_index(D_p, D_m)
        indices_t_uw.append(idx)

        if ic == 0:
            print(f"\n  D_+ shape: {D_p.shape}")
            print(f"  D_+ rank: {rank}")
            print(f"  dim ker(D_+): {dk}, dim ker(D_+†): {dkd}")
            print(f"  Index: {idx}")
            print(f"  Singular values: [{', '.join(f'{x:.3f}' for x in s[:8])}]")
            print(f"  D_+ == D_-†? {np.allclose(D_p, D_m.T)}")

    print(f"\n  Index across {n_ic} ICs: {Counter(indices_t_uw)}")

    # ═══════════════════════════════════════════════════════════════════
    # OPERATOR 4: Ternary hyperedge Dirac (Born-weighted)
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*70}")
    print(f"  OPERATOR 4: Ternary hyperedge Dirac (Born-weighted)")
    print(f"{'─'*70}")

    indices_t_bw = []
    rng_master4 = np.random.default_rng(seed)
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master4.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)
        D_p, D_m = build_ternary_dirac(
            q_psi, q_tier, unique_he, tier_info, n_cl, weight='born')
        idx, rank, dk, dkd, s = compute_index(D_p, D_m)
        indices_t_bw.append(idx)

        if ic == 0:
            print(f"\n  D_+ rank: {rank}")
            print(f"  dim ker(D_+): {dk}, dim ker(D_+†): {dkd}")
            print(f"  Index: {idx}")
            print(f"  Singular values: [{', '.join(f'{x:.3f}' for x in s[:8])}]")

    print(f"\n  Index across {n_ic} ICs: {Counter(indices_t_bw)}")

    # ═══════════════════════════════════════════════════════════════════
    # OPERATOR 5: Antisymmetric Dirac (D_+ ≠ D_-†)
    # Use hyperedge ORIENTATION to break symmetry
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'─'*70}")
    print(f"  OPERATOR 5: Oriented ternary Dirac (pos1→pos3 direction)")
    print(f"{'─'*70}")

    indices_oriented = []
    rng_master5 = np.random.default_rng(seed)
    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master5.integers(0, 2**31))
        q_psi, q_tier, unique_he, vtx_map, tier_info, n_cl = build_Q24(rng, depth)

        even_ids = sorted(tier_info['A'] + tier_info.get('C_even', []))
        odd_ids = sorted(tier_info['B'])
        even_idx = {v: i for i, v in enumerate(even_ids)}
        odd_idx = {v: i for i, v in enumerate(odd_ids)}

        he_borns = {}
        for (c1, c2, c3), instances in unique_he.items():
            he_borns[(c1, c2, c3)] = np.mean([bw for d, bw in instances])

        # Oriented: pos1→pos3 creates a DIRECTED coupling
        # D_+ maps odd→even ONLY when the orientation goes odd→even
        D_p = np.zeros((len(even_ids), len(odd_ids)))
        D_m = np.zeros((len(odd_ids), len(even_ids)))

        for (c1, c2, c3), bw in he_borns.items():
            # Direction: pos1 → pos3 (source to spectator)
            if c1 in odd_idx and c3 in even_idx:
                D_p[even_idx[c3], odd_idx[c1]] += bw
            if c1 in even_idx and c3 in odd_idx:
                D_m[odd_idx[c3], even_idx[c1]] += bw
            # Also pos2 → pos3
            if c2 in odd_idx and c3 in even_idx:
                D_p[even_idx[c3], odd_idx[c2]] += bw
            if c2 in even_idx and c3 in odd_idx:
                D_m[odd_idx[c3], even_idx[c2]] += bw

        idx, rank, dk, dkd, s = compute_index(D_p, D_m)
        indices_oriented.append(idx)

        if ic == 0:
            print(f"\n  D_+ rank: {rank}")
            print(f"  dim ker(D_+): {dk}, dim ker(D_+†): {dkd}")
            print(f"  Index: {idx}")
            print(f"  D_+ == D_-†? {np.allclose(D_p, D_m.T)}")
            print(f"  Singular values: [{', '.join(f'{x:.3f}' for x in s[:8])}]")

    print(f"\n  Index across {n_ic} ICs: {Counter(indices_oriented)}")

    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  {'Operator':<40} | {'Index distribution':>25}")
    print(f"  {'─'*70}")
    for name, indices in [
        ("1: Unweighted adjacency", indices_uw),
        ("2: Born-weighted adjacency", indices_bw),
        ("3: Ternary hyperedge (unweighted)", indices_t_uw),
        ("4: Ternary hyperedge (Born)", indices_t_bw),
        ("5: Oriented ternary (Born)", indices_oriented),
    ]:
        dist = Counter(indices)
        print(f"  {name:<40} | {str(dict(dist)):>25}")

    # Key question: is any index non-zero?
    all_zero = all(i == 0 for i in indices_uw + indices_bw + indices_t_uw + indices_t_bw + indices_oriented)
    print(f"\n  All indices zero? {all_zero}")
    if all_zero:
        print(f"  → No discrete anomaly from any operator definition tested.")
        print(f"  → The Z₂ grading produces a self-adjoint decomposition")
        print(f"    (D_+ = D_-†), forcing index = 0.")


def main():
    parser = argparse.ArgumentParser(
        description="G3: Discrete Dirac index on Q₂₄")
    parser.add_argument("--n_ic", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--depth", type=int, default=6)
    args = parser.parse_args()

    t0 = time.time()
    analyse_index(args.n_ic, args.seed, args.depth)
    print(f"\n  Total time: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
