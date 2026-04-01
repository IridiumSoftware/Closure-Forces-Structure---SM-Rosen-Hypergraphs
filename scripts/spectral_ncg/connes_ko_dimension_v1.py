#!/usr/bin/env python3
"""
connes_ko_dimension_v1.py — KO-Dimension of Q₄₈

Determine the KO-dimension from the sign triple (J², Jγ, JD).

Steps:
  1. Build J (C-involution) and γ candidates as explicit 48×48 matrices
  2. Test Jγ = ±γJ for each chirality candidate
  3. Search for γ satisfying Jγ = -γJ (KO-dim 6 requirement)
  4. Apply CCM classification

KO-dimension table:
  0: J²=+1, JD=+1, Jγ=+1
  2: J²=-1, JD=+1, Jγ=+1
  4: J²=-1, JD=+1, Jγ=-1
  6: J²=+1, JD=+1, Jγ=-1  ← SM target

Usage:
  python3 connes_ko_dimension_v1.py [--seed S]
"""

import numpy as np
import argparse
from collections import defaultdict
from connes_q48_build_v1 import build_q48, haar_C3, fidelity, G0_TOPO


def build_J_matrix(Q):
    """Build the 48×48 J matrix (C-involution: particle↔antiparticle)."""
    n = Q['n_cl']
    q_psi = Q['q_psi']
    J = np.zeros((n, n))

    for c in range(n):
        psi_c = np.conj(q_psi[c])
        for c2 in range(n):
            if fidelity(psi_c, q_psi[c2]) > 0.999:
                J[c, c2] = 1
                break

    return J


def build_gamma_candidates(Q):
    """Build several chirality candidates as diagonal matrices."""
    n = Q['n_cl']
    q_tier = Q['q_tier']
    cl_origin = Q['cl_origin']

    candidates = {}

    # γ₁: tier-parity. +1 = A∪C (even/singlet), -1 = B (odd/doublet)
    g1 = np.array([-1 if q_tier[c] == 'B' else 1 for c in range(n)], dtype=float)
    candidates['tier_parity'] = g1

    # γ₂: C-parity (sector sign). +1 = original, -1 = conjugate
    g2 = np.array([1 if cl_origin[c] == 'orig_only' else -1 for c in range(n)], dtype=float)
    candidates['sector_sign'] = g2

    # γ₃: composite = tier_parity × sector_sign
    # This flips sign between particle and antiparticle within each tier
    g3 = g1 * g2
    candidates['tier_x_sector'] = g3

    # γ₄: pure sector with tier B flipped
    # +1 if (orig AND singlet) OR (conj AND doublet)
    # -1 if (orig AND doublet) OR (conj AND singlet)
    # This gives Jγ₄(v) = γ₄(J(v)): J swaps orig↔conj, so
    # γ₄(J(v)): if v is orig-singlet → J(v) is conj-singlet → γ₄ = -1 ≠ γ₄(v) = +1 ✓
    g4 = np.zeros(n)
    for c in range(n):
        is_orig = cl_origin[c] == 'orig_only'
        is_singlet = q_tier[c] != 'B'
        if (is_orig and is_singlet) or (not is_orig and not is_singlet):
            g4[c] = 1
        else:
            g4[c] = -1
    candidates['chiral_candidate'] = g4

    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()

    print("="*60)
    print("  KO-Dimension of Q₄₈")
    print("="*60)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}
    Q = build_q48(psi_init, depth=5)
    n = Q['n_cl']
    print(f"\n  Q₄₈: {n} vertices")

    # ─── Step 1: Build J ───
    print(f"\n{'─'*60}")
    print(f"  STEP 1: Build J (C-involution matrix)")
    print(f"{'─'*60}")

    J = build_J_matrix(Q)
    # J should be a permutation matrix
    row_sums = J.sum(axis=1)
    col_sums = J.sum(axis=0)
    print(f"  J shape: {J.shape}")
    print(f"  Row sums: min={row_sums.min()}, max={row_sums.max()} (should be 1)")
    print(f"  Col sums: min={col_sums.min()}, max={col_sums.max()} (should be 1)")
    print(f"  Is permutation: {np.allclose(row_sums, 1) and np.allclose(col_sums, 1)}")

    # Check J² = ε
    J2 = J @ J
    j2_diag = np.diag(J2)
    j2_is_identity = np.allclose(J2, np.eye(n))
    j2_is_minus = np.allclose(J2, -np.eye(n))
    print(f"\n  J² = I: {j2_is_identity}")
    print(f"  J² = -I: {j2_is_minus}")
    if j2_is_identity:
        print(f"  ε(J²) = +1 → KO-dim ∈ {{0, 6, 7, 1}}")
    elif j2_is_minus:
        print(f"  ε(J²) = -1 → KO-dim ∈ {{2, 3, 4, 5}}")
    else:
        print(f"  J² is neither ±I!")
        print(f"  J² diagonal: {j2_diag[:10]}...")
        # Check if J is the right permutation
        fixed = np.sum(np.diag(J) > 0.5)
        print(f"  Fixed points of J: {fixed}")

    # ─── Step 2: Test Jγ for each candidate ───
    print(f"\n{'─'*60}")
    print(f"  STEP 2: Test Jγ = ±γJ for chirality candidates")
    print(f"{'─'*60}")

    gammas = build_gamma_candidates(Q)

    for name, g in gammas.items():
        G = np.diag(g)
        JG = J @ G
        GJ = G @ J  # Note: G is diagonal, so GJ[i,j] = g[i] * J[i,j]

        # Check γ² = 1
        g_squared = np.allclose(g * g, np.ones(n))

        # Check Jγ = +γJ or Jγ = -γJ
        comm = JG - GJ  # [J, γ]
        anticomm = JG + GJ  # {J, γ}

        comm_norm = np.linalg.norm(comm, 'fro')
        anticomm_norm = np.linalg.norm(anticomm, 'fro')

        # Even/odd split
        n_plus = int(np.sum(g > 0))
        n_minus = int(np.sum(g < 0))

        print(f"\n  γ = {name}: (+1: {n_plus}, -1: {n_minus})")
        print(f"    γ² = 1: {g_squared}")
        print(f"    ||[J, γ]|| = {comm_norm:.6f}  (= 0 means Jγ = +γJ)")
        print(f"    ||{{J, γ}}|| = {anticomm_norm:.6f}  (= 0 means Jγ = -γJ)")

        if comm_norm < 1e-10:
            print(f"    → Jγ = +γJ (ε'' = +1) → KO-dim ∈ {{0, 2}}")
        elif anticomm_norm < 1e-10:
            print(f"    → Jγ = -γJ (ε'' = -1) → KO-dim ∈ {{4, 6}} ← includes SM target!")
        else:
            print(f"    → Neither commutes nor anticommutes")

    # ─── Step 3: Detailed analysis of best candidate ───
    print(f"\n{'─'*60}")
    print(f"  STEP 3: Detailed Analysis of Best Candidates")
    print(f"{'─'*60}")

    # For each candidate with Jγ = -γJ, check the subspace structure
    for name, g in gammas.items():
        G = np.diag(g)
        anticomm_norm = np.linalg.norm(J @ G + G @ J, 'fro')
        if anticomm_norm > 1e-10:
            continue

        print(f"\n  *** γ = {name} gives Jγ = -γJ (KO-dim 6 candidate!) ***")
        plus_idx = [c for c in range(n) if g[c] > 0]
        minus_idx = [c for c in range(n) if g[c] < 0]

        # How does J map between + and - subspaces?
        # Jγ = -γJ means: if γ(v) = +1, then γ(J(v)) = -1 (and vice versa)
        # So J maps + to - and - to +
        j_plus_to_minus = 0
        j_minus_to_plus = 0
        for c in plus_idx:
            j_c = np.argmax(J[c])
            if g[j_c] < 0:
                j_plus_to_minus += 1
        for c in minus_idx:
            j_c = np.argmax(J[c])
            if g[j_c] > 0:
                j_minus_to_plus += 1
        print(f"  J maps + → -: {j_plus_to_minus}/{len(plus_idx)}")
        print(f"  J maps - → +: {j_minus_to_plus}/{len(minus_idx)}")

        # Tier decomposition of + and - subspaces
        tier_plus = defaultdict(int)
        tier_minus = defaultdict(int)
        for c in plus_idx:
            tier_plus[Q['q_tier'][c]] += 1
        for c in minus_idx:
            tier_minus[Q['q_tier'][c]] += 1

        print(f"\n  + subspace ({len(plus_idx)} vertices):")
        for t in sorted(tier_plus):
            orig = sum(1 for c in plus_idx if Q['q_tier'][c]==t and Q['cl_origin'][c]=='orig_only')
            conj = sum(1 for c in plus_idx if Q['q_tier'][c]==t and Q['cl_origin'][c]=='conj_only')
            print(f"    Tier {t}: {tier_plus[t]} (orig: {orig}, conj: {conj})")

        print(f"\n  - subspace ({len(minus_idx)} vertices):")
        for t in sorted(tier_minus):
            orig = sum(1 for c in minus_idx if Q['q_tier'][c]==t and Q['cl_origin'][c]=='orig_only')
            conj = sum(1 for c in minus_idx if Q['q_tier'][c]==t and Q['cl_origin'][c]=='conj_only')
            print(f"    Tier {t}: {tier_minus[t]} (orig: {orig}, conj: {conj})")

        # Physical interpretation
        # In Connes' SM: + = right-handed fermions, - = left-handed fermions (or vice versa)
        # The SM assigns:
        #   L: Q_L(3,2), L_L(1,2) — doublets are left-handed
        #   R: u_R(3,1), d_R(3,1), e_R(1,1), ν_R(1,1) — singlets are right-handed
        # So γ should give -1 to doublets, +1 to singlets (matching tier-parity)
        # BUT Jγ = -γJ requires J to FLIP chirality.
        # If J maps particle↔antiparticle AND flips chirality,
        # then: left-particle → right-antiparticle (which IS what CPT does!)

        print(f"\n  Physical interpretation:")
        print(f"  If + = right-handed, - = left-handed:")
        # Check: does + have more singlets than doublets?
        plus_singlet = tier_plus.get('A',0) + tier_plus.get('C',0)
        plus_doublet = tier_plus.get('B',0)
        minus_singlet = tier_minus.get('A',0) + tier_minus.get('C',0)
        minus_doublet = tier_minus.get('B',0)
        print(f"    + subspace: {plus_singlet} singlets, {plus_doublet} doublets")
        print(f"    - subspace: {minus_singlet} singlets, {minus_doublet} doublets")

    # ─── Step 4: KO-dimension summary ───
    print(f"\n{'─'*60}")
    print(f"  STEP 4: KO-Dimension Summary")
    print(f"{'─'*60}")

    print(f"\n  From J²:")
    if j2_is_identity:
        print(f"    J² = +1 → ε = +1")
    elif j2_is_minus:
        print(f"    J² = -1 → ε = -1")

    print(f"\n  From Jγ (best candidates):")
    for name, g in gammas.items():
        G = np.diag(g)
        comm_n = np.linalg.norm(J @ G - G @ J, 'fro')
        anti_n = np.linalg.norm(J @ G + G @ J, 'fro')
        if comm_n < 1e-10:
            sign = "+1"
        elif anti_n < 1e-10:
            sign = "-1"
        else:
            sign = "undefined"
        print(f"    γ = {name}: ε'' = {sign}")

    print(f"\n  KO-dimension table (even, with grading):")
    print(f"    KO=0: J²=+1, Jγ=+1")
    print(f"    KO=2: J²=-1, Jγ=+1")
    print(f"    KO=4: J²=-1, Jγ=-1")
    print(f"    KO=6: J²=+1, Jγ=-1  ← SM target")

    if j2_is_identity:
        for name, g in gammas.items():
            anti_n = np.linalg.norm(J @ np.diag(g) + np.diag(g) @ J, 'fro')
            if anti_n < 1e-10:
                print(f"\n  ★ KO-DIMENSION 6 ACHIEVED with γ = {name}")
                print(f"    J² = +1, Jγ = -γJ → ε = +1, ε'' = -1 → KO-dim 6")
                print(f"    (JD sign TBD — need D_F to determine ε')")


if __name__ == '__main__':
    main()
