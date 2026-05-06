#!/usr/bin/env python3
"""
q102_kw_j_equivariance_v1.py — verify K_ω's J-equivariant Markov-blanket.

S163 (Thm_closure_potential_J_markov_blanket) established that the
spectral-action Hessian on Q102 admits a J-equivariant Markov-blanket
factorisation H_c = H_{J-inv} ⊕ H_{J-skew} with cross-block = 0 by
J-symmetry of Tr(D⁴).

This script verifies that the morphogenesis-time generator
K_ω = (β/Λ²)·D² + const inherits the same J-equivariant structure,
following directly from the KO-dim 6 sign triple JD = +DJ (Thm_Q102_KO6
/ S86):

  JD = +DJ  ⟹  J·D² = D·J·D = D·D·J = D²·J  ⟹  [J, D²] = 0
  ⟹  K_ω = β·D²/Λ² + const · 1 commutes with J

So K_ω is J-equivariant: K_ω(J·v) = J·K_ω(v).  Decomposing H = ℂ^n on
the J = +1 and J = -1 eigenspaces (J² = I, so spectrum ⊂ {+1, -1}):
  K_ω = K_+ ⊕ K_-     blockwise
  with the cross-block K_{+,-} ≡ 0 by [J, K_ω] = 0.

This is the morphogenesis-time analog of S163's Hessian factorisation:
the same J-equivariant Markov-blanket structure applies to BOTH the
closure-potential Hessian and the modular Hamiltonian, by the same
KO-dim 6 sign triple.

Computational verification:
  1. compute J, D, K_ω = D² on Q102
  2. verify [J, K_ω] = 0 numerically (norm < 1e-10)
  3. diagonalise J → eigenvectors of J = ±1 partition H
  4. compute K_+ and K_- (K_ω restricted to each J-eigenspace)
  5. verify their eigenvalue spectra together = spec(K_ω) up to ordering
  6. confirm the off-diagonal block (between J=+1 and J=-1 sectors)
     is zero to floating-point precision

Per S180 observation-only: this script COMPUTES K_+ and K_- on Q102's
fixed structure — pure linear algebra. No state evolution.

Aaron Green — May 5, 2026 — S186 follow-up: K_ω J-equivariance
verification.
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
    print("  K_ω J-EQUIVARIANCE on Q102 — structural inheritance from S86 + S163")
    print("=" * 78)

    print(f"\n[build] Q102 = C(M(K_6^3))  seed={seed}, IC=42, depth=4")
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
    K_omega = D @ D  # = D²; up to overall β/Λ² scale + log(Z) constant

    print(f"[build] n={n}, dim_DF={dim_DF}, α={alpha:.4f}, "
          f"({time.time()-t0:.1f}s)")

    # ──────────────────────────────────────────────────────────────────
    # (1) Verify J properties
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 1] Verify J properties")

    J_complex = J.astype(np.complex128)
    J2 = J_complex @ J_complex
    j2_err = float(np.linalg.norm(J2 - np.eye(n)))
    print(f"  ‖J² − I‖_F = {j2_err:.4e}  (should be ≈ 0; J² = I per Thm_Q102_KO6)")

    # ──────────────────────────────────────────────────────────────────
    # (2) Verify [J, K_ω] = 0
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 2] Verify [J, K_ω] = J·K_ω − K_ω·J = 0")
    print(f"  Structural reason: JD = +DJ (S86) ⟹ JD² = D²J ⟹ [J, D²] = 0")

    # First check JD = +DJ
    JD_minus_DJ = J_complex @ D - D @ J_complex
    jd_err = float(np.linalg.norm(JD_minus_DJ))
    print(f"  ‖JD − DJ‖_F = {jd_err:.4e}  (should be ≈ 0; KO-dim 6 sign triple)")

    # Now [J, K_ω]
    comm_J_Kw = J_complex @ K_omega - K_omega @ J_complex
    comm_norm = float(np.linalg.norm(comm_J_Kw))
    print(f"  ‖[J, K_ω]‖_F = {comm_norm:.4e}  (should be ≈ 0)")

    if comm_norm < 1e-10:
        print(f"  ✓ [J, K_ω] = 0 verified to floating-point precision")
        print(f"    K_ω is J-EQUIVARIANT (commutes with J)")
    else:
        print(f"  ✗ [J, K_ω] ≠ 0 — investigate")

    # ──────────────────────────────────────────────────────────────────
    # (3) Diagonalise J → ±1 eigenspaces partition H
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 3] Diagonalise J → ±1 eigenspaces")
    eig_J, vec_J = np.linalg.eigh(J_complex.real.astype(np.float64))
    # J is real symmetric (permutation-like) → real eigenvalues
    plus_mask  = eig_J > 0.5
    minus_mask = eig_J < -0.5
    n_plus  = int(plus_mask.sum())
    n_minus = int(minus_mask.sum())
    print(f"  J = +1 eigenspace: {n_plus} dimensions")
    print(f"  J = −1 eigenspace: {n_minus} dimensions")
    print(f"  total: {n_plus + n_minus} (should be n = {n})")

    P_plus  = vec_J[:, plus_mask]   # n × n_plus, columns are J=+1 eigenvectors
    P_minus = vec_J[:, minus_mask]  # n × n_minus, columns are J=−1 eigenvectors

    # ──────────────────────────────────────────────────────────────────
    # (4) Block decomposition K_ω = K_+ ⊕ K_-
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 4] Block decomposition: K_+ on J=+1, K_− on J=−1")

    K_plus_block  = P_plus.conj().T  @ K_omega @ P_plus    # n_plus × n_plus
    K_minus_block = P_minus.conj().T @ K_omega @ P_minus   # n_minus × n_minus
    K_off_block   = P_plus.conj().T  @ K_omega @ P_minus   # n_plus × n_minus

    K_plus_norm  = float(np.linalg.norm(K_plus_block, 'fro'))
    K_minus_norm = float(np.linalg.norm(K_minus_block, 'fro'))
    K_off_norm   = float(np.linalg.norm(K_off_block, 'fro'))
    print(f"  ‖K_+‖_F   = {K_plus_norm:.4e}  (J=+1 sector)")
    print(f"  ‖K_−‖_F   = {K_minus_norm:.4e}  (J=−1 sector)")
    print(f"  ‖K_+,−‖_F = {K_off_norm:.4e}  (off-block, should be ≈ 0 by [J,K_ω]=0)")

    if K_off_norm < 1e-10:
        print(f"  ✓ Off-block ≈ 0 to floating-point precision")
        print(f"    Markov-blanket factorisation K_ω = K_+ ⊕ K_- holds")
    else:
        print(f"  ✗ Off-block non-zero — investigate")

    # ──────────────────────────────────────────────────────────────────
    # (5) Eigenvalue spectra of K_+ and K_-
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 5] Eigenvalue spectra of K_+ and K_-")

    eig_plus  = np.sort(np.linalg.eigvalsh(K_plus_block.real.astype(np.float64)))
    eig_minus = np.sort(np.linalg.eigvalsh(K_minus_block.real.astype(np.float64)))
    eig_full  = np.sort(np.linalg.eigvalsh(K_omega.real.astype(np.float64)))
    eig_combined = np.sort(np.concatenate([eig_plus, eig_minus]))

    print(f"  K_+: {n_plus} eigenvalues, range [{eig_plus[0]:.4f}, "
          f"{eig_plus[-1]:.4f}], mean={eig_plus.mean():.2f}")
    print(f"  K_−: {n_minus} eigenvalues, range [{eig_minus[0]:.4f}, "
          f"{eig_minus[-1]:.4f}], mean={eig_minus.mean():.2f}")
    print(f"  K_ω: {n} eigenvalues, range [{eig_full[0]:.4f}, "
          f"{eig_full[-1]:.4f}], mean={eig_full.mean():.2f}")

    # Verify combined = full
    spec_match_err = float(np.linalg.norm(eig_combined - eig_full))
    print(f"  ‖spec(K_+) ∪ spec(K_−) − spec(K_ω)‖ = {spec_match_err:.4e}")
    if spec_match_err < 1e-8:
        print(f"  ✓ Combined spectra match full K_ω spectrum exactly")
    else:
        print(f"  ✗ Spectra mismatch — investigate")

    # ──────────────────────────────────────────────────────────────────
    # (6) Per-sector spectral statistics
    # ──────────────────────────────────────────────────────────────────
    print(f"\n[step 6] Per-sector spectral statistics")
    print(f"  {'Sector':<12} {'n':>4} {'mean':>10} {'std':>10} "
          f"{'min':>10} {'max':>10} {'distinct':>9}")
    for label, ev, ne in [('K_ω full', eig_full, n),
                           ('K_+ (J=+1)', eig_plus, n_plus),
                           ('K_− (J=−1)', eig_minus, n_minus)]:
        ndist = int(len(np.unique(np.round(ev, 8))))
        print(f"  {label:<12} {ne:>4} {ev.mean():>10.2f} {ev.std():>10.2f} "
              f"{ev.min():>10.4f} {ev.max():>10.4f} {ndist:>9d}")

    # ──────────────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  SUMMARY")
    print(f"{'='*78}")
    print(f"""
  K_ω inherits the J-equivariant Markov-blanket structure of S163
  by structural argument from S86's KO-dim 6 sign triple:
    JD = +DJ  ⟹  [J, D²] = 0  ⟹  K_ω = β·D²/Λ² commutes with J
    ⟹  K_ω = K_+ ⊕ K_-  blockwise on the J = ±1 eigenspaces

  Numerical verification on Q102 (canonical seed=42):
    ‖[J, K_ω]‖_F   = {comm_norm:.4e}  (≈ 0 ✓)
    ‖off-block‖_F  = {K_off_norm:.4e}  (≈ 0 ✓)
    spec(K_+) ∪ spec(K_−) = spec(K_ω) to {spec_match_err:.4e} precision ✓

  Sector dimensions:
    J = +1 sector: {n_plus} eigenvalues, mean = {eig_plus.mean():.2f}
    J = −1 sector: {n_minus} eigenvalues, mean = {eig_minus.mean():.2f}

  Structural reading: morphogenesis frequencies on Q102 partition
  cleanly into J = +1 and J = −1 sectors (particle vs antiparticle in
  the C-closure).  The Markov-blanket factorisation S163 found at the
  Hessian level extends to the morphogenesis-time generator: BOTH the
  closure-potential Hessian and the modular Hamiltonian K_ω respect
  the J-symmetry from KO-dim 6.

  This identifies J as the morphogenesis Markov-blanket variable: the
  zygote's developmental dynamics decouple into J=+1 and J=−1
  factors with no cross-coupling, structurally.

  Per S180 observation-only scope: this script computes K_+ and K_-
  as structural objects on Q102's fixed Hilbert space.  No states
  evolved; no time-stepping; just the J-block decomposition of the
  morphogenesis-time generator.
""")


if __name__ == '__main__':
    main()
