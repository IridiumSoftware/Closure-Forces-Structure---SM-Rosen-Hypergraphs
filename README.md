# Closure Forces Structure

**The Standard Model from Rosen Closure on Ternary Causal Hypergraphs**

Aaron Green | April 2026

---

## Status

This repository is the **v1.0 public release snapshot** of the paper, tagged [`v1.0-2026-04-01`](../../releases/tag/v1.0-2026-04-01). All artifacts in this repo reflect the paper as submitted on 2026-04-01. Active spec and companion-doc development continues privately; future public releases will land here as new tags (v1.1, v1.2, ...). For citation, pin to the tag.

---

## What This Is

A causal-ontology research project deriving Standard Model structure from a single principle: Rosen's closure to efficient causation, formalized as a fixed-point equation in a Cartesian Closed Category and realized in the category of ternary causal hypergraphs with double-pushout rewriting.

The main result: a chain of algebraic obstructions eliminates every decoration structure except the SM gauge group [SU(3) x SU(2) x U(1)\_Y] x SU(3)\_gen, the Born-rule probability measure, and a KO-dimension 6 spectral triple forcing the lepton sector and anomaly cancellation -- with zero free structural parameters. The 224 vacuum moduli (mass ratios, mixing angles, CP phases) are free within the spectral action minimum.

**151 scorecard entries: 130 proved unconditional, 21 computationally verified.**

## Paper

`closure_forces_structure.txt` -- the submission document in legal-style numbered rows.

## Repository Structure

```
paper/
  closure_forces_structure.txt    The paper
  README.md                       This file
  scripts/
    spec/                         CatLab.jl categorical machine proofs
    exact_verification/           Julia proofs (Rational{BigInt} exact arithmetic)
    quotient_construction/        Q_24, Q_48, Q_102 gauge-equivalence quotients
    spectral_ncg/                 KO-dim 6, CCM, cohomology, spectral action
    dynamics/                     Transfer operator, EWSB, mass gap, Born dynamics
    gauge_obstruction/            Tier parity, POVM, cluster decomposition
    higgs_generation/             Higgs identification, SU(3)_gen SSB
    gravity_product/              Curvature, Einstein eq, product structure
    vev_landscape/                VEV landscape, iterated closure, dark sector
    ic_diagnostics/               IC-independence threshold analysis
    figures/                      Figure generation scripts
```

## Evidence Types

| Type | Meaning | Example |
|------|---------|---------|
| **proof** | Deductive from axioms | Discrete obstruction (Thm 5.9b) |
| **algebraic** | Exact symbolic computation = proof | Q_48 verification in Rational{BigInt} |
| **standard** | Established result with citation | Hurwitz classification, Gleason's theorem |
| **catlab** | CatLab.jl categorical construction | Adhesivity (S25), DPO (S26) |
| **computational** | Numerical simulation (not proof) | d_s formula, curvature law |

Scripts in `exact_verification/` produce results of type **algebraic**. Scripts elsewhere produce results of type **computational** unless noted.

## Requirements

**Julia** (1.10+): CatLab.jl, AlgebraicRewriting.jl, exact arithmetic (Rational{BigInt}).

**Python** (3.10+): NumPy, SciPy. No other dependencies.

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
  title={Closure Forces Structure: The Standard Model from Rosen Closure
         on Ternary Causal Hypergraphs},
  author={Green, Aaron},
  year={2026},
  note={Available at https://github.com/IridiumSoftware/Closure-Forces-Structure---SM-Rosen-Hypergraphs}
}
```

## License

Apache License 2.0. See LICENSE.

## Contact

aaron.green@hey.com
