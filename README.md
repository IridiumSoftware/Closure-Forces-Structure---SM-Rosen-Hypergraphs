# Closure Forces Structure

**The Standard Model from Rosen Closure on Ternary Causal Hypergraphs**

Aaron Green | March 2026 (revised May 2026)

---

## Status

This repository is the **v1.1 public release snapshot** (May 2026
revision of the original April 2026 v1.0 submission). All artifacts
in this repo reflect the paper as revised on 2026-05-05. The original
March-2026 release remains available at the
[`v1.0-2026-04-01`](../../releases/tag/v1.0-2026-04-01) tag; the
present revision is tagged
[`v1.1-2026-05-05`](../../releases/tag/v1.1-2026-05-05). For
citation, pin to the relevant tag. Active spec and companion-doc
development continues privately; future public releases will land
here as new tags (v1.2, v1.3, ...).

## What's New in the v1.1 Revision

The May revision incorporates a structured review by Sean McClure and
adds substantial material to the framework:

- **Appendix G — The Q$_{102}$ Zygote and the Morphogenesis
  Programme** (~270 lines, 7 subsections). Reframes the long-standing
  G10 (continuum-limit) open problem: Q$_{102}$ is shown to be
  *developmentally complete* for the SM (syntactic + Rosen + semantic
  closure), so it is not an approximation of a larger continuum
  object but the SM zygote itself. The right open question is
  morphogenesis on the 224-dim vacuum moduli, not the $n \to \infty$
  scaling limit. Eleven new spec entries (S180–S190) characterise the
  modular time parameter, $K_\omega$ spectrum, mode architecture,
  $\Lambda$-scan, IC-attractor signatures, and a dual Markov-blanket
  structure (geometric $J$ + algebraic $A \leftrightarrow A^\circ$).
- **Sean McClure 7-point review additions**: §1.1 (presupposition vs
  derivation), §6 (scope of the uniqueness claim), §2.1 (CCC
  necessity), §2.7 (CCC + DPO modularity), §11.4 (KO-dim 6 as
  constructed not derived), §15.3 (end-to-end derivation status).
- **10 TikZ/pgfplots figures** at the highest-impact theorem moments
  (closure cycle, ternary arity, gauge-derivation tree, family
  taxonomy, $a_4$ sector decomposition, three-level Markov-blanket
  synthesis, GUT-ratio prediction, $K_\omega$ spectrum, $\Lambda$-scan
  asymmetry, dual blanket schematic).
- **Acknowledgments** extended: Brian Crabtree (insights on closure
  dynamics), Vagid Abatchev (adversarial critiques driving
  Haskell + Lean 4 ``proofs closer to the metal''), and Sean McClure
  (review work).
- **Spec growth**: 151 scorecard entries (March release) → **195**
  (May release): **159 proved**, **33 verified**, **1 argued**.
  Julia test suite: 72/72 pass; audit-engine: 0 errors / 0 warnings.

## What This Is

A causal-ontology research project deriving Standard Model structure
from a single principle: Rosen's closure to efficient causation,
formalized as a fixed-point equation in a Cartesian Closed Category
and realized in the category of ternary causal hypergraphs with
double-pushout rewriting.

The main result: a chain of algebraic obstructions eliminates every
decoration structure except the SM gauge group [SU(3) x SU(2) x
U(1)\_Y] x SU(3)\_gen, the Born-rule probability measure, and a
KO-dimension 6 spectral triple forcing the lepton sector and anomaly
cancellation — with zero free structural parameters. The 224 vacuum
moduli (mass ratios, mixing angles, CP phases) are free within the
spectral action minimum.

The v1.1 revision reframes the continuum-limit question (G10) as
**morphogenesis on the Q$_{102}$ moduli**: Q$_{102}$ itself is
developmentally complete for the SM (Rosen-closed, syntactically
self-reproducing, semantically complete spectral triple), so the
right open question is the dynamical structure that unfolds the
zygote into observed scales — not the graph-size scaling limit.

**195 scorecard entries: 159 proved unconditional, 33 computationally
verified, 1 argued.**

## Paper

`closure_forces_structure.pdf` — the May 2026 revision (5.0 MiB,
10 figures, Appendix G, 17 sections + 7 appendices).

## Repository Structure

```
closure_forces_structure.pdf      The paper (v1.1, May 2026 revision)
README.md                         This file
LICENSE                           Apache 2.0
figures/                          v1.0 standalone figure-generation outputs
                                  (kept for reproducibility of the original
                                  release; v1.1 figures are inline TikZ)
scripts/
  spec/                           CatLab.jl categorical machine proofs
  exact_verification/             Julia proofs (Rational{BigInt} exact arithmetic)
  quotient_construction/          Q_24, Q_48, Q_102 gauge-equivalence quotients
                                  (+ Q_90 family characterisation, S178/S179)
  morphogenesis/                  v1.1 NEW — observation-only morphogenesis
                                  programme verifications (S182–S190): K_ω
                                  spectrum, mode architecture, Λ-scan,
                                  J-equivariant Markov-blanket, algebraic
                                  Markov-blanket, per-sector decomposition,
                                  per-sector Λ-scan
  spectral_ncg/                   KO-dim 6, CCM, cohomology, spectral action
  dynamics/                       Transfer operator, EWSB, mass gap, Born dynamics
  gauge_obstruction/              Tier parity, POVM, cluster decomposition
  higgs_generation/               Higgs identification, SU(3)_gen SSB
  gravity_product/                Curvature, Einstein eq, product structure
  vev_landscape/                  VEV landscape, iterated closure, dark sector
  ic_diagnostics/                 IC-independence threshold analysis
  figures/                        v1.0 figure generation scripts
```

## Evidence Types

| Type | Meaning | Example |
|------|---------|---------|
| **proof** | Deductive from axioms | Discrete obstruction (Thm 5.9b) |
| **algebraic** | Exact symbolic computation = proof | Q_48 verification in Rational{BigInt} |
| **standard** | Established result with citation | Hurwitz classification, Gleason's theorem |
| **catlab** | CatLab.jl categorical construction | Adhesivity (S25), DPO (S26) |
| **computational** | Numerical simulation (not proof) | d_s formula, curvature law |
| **argued** | Structural argument, not yet machine-checked | Φ_F eigenvalue equivalence (S183) |

Scripts in `exact_verification/` produce results of type **algebraic**.
Scripts in `morphogenesis/` produce results of type **computational**
(observation-only structural verifications on Q$_{102}$'s fixed
spectral triple — no state evolution, no time-stepping). Scripts
elsewhere produce results of type **computational** unless noted.

## Requirements

**Julia** (1.10+): CatLab.jl, AlgebraicRewriting.jl, exact arithmetic
(Rational{BigInt}).

**Python** (3.10+): NumPy, SciPy, numba (for the Q_102 order-one
kernel construction). No other dependencies.

## Reproducing Key Results

**Q_24 quotient (24 vertices):**
```
python scripts/quotient_construction/g4_three_routes_v1.py
```

**Q_48 spectral triple (KO-dim 6):**
```
python scripts/quotient_construction/connes_q48_build_v1.py --seed 0 --n_ic 10
```

**Q_102 unified Dirac operator:**
```
python scripts/quotient_construction/q102_build_v1.py --seed 0 --n_ic 10
```

**Q_90 family characterisation (S178/S179, v1.1):**
```
python scripts/quotient_construction/q90_characterization_v1.py
```

**K_ω modular Hamiltonian spectrum on Q_102 (S182, v1.1):**
```
python scripts/morphogenesis/q102_modular_hamiltonian_spectrum_v1.py
```

**Λ-scan + S125 asymptotic connection (S185, v1.1):**
```
python scripts/morphogenesis/q102_lambda_scan_v1.py
```

**K_ω J-equivariant Markov-blanket verification (S187, v1.1):**
```
python scripts/morphogenesis/q102_kw_j_equivariance_v1.py
```

**Per-sector Λ-scan particle/antiparticle asymmetry (S190, v1.1):**
```
python scripts/morphogenesis/q102_per_sector_lambda_scan_v1.py
```

**Exact verification (Julia):**
```
julia scripts/exact_verification/q48_exact_verification_v1.jl
julia scripts/exact_verification/q102_exact_verification_v1.jl
julia scripts/exact_verification/batch2_exact_verification_v3.jl
```

**IC-independence (200 seeds, threshold sensitivity):**
```
python scripts/ic_diagnostics/ic_threshold_diagnostic_v1.py
```

**CatLab categorical proofs (9 entries):**
```
julia scripts/spec/catlab_proofs.jl
```

## Citation

```
@article{green2026closure,
  title={Closure Forces Structure: The Standard Model Lagrangian from
         Rosen Closure in Ternary Causal Hypergraphs},
  author={Green, Aaron},
  year={2026},
  note={Revised May 2026. Available at
        https://github.com/IridiumSoftware/Closure-Forces-Structure---SM-Rosen-Hypergraphs}
}
```

For citation of the original v1.0 (March 2026) release, pin to tag
`v1.0-2026-04-01`. For citation of the v1.1 revision (May 2026), pin
to tag `v1.1-2026-05-05`.

## License

Apache License 2.0. See LICENSE.

## Contact

aaron.green@hey.com
