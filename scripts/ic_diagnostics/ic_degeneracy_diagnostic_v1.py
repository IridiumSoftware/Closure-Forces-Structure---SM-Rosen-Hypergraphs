"""
Diagnostic: characterize the degenerate IC seeds for Q₄₈ and Q₁₀₂.

Purpose: determine whether the 1/10 failure is measure-zero (collinear/degenerate ICs)
or a genuine second branch.

Method:
1. Reproduce the exact seeds from connes_q48_build_v1.py and q102_build_v1.py
2. Extract the degenerate IC vectors
3. Compute pairwise fidelities (|⟨ψᵢ|ψⱼ⟩|²) to detect near-collinearity
4. Compute the Gram determinant (measure of degeneracy)
5. Run 100+ seeds to get a better failure rate estimate
6. Perturb the degenerate IC to confirm it's a threshold artifact

Mathematical conventions:
  - ψ ∈ ℂ³, normalized: |ψ| = 1
  - Fidelity: |⟨ψᵢ|ψⱼ⟩|² ∈ [0, 1]
  - Gram determinant of 6 vectors in ℂ³: det(G) where G_{ij} = ⟨ψᵢ|ψⱼ⟩
    Since dim=3, rank ≤ 3, so Gram matrix is 6×6 with rank 3 generically.
    Degeneracy = multiple vectors in same direction.
"""

import numpy as np
import sys
import os

# Import the build functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from connes_q48_build_v1 import build_q48, haar_C3, fidelity, normalize
from q102_build_v1 import build_c_closed_quotient, complete_ternary


def reproduce_seeds(master_seed, offset, n_ic):
    """Reproduce the exact seed sequence used by ic_independence()."""
    rng_master = np.random.default_rng(master_seed + offset)
    seeds = []
    for _ in range(n_ic):
        s = rng_master.integers(0, 2**31)
        seeds.append(s)
    return seeds


def make_ics(seed):
    """Generate 6 Haar-random ℂ³ vectors from a seed."""
    rng = np.random.default_rng(seed)
    return {v: haar_C3(rng) for v in range(6)}


def ic_diagnostics(psi_init):
    """Compute degeneracy diagnostics for an IC set."""
    vecs = [psi_init[v] for v in range(6)]
    n = len(vecs)

    # Pairwise fidelities
    fids = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            fids[i, j] = np.abs(np.vdot(vecs[i], vecs[j]))**2

    # Max off-diagonal fidelity (closest pair)
    off_diag = fids.copy()
    np.fill_diagonal(off_diag, 0)
    max_fid = off_diag.max()
    i_max, j_max = np.unravel_index(off_diag.argmax(), off_diag.shape)

    # Gram matrix and its singular values
    V = np.array(vecs)  # 6 × 3
    G = V @ V.conj().T  # 6 × 6
    svs = np.linalg.svd(G, compute_uv=False)

    # Minimum singular value (of the 3×6 matrix V^T)
    _, s_vals, _ = np.linalg.svd(V.T)
    min_sv = s_vals[-1] if len(s_vals) > 0 else 0

    return {
        'max_fidelity': max_fid,
        'closest_pair': (i_max, j_max),
        'gram_svs': svs,
        'min_sv_VT': min_sv,
        'fidelity_matrix': fids,
    }


def main():
    print("=" * 70)
    print("  IC DEGENERACY DIAGNOSTIC")
    print("=" * 70)

    # ── Part 1: Reproduce the degenerate seeds ──
    print("\n── Part 1: Reproduce degenerate seeds ──\n")

    # Q₄₈ seeds (offset 5000)
    q48_seeds = reproduce_seeds(0, 5000, 10)
    print(f"Q₄₈ seeds: {q48_seeds}")

    # Q₁₀₂ seeds (offset 9000)
    q102_seeds = reproduce_seeds(0, 9000, 10)
    print(f"Q₁₀₂ seeds: {q102_seeds}")

    # The degenerate ones (index 5 for Q₄₈, index 4 for Q₁₀₂)
    q48_degen_seed = q48_seeds[5]
    q102_degen_seed = q102_seeds[4]
    print(f"\nQ₄₈ degenerate seed: index 5, seed = {q48_degen_seed}")
    print(f"Q₁₀₂ degenerate seed: index 4, seed = {q102_degen_seed}")

    # ── Part 2: Characterize the degenerate ICs ──
    print("\n── Part 2: Characterize degenerate ICs ──\n")

    for label, seed, good_seed in [
        ("Q₄₈ degenerate", q48_degen_seed, q48_seeds[0]),
        ("Q₁₀₂ degenerate", q102_degen_seed, q102_seeds[0]),
        ("Q₄₈ generic", q48_seeds[0], None),
        ("Q₁₀₂ generic", q102_seeds[0], None),
    ]:
        psi = make_ics(seed)
        diag = ic_diagnostics(psi)
        print(f"  {label} (seed={seed}):")
        print(f"    Max pairwise fidelity: {diag['max_fidelity']:.6f}"
              f"  (pair {diag['closest_pair']})")
        print(f"    Gram SVs (top 6): {np.round(diag['gram_svs'][:6], 4)}")
        print(f"    Min SV of V^T: {diag['min_sv_VT']:.6f}")
        print()

    # ── Part 3: Run large-N test ──
    print("\n── Part 3: Large-N IC test (200 seeds) ──\n")

    n_test = 200
    rng_large = np.random.default_rng(42)

    # Q₄₈
    q48_counts = []
    q48_degen_info = []
    for i in range(n_test):
        s = rng_large.integers(0, 2**31)
        psi = make_ics(s)
        Q = build_q48(psi, depth=5)
        q48_counts.append(Q['n_cl'])
        if Q['n_cl'] != 48:
            diag = ic_diagnostics(psi)
            q48_degen_info.append((i, s, Q['n_cl'], diag['max_fidelity'],
                                   diag['closest_pair']))

    n48 = sum(1 for c in q48_counts if c == 48)
    print(f"  Q₄₈: {n48}/{n_test} give 48 ({100*n48/n_test:.1f}%)")
    unique_counts = sorted(set(q48_counts))
    for uc in unique_counts:
        cnt = sum(1 for c in q48_counts if c == uc)
        print(f"    |Q| = {uc}: {cnt} times")
    if q48_degen_info:
        print(f"  Degenerate cases:")
        for (idx, seed, ncl, mf, pair) in q48_degen_info:
            print(f"    IC #{idx} seed={seed}: |Q|={ncl}, max_fid={mf:.6f}, pair={pair}")

    print()

    # Q₁₀₂
    q102_counts = []
    q102_degen_info = []
    for i in range(n_test):
        s = rng_large.integers(0, 2**31)
        psi = make_ics(s)
        Q = build_c_closed_quotient(complete_ternary(6), psi, depth=4)
        q102_counts.append(Q['n_cl'])
        if Q['n_cl'] != 102:
            diag = ic_diagnostics(psi)
            q102_degen_info.append((i, s, Q['n_cl'], diag['max_fidelity'],
                                    diag['closest_pair']))

    n102 = sum(1 for c in q102_counts if c == 102)
    print(f"  Q₁₀₂: {n102}/{n_test} give 102 ({100*n102/n_test:.1f}%)")
    unique_counts = sorted(set(q102_counts))
    for uc in unique_counts:
        cnt = sum(1 for c in q102_counts if c == uc)
        print(f"    |Q| = {uc}: {cnt} times")
    if q102_degen_info:
        print(f"  Degenerate cases:")
        for (idx, seed, ncl, mf, pair) in q102_degen_info:
            print(f"    IC #{idx} seed={seed}: |Q|={ncl}, max_fid={mf:.6f}, pair={pair}")

    # ── Part 4: Threshold sensitivity ──
    print("\n\n── Part 4: Threshold sensitivity on degenerate IC ──\n")

    psi_degen = make_ics(q48_degen_seed)
    diag = ic_diagnostics(psi_degen)
    print(f"  Q₄₈ degenerate IC fidelity matrix:")
    for i in range(6):
        row = "    "
        for j in range(6):
            row += f"{diag['fidelity_matrix'][i,j]:.4f} "
        print(row)

    # Check: does a tiny perturbation fix it?
    print(f"\n  Perturbing degenerate IC (pair {diag['closest_pair']})...")
    pair = diag['closest_pair']
    for eps in [0.0, 0.001, 0.01, 0.05, 0.1]:
        psi_pert = dict(psi_degen)
        if eps > 0:
            rng_pert = np.random.default_rng(999)
            noise = eps * (rng_pert.standard_normal(3) + 1j * rng_pert.standard_normal(3))
            psi_pert[pair[1]] = normalize(psi_degen[pair[1]] + noise)
        Q = build_q48(psi_pert, depth=5)
        new_diag = ic_diagnostics(psi_pert)
        print(f"    eps={eps:.3f}: |Q|={Q['n_cl']}, "
              f"max_fid={new_diag['max_fidelity']:.6f}")

    print("\n" + "=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
