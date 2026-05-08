# Closure Forces Structure

**Rosen Closure and the Standard-Model Algebra**

Aaron Green | March 2026 (revised May 2026)

---

## Status

This repository is the **v1.5 public release snapshot**
(2026-05-08). All artifacts in this repo reflect the paper as
revised on 2026-05-08. Tags:

- [`v1.0-2026-04-01`](../../releases/tag/v1.0-2026-04-01) — original
  release.
- [`v1.1-2026-05-05`](../../releases/tag/v1.1-2026-05-05) — May 5
  morphogenesis-programme + McClure review revision.
- [`v1.4-2026-05-08`](../../releases/tag/v1.4-2026-05-08) — May 8
  morning revision (Lockwood red-team review, joint meta-claim
  corpus, algebraic-translation campaign, Lean track expansion,
  abstract + summary restructuring).
- `v1.5-2026-05-08` — current revision (purple-team review
  integration: §Forward research programme + §availability
  publication-discipline paragraph; title halved).

For citation, pin to the relevant tag. v1.2 and v1.3 were internal
milestones during the Lockwood revision and are not separately
tagged. Active spec and companion-doc development continues
privately; future public releases will land here as new tags
(v1.6, v1.7, ...).

## What's New in the v1.5 Revision

The v1.5 revision (May 8 evening) integrates a Grok red → blue → purple
synthesis review of v1.4 and applies a small set of paper-side polish
edits. The synopsis externally validates the v1.4 framing arc
(NCG-as-declared-completion, residual-inputs honesty, "Bedrock, not
river," four-cause redistribution), and the prioritized future-work
list maps onto existing paper structure with two paper-actionable gaps
that this release closes.

- **Title halved.** Old: "Closure Forces Structure: A Ternary Causal
  Hypergraph Realization of Rosen Closure with an NCG Bridge to
  Standard-Model Algebraic Invariants" (3 lines). New: "Closure Forces
  Structure: Rosen Closure and the Standard-Model Algebra" (2 lines).
  Drops the method-words; keeps the arc-verb load on the main title
  ("Closure Forces Structure") and uses *Algebra* as the scope-honest
  noun for what the paper actually derives — gauge group, Born rule,
  particle content, $\sin^2\theta_W = 3/8$ — not the SM full stop,
  which §endtoend + §bedrock specifically disarm.

- **§"Forward research programme"** (new closing subsection in
  §Summary, between §bedrock and §availability). Five priorities
  consolidated as a single forward map: **F1** robustness and
  adversarial testing, **F2** reduce or eliminate NCG externality,
  **F3** spacetime emergence and gravity, **F4** quantitative RG /
  Higgs / beyond-SM signatures, **F5** generality beyond ternary SM.
  Each cross-referenced to the existing gap-by-gap and weak-link-by-
  weak-link sections; the new subsection lets the paper carry its
  own forward map alongside the per-gap and per-weak-link statuses.

- **§availability publication-discipline paragraph.** §"Code and
  paper availability" extended with a paragraph committing to the
  publication discipline the v1.5 forward programme names: invitations
  for external adversarial testing (searches of larger finite quotient
  targets, non-standard composition rules $\mu$, rewrite families
  beyond $R_2$), commitments to release negative results alongside
  positive ones, explicit invitations for stress-tests of the
  realisation functor $R$ extending the obstruction chain to admissible
  adhesive categories beyond $\TCHyp$.

- **Companion (private)** — `purple_team_review_response_v1.md`.
  Records the synthesis verbatim (multi-persona: Tao opening, Bar-Yam
  + McClure synthesis, Pearl + Gorard closing, Taleb risk assessment),
  maps each priority to existing paper coverage, and identifies the
  paper-actionable items distinct from already-tracked dashboard work.

No spec entries changed; no S-IDs added or upgraded. Counts identical
to v1.4. The v1.5 changes are paper-side framing + scope-discipline
polish.

## What's New in the v1.4 Revision

The May 8 revision incorporates a structured red-team review by
Stephen Lockwood, an algebraic-translation campaign sharpening
selected `:verified` results to `:proved`, and a substantial Lean 4
track expansion. The framework's claims are also reframed to
disambiguate scope from a TOE / GUT reading.

- **Lockwood red-team revision** (4 phases, all 16 actionable
  items closed). Phase A: title softening (now naming the NCG
  bridge explicitly), abstract framing, $U(1)$ terminology
  cleanup. Phase B: $\beta$-2 typing in $\TCHyp$ unified across
  the spec; $\mathrm{Hyp}_\tau$ as the general category, $\TCHyp$
  as the $\tau = 3$ specialisation. Phase C: determinant-uniqueness
  theorem replaces Gleason invocation; Hurwitz demoted from
  load-bearing to comparison; $\mathrm{SU}(3)$ characterised as
  the $\varepsilon$-preserving subgroup of $U(3)$. Phase D: $T_2$
  functor split into $R$ (realisation) + $T$ (skeleton) at
  Definition `def:RT-functors`.

- **Joint meta-claim corpus** (24 new spec entries: schema
  `Def_joint_meta_claim` / S192 + 23 instances S193–S215).
  The schema defines the convention for representing
  triadic-coordination-engine (TCE) discoveries: structural
  observations about the spec itself, surfaced by similarity-based
  triadic-closure search, recorded as `:argued` claims. The 23
  instances span three Jaccard score-bands — high (>0.85,
  multi-angle on one object), mid (0.70–0.85, cross-framing
  invariance), and low (0.55–0.70, convergence / structural echo).

- **Algebraic-translation campaign**. S174 / S175 / S176 upgraded
  from `:verified` (computational, Float64) to `:proved`
  (algebraic, Julia `Rational{BigInt}` exact arithmetic). S176
  verifies the $\Lambda$-scale unification ratio
  $c_3 : c_2 : c_1 = 6 : 6 : 10$ and $\sin^2\theta_W = 3/8$
  exactly in $\mathbb{Q}$ — no Float64 corroboration in the
  derivation chain. Companion: `algebraic_translation_manifest_v1.md`
  (private).

- **Lean 4 track expansion**, 5 → 13 entries. The
  Markov-blanket family is now substantially Lean-verified:
  S165 (algebra-level order-one axiom as Markov blanket), S162 +
  S163 (Hessian-level spectral-action Hessian factorising into
  Friston form), S187 ($K_\omega$ modular generator
  $J$-equivariance — the morphogenesis-time generator). Plus
  spectator + cross-product algebraic identities at S29
  (`ConjugationTransmutation`), S32 (`CrossUnderLinear`), S94
  (`UniversalViability`), S143 (`WedderburnArtin`).

- **Abstract restructured**, compressed to ~1 page with bold-lead
  headliner paragraphs: (1) SM gauge group from closure, (2) NCG
  admissibility addresses anomaly cancellation, (3) quotient
  cascade $Q_{24} / Q_{51} / Q_{102}$, (4) $Q_{102}$
  morphogenesis (three-level Markov-blanket synthesis). The
  pre-existing "What is not claimed" honesty markers are retained;
  a new affirmative "What *is* claimed" closer names the
  rep-theoretic completeness of the obstruction chain and
  forecloses framework-agnostic re-encoding.

- **§ "The four causes, redistributed"** (new closing subsection
  in §Summary). Closes the rhetorical arc opened in §Introduction's
  Aristotle setup. **Efficient** cause is restored in Rosen's
  sense and made generative. **Material** cause is voided (the
  realisation functor of `def:RT-functors` shows the obstruction
  chain holds in any adhesive category with DPO dynamics
  satisfying a mild representability hypothesis — substrate is
  irrelevant). **Formal** cause is restored as load-bearing (the
  obstruction chain itself is the formal-cause derivation).
  **Final** cause is deflated and reabsorbed (no goal beyond
  closure itself; closure read teleologically, not metaphysics
  restored).

- **§ "Bedrock, not river"** (new closing subsection — scope
  disambiguation for TOE / GUT-frame red-teams). The framework is
  agnostic to the core: structural, not meaningful. It does not
  propose a substrate, a dynamics, or a set of dimensional
  values. What it supplies — and what is contended to be a
  *stronger* claim, not a weaker one — is the structural
  scaffolding any TOE or GUT must conform to if its dynamics is
  closed to efficient causation. The work is "not a destination
  but a passage."

- **Spec growth**. 195 scorecard entries (May 5) → **219**
  (May 8): **162 proved unconditional**, **30 verified**,
  **23 argued joint-meta-claim instances** (the new
  `Def_joint_meta_claim` corpus). Total spec: 279 entries
  (including 40 `:defined`, of which `Def_joint_meta_claim` /
  S192 is the schema). **9 entries** carry CatLab.jl categorical
  machine proofs; **13 entries** Lean 4 machine-verified content
  (up from 5); **3 entries** (S174 / S175 / S176) carry exact
  $\mathbb{Q}$-arithmetic algebraic proofs in Julia (up from 0
  in v1.1). Julia test suite: 72/72 pass; audit-engine:
  0 errors / 0 warnings.

### Previous Revisions

- **v1.1** (2026-05-05): Q$_{102}$ zygote / morphogenesis-programme
  reframing of G10 (continuum-limit) open problem; eleven new spec
  entries (S180–S190) characterising modular time, $K_\omega$
  spectrum, mode architecture, $\Lambda$-scan, IC-attractor
  signatures, and dual Markov-blanket structure; Sean McClure
  7-point review additions; 10 inline TikZ / pgfplots figures;
  spec 151 → 195 entries.
- **v1.0** (2026-04-01): initial public release.

## What This Is

A causal-ontology research project deriving Standard Model
*structure* from a single principle: Rosen's closure to efficient
causation, formalised as a fixed-point equation in a Cartesian
Closed Category and realised in $\TCHyp$, the category of ternary
causal hypergraphs with double-pushout rewriting.

The main result: a chain of algebraic obstructions eliminates
every decoration structure on $\TCHyp$ except the SM gauge group
$[\mathrm{SU}(3) \times \mathrm{SU}(2) \times U(1)] \times
\mathrm{SU}(3)_{\mathrm{gen}}$ (with the $U(1)$ factor identified
with hypercharge $U(1)_Y$), the Born-rule probability measure, and
a $\mathrm{KO}$-dimension 6 spectral triple forcing the lepton
sector and anomaly cancellation. **No free dimensionless structural
parameters.** The 224 vacuum moduli (mass ratios, mixing angles,
CP phases) are free within the spectral action minimum; the
dimensional energy scale $\Lambda$ remains external calibration.

The v1.4 + v1.5 revisions sharpen the *scope* of the claim. The
framework is bedrock, not river: it supplies the structural
scaffolding any closed self-maintaining system must conform to, but
does not propose substrate, dynamics, or dimensional values. Once a
substrate is selected and meaning is applied, ratios are forced
(S176's $c_3 : c_2 : c_1 = 6 : 6 : 10$ and $\sin^2\theta_W = 3/8$
exactly in $\mathbb{Q}$), patterns are forced (the obstruction
chain on $Q_{24}$, $Q_{51}$, $Q_{102}$), and the noise of
unconstrained model-building is cut through.

**219 scorecard entries: 162 proved unconditional,
30 computationally verified, 23 argued joint-meta-claim
instances.**

## Paper

`closure_forces_structure.pdf` — the v1.5 (2026-05-08) revision
(5.0 MiB, 10 figures, Appendix G, 17 sections + 7 appendices +
v1.4 closing subsections "The four causes, redistributed" and
"Bedrock, not river" + v1.5 closing subsection "Forward research
programme").

## Repository Structure

```
closure_forces_structure.pdf      The paper (v1.5, 2026-05-08)
README.md                         This file
LICENSE                           Apache 2.0
figures/                          v1.0 standalone figure-generation outputs
                                  (kept for reproducibility of the original
                                  release; v1.1+ figures are inline TikZ)
scripts/
  spec/                           CatLab.jl categorical machine proofs
  exact_verification/             Julia proofs (Rational{BigInt} exact arithmetic),
                                  including the v1.4 algebraic-translation
                                  artefacts for S174 / S175 / S176
  quotient_construction/          Q_24, Q_48, Q_102 gauge-equivalence quotients
                                  (+ Q_90 family characterisation, S178/S179)
  morphogenesis/                  v1.1+ — observation-only morphogenesis
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
| **algebraic** | Exact symbolic computation = proof | S174 / S175 / S176 in Rational{BigInt} (v1.4) |
| **lean-proved** | Lean 4 machine-verified content | Markov-blanket family S162 / S163 / S165 / S187 (v1.4) |
| **standard** | Established result with citation | Hurwitz classification, Gleason's theorem |
| **catlab** | CatLab.jl categorical construction | Adhesivity (S25), DPO (S26) |
| **computational** | Numerical simulation (not proof) | d_s formula, curvature law |
| **argued** | Structural argument, not yet machine-checked | TCE-surfaced joint meta-claims S193–S215 (v1.4) |

Scripts in `exact_verification/` produce results of type
**algebraic**. Scripts in `morphogenesis/` produce results of type
**computational** (observation-only structural verifications on
$Q_{102}$'s fixed spectral triple — no state evolution, no
time-stepping). Scripts elsewhere produce results of type
**computational** unless noted.

## Requirements

**Julia** (1.10+): CatLab.jl, AlgebraicRewriting.jl, exact
arithmetic (`Rational{BigInt}`).

**Python** (3.10+): NumPy, SciPy, numba (for the $Q_{102}$
order-one kernel construction). No other dependencies.

**Lean 4** (toolchain pinned via `lean-toolchain`): for the 13
Lean-verified entries. Mathlib used for the Markov-blanket family.

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

**Algebraic translations (v1.4, Julia `Rational{BigInt}`):**
```
julia scripts/exact_verification/g6a_c168_sm_verification_algebraic_v1.jl
julia scripts/exact_verification/g6a_closure_rep_ca_algebraic_v1.jl
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
  title={Closure Forces Structure: Rosen Closure and the
         Standard-Model Algebra},
  author={Green, Aaron},
  year={2026},
  note={Revised 2026-05-08 (v1.5). Available at
        https://github.com/IridiumSoftware/Closure-Forces-Structure---SM-Rosen-Hypergraphs}
}
```

For citation of the original v1.0 (March 2026) release, pin to
tag `v1.0-2026-04-01`. For the v1.1 revision (May 5, 2026), pin
to tag `v1.1-2026-05-05`. For the v1.4 revision (May 8 morning),
pin to tag `v1.4-2026-05-08`. For the v1.5 revision (May 8
evening, current), pin to tag `v1.5-2026-05-08`.

## License

Apache License 2.0. See LICENSE.

## Contact

aaron.green@hey.com
