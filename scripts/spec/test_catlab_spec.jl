#!/usr/bin/env julia
# ═══════════════════════════════════════════════════════════════════════════════
# TEST SUITE — catlab_spec.jl  (stdlib only: Test)
# Structural validation: 72 testsets. See changelog.md for version history.
# ═══════════════════════════════════════════════════════════════════════════════

using Test

# ── Load the module under test ───────────────────────────────────────────────
include(joinpath(@__DIR__, "catlab_spec.jl"))
using .OntologyCatLab

# ── Collect all NamedTuple entries ───────────────────────────────────────────

const ALL_ENTRY_NAMES = Symbol[]
const ALL_ENTRIES = NamedTuple[]

for sym in names(OntologyCatLab; all=true)
    sym in (:OntologyCatLab, :eval, :include, :DEPENDENCY_GRAPH, :SCORECARD) && continue
    startswith(String(sym), '#') && continue
    obj = getfield(OntologyCatLab, sym)
    obj isa NamedTuple || continue
    haskey(obj, :kind) || continue
    push!(ALL_ENTRY_NAMES, sym)
    push!(ALL_ENTRIES, obj)
end

# ── Constants ────────────────────────────────────────────────────────────────

const VALID_KINDS   = Set([:definition, :axiom, :lemma, :proposition,
                           :theorem, :corollary, :conjecture,
                           :bridge_principle, :step, :observation])
const VALID_LOGICS  = Set([:classical, :possibilistic, :probabilistic, :bridge])
const VALID_STATUS  = Set([:proved, :proved_conditional, :verified, :sound, :open,
                           :defined, :assumed, :subsumed, :argued])
const REQUIRED_KEYS = Set([:kind, :layer, :logic, :status,
                           :uses_LEM, :uses_AC, :statement,
                           :depends_on, :ontology_ref])
const ENTRY_NAME_SET = Set(ALL_ENTRY_NAMES)
const STATUS_RANK   = Dict(:proved => 4, :proved_conditional => 3,
                           :verified => 3, :sound => 2, :argued => 2,
                           :open => 1,
                           :defined => 0, :assumed => 0, :subsumed => 0)
const LOGIC_RANK    = Dict(:classical => 1, :possibilistic => 2,
                           :probabilistic => 3, :bridge => 0)

# ── Helpers ──────────────────────────────────────────────────────────────────

function transitive_deps(nm::Symbol, graph)
    visited = Set{Symbol}()
    stack = copy(get(graph, nm, Symbol[]))
    while !isempty(stack)
        cur = pop!(stack)
        cur ∈ visited && continue
        push!(visited, cur)
        append!(stack, get(graph, cur, Symbol[]))
    end
    return visited
end

function has_cycle(graph::Dict{Symbol, Vector{Symbol}})
    visited = Dict{Symbol, Int}()
    function dfs(node)
        get(visited, node, -1) == 0 && return true
        get(visited, node, -1) == 1 && return false
        visited[node] = 0
        for dep in get(graph, node, Symbol[])
            dfs(dep) && return true
        end
        visited[node] = 1
        return false
    end
    for node in keys(graph)
        dfs(node) && return true
    end
    return false
end

layer_of(nm::Symbol) = getfield(OntologyCatLab, nm).layer

# ═══════════════════════════════════════════════════════════════════════════════
#  T01. ENTRY COUNT
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T01 — Entry count" begin
    @test length(ALL_ENTRY_NAMES) == 288  # v312: count reconciled to live spec (+8 over the stale 280; cosmology-arc growth — see task #187 registry-completion); v253: 280 (+S216); v237 baseline 279
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T02. SCHEMA — every entry has exactly 9 required fields
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T02 — Schema: 9 required fields on every entry" begin
    for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
        @test Set(keys(e)) == REQUIRED_KEYS
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T03–T11. FIELD-TYPE / ENUM CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T03 — kind ∈ valid set" begin
    for e in ALL_ENTRIES; @test e.kind ∈ VALID_KINDS; end
end

@testset "T04 — layer ∈ 1:9" begin
    for e in ALL_ENTRIES; @test 1 ≤ e.layer ≤ 9; end
end

@testset "T05 — logic ∈ valid set" begin
    for e in ALL_ENTRIES; @test e.logic ∈ VALID_LOGICS; end
end

@testset "T06 — status ∈ valid set" begin
    for e in ALL_ENTRIES; @test e.status ∈ VALID_STATUS; end
end

@testset "T07 — uses_LEM is Bool" begin
    for e in ALL_ENTRIES; @test e.uses_LEM isa Bool; end
end

@testset "T08 — uses_AC is Bool" begin
    for e in ALL_ENTRIES; @test e.uses_AC isa Bool; end
end

@testset "T09 — statement is non-empty String" begin
    for e in ALL_ENTRIES; @test e.statement isa String && !isempty(e.statement); end
end

@testset "T10 — depends_on is Vector{Symbol}" begin
    for e in ALL_ENTRIES; @test e.depends_on isa Vector{Symbol}; end
end

@testset "T11 — ontology_ref is non-empty String containing §" begin
    for e in ALL_ENTRIES
        @test e.ontology_ref isa String && occursin("§", e.ontology_ref)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T11b. NO STALE ONTOLOGY_REF VERSION STRINGS (G11)
#        Header claims all refs → ontology_v14.md.  Guard against regression.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T11b — No stale ontology_ref version strings (v10, v11, v12, v13)" begin
    for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
        @test !occursin("v10", e.ontology_ref)
        @test !occursin("v11", e.ontology_ref)
        @test !occursin("v12", e.ontology_ref)
        @test !occursin("v13", e.ontology_ref)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T12. NO uses_AC anywhere
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T12 — No entry uses Axiom of Choice" begin
    @test all(e -> e.uses_AC == false, ALL_ENTRIES)
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T13. ALL depends_on targets name existing entries
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T13 — All depends_on targets exist" begin
    for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
        for dep in e.depends_on
            @test dep ∈ ENTRY_NAME_SET
        end
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T14. DEPENDENCY_GRAPH covers every entry
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T14 — DEPENDENCY_GRAPH covers every entry" begin
    @test Set(keys(OntologyCatLab.DEPENDENCY_GRAPH)) == ENTRY_NAME_SET
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T14b. DEPENDENCY_GRAPH value targets all exist (G1)
#        Graph values could contain typos; T13/T14 don't catch this.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T14b — DEPENDENCY_GRAPH value targets all exist in ENTRY_NAME_SET" begin
    for (src, deps) in OntologyCatLab.DEPENDENCY_GRAPH
        for dep in deps
            @test dep ∈ ENTRY_NAME_SET
        end
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T15. DEPENDENCY_GRAPH values match entry depends_on
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T15 — DEPENDENCY_GRAPH matches depends_on" begin
    for nm in ALL_ENTRY_NAMES
        entry = getfield(OntologyCatLab, nm)
        graph_deps = Set(OntologyCatLab.DEPENDENCY_GRAPH[nm])
        entry_deps = Set(entry.depends_on)
        @test graph_deps == entry_deps
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T16. NO SELF-LOOPS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T16 — No entry depends on itself" begin
    for nm in ALL_ENTRY_NAMES
        @test nm ∉ getfield(OntologyCatLab, nm).depends_on
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T17. ACYCLICITY
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T17 — Dependency graph is acyclic" begin
    @test !has_cycle(OntologyCatLab.DEPENDENCY_GRAPH)
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T18. LAYER CROSS-REFERENCES — exactly 3 known cross-layer deps
#       Def_5_6 (L5)→Step_D (L6), Def_5_6 (L5)→Step_E (L6),
#       Prop_5_8 (L6)→Thm_5_11 (L7).
#       All other deps satisfy layer monotonicity.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T18 — Exactly 3 known cross-layer deps; rest monotone" begin
    violations = Tuple{Symbol,Symbol}[]
    for nm in ALL_ENTRY_NAMES
        my_layer = layer_of(nm)
        for dep in getfield(OntologyCatLab, nm).depends_on
            if layer_of(dep) > my_layer
                push!(violations, (nm, dep))
            end
        end
    end
    @test length(violations) == 4  # +1: Thm_7_6 → Cor_anomaly_cancellation (v62, B1 derived)
    vset = Set(violations)
    @test (:Def_5_6, :Step_D)   ∈ vset
    @test (:Def_5_6, :Step_E)   ∈ vset
    @test (:Prop_5_8, :Thm_5_11) ∈ vset
    @test (:Thm_7_6, :Cor_anomaly_cancellation) ∈ vset  # layer 7 → 8: NCG derivation feeds back
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T19. NO DUPLICATE DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T19 — No duplicate dependencies" begin
    for e in ALL_ENTRIES
        @test length(e.depends_on) == length(Set(e.depends_on))
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T20–T22. STATUS–KIND CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T20 — :defined status only on :definition" begin
    for e in ALL_ENTRIES
        e.status == :defined && @test e.kind == :definition
    end
end

@testset "T21 — :assumed status only on :axiom or :bridge_principle" begin
    for e in ALL_ENTRIES
        e.status == :assumed && @test e.kind ∈ (:axiom, :bridge_principle)
    end
end

@testset "T22 — Definitions never :proved" begin
    for e in ALL_ENTRIES
        e.kind == :definition && @test e.status ∉ (:proved, :proved_conditional)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T23. :defined ↔ :definition bijection
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T23 — :defined entries == :definition entries" begin
    defined_set = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :defined)
    defn_set    = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :definition)
    @test defined_set == defn_set
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T24. LAYERS 1–8 each populated
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T24 — Layers 1–8 each populated" begin
    layers = Set(e.layer for e in ALL_ENTRIES)
    for L in 1:8; @test L ∈ layers; end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T24b. LAYER 9 INTENTIONALLY UNUSED (G8)
#        Schema allows 1..9; T24 checks 1–8 populated.  Assert 9 is empty.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T24b — Layer 9 is intentionally unused" begin
    @test 9 ∉ Set(e.layer for e in ALL_ENTRIES)
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T25–T27. LAYER-SIZE SPOT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T25 — Layer 1: exactly 5 definitions" begin
    L1 = filter(e -> e.layer == 1, ALL_ENTRIES)
    @test length(L1) == 5
    @test all(e -> e.kind == :definition, L1)
end

@testset "T26 — Layer 2: exactly 2 definitions" begin
    L2 = filter(e -> e.layer == 2, ALL_ENTRIES)
    @test length(L2) == 2
end

@testset "T27 — Layer 3: 6 entries" begin
    L3 = filter(e -> e.layer == 3, ALL_ENTRIES)
    @test length(L3) == 6
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T25b. LAYER-SIZE COUNTS FOR L4–L8 (G9)
#        Pinned from catlab_spec_v14.jl.  Catches accidental adds/deletes.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T25b — Layer 4: 19 entries" begin
    L4 = filter(e -> e.layer == 4, ALL_ENTRIES)
    @test length(L4) == 19  # +3: Prop_adhesive_pushout_complement, Prop_TCHyp_colimits, Lemma_Gleason (v61)
end

@testset "T26b — Layer 5: 11 entries" begin
    L5 = filter(e -> e.layer == 5, ALL_ENTRIES)
    @test length(L5) == 12  # v225: +Obs_meta_T2_three_role_alignment (joint meta-claim, classical, layer 5 to match T₂ functor cluster)
end

@testset "T27b — Layer 6: 15 entries" begin
    L6 = filter(e -> e.layer == 6, ALL_ENTRIES)
    @test length(L6) == 15  # +1: Lemma_Hurwitz (v61)
end

@testset "T27c — Layer 7: 49 entries" begin
    L7 = filter(e -> e.layer == 7, ALL_ENTRIES)
    @test length(L7) == 49  # +1: Cor_composition_determinism (v61)
end

@testset "T27d — Layer 8: 180 entries" begin
    L8 = filter(e -> e.layer == 8, ALL_ENTRIES)
    @test length(L8) == 180  # v312: +8 (S183 Phase-2/3 φ_F-smooth arc, all layer 8)  # v253: 172 (+S216)  # v237: +3 joint meta-claims
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T28–T33. SCORECARD
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T28 — Scorecard row count" begin
    @test length(OntologyCatLab.SCORECARD) == 228  # v312: count reconciled to live spec (+8 S183 Phase-2/3 φ_F-smooth arc); v253: 220 (+S216); v237 baseline 219
end

@testset "T29 — Scorecard keys reference existing entries" begin
    for (_, row) in OntologyCatLab.SCORECARD
        @test row.key ∈ ENTRY_NAME_SET
    end
end

@testset "T30 — Scorecard logic distribution: 16 prob, 114 poss, 21 classical, 0 bridge" begin
    sc = collect(values(OntologyCatLab.SCORECARD))
    @test count(r -> r.logic == :probabilistic, sc) == 18   # v212 reverted S191
    @test count(r -> r.logic == :possibilistic, sc) == 184  # v312: +8 (S183 Phase-2/3 arc, all possibilistic); v253: 176 (+S216); v237 baseline 175
    @test count(r -> r.logic == :classical, sc) == 26  # v235: +S211 Obs_meta_categorical_foundation_richness (classical, T₂/TCHyp foundation)
    @test count(r -> r.logic == :bridge, sc) == 0  # S16 no longer bridge (v62)
end

@testset "T31 — Scorecard: 0 proved_conditional (S16 upgraded v62)" begin
    sc = collect(OntologyCatLab.SCORECARD)
    cond = filter(p -> p.second.status == :proved_conditional, sc)
    @test length(cond) == 0
end

@testset "T32 — Scorecard tags are unique" begin
    tags = [r.tag for (_, r) in OntologyCatLab.SCORECARD]
    @test length(tags) == length(Set(tags))
end

@testset "T33 — Scorecard status does not over-claim vs entry" begin
    for (_, row) in OntologyCatLab.SCORECARD
        entry = getfield(OntologyCatLab, row.key)
        @test get(STATUS_RANK, row.status, 0) ≤ get(STATUS_RANK, entry.status, 0)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T34–T35. OPEN ENTRIES
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T34 — 2 open entries total" begin
    opens = [nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :open]
    @test length(opens) == 2
end

@testset "T35 — Open = {Lemma_7_0b, Lemma_7_0d}" begin
    open_set = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :open)
    @test open_set == Set([:Lemma_7_0b, :Lemma_7_0d])
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T36–T38. SINGLETON STATUS CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T36 — Exactly 3 subsumed entries (Axiom_T, Thm_5, Thm_9_4)" begin
    sub = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :subsumed)
    @test sub == Set([:Axiom_T, :Thm_5, :Thm_9_4])
end

@testset "T37 — Exactly 1 :sound entry (Step_E)" begin
    snd = [nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :sound]
    @test length(snd) == 1 && snd[1] == :Step_E
end

@testset "T38 — Exactly 2 uses_LEM entries" begin
    lem = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.uses_LEM)
    @test lem == Set([:Thm_6, :Thm_3_proved])
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T39–T42. KIND COUNTS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T39 — Exactly 2 axioms" begin
    ax = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :axiom)
    @test ax == Set([:Axiom_R, :Axiom_T])
end

@testset "T40 — Exactly 1 bridge principle" begin
    bp = [nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :bridge_principle]
    @test length(bp) == 1 && bp[1] == :Bridge_B1
end

@testset "T41 — Exactly 0 conjectures" begin
    cj = [nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :conjecture]
    @test length(cj) == 0
end

@testset "T42 — Kind distribution: 37 def, 22 lem, 103 thm, 24 prop, 18 cor, 2 step, 2 obs" begin
    kc = Dict{Symbol,Int}()
    for e in ALL_ENTRIES; kc[e.kind] = get(kc, e.kind, 0) + 1; end
    @test kc[:definition]  == 40   # v223: +Def_joint_meta_claim (joint-meta-claim schema for TCE-discovered triples)
    @test kc[:lemma]       == 22   # +3: Hurwitz, Gleason, Wedderburn (v61)
    @test kc[:theorem]     == 109  # +1: S163 Φ_SA J-Markov-blanket (v163 / G17 / Task 14 sub-step 3)
    @test kc[:proposition] == 28   # unchanged (v157)
    @test kc[:corollary]   == 34   # v312: +1 (Cor_S183_S216_lorentzian_synthesis); v212 reverted S191
    @test kc[:step]        == 2
    @test kc[:observation] == 50  # v312: +7 (S183 Phase-2/3 Obs_phi_F_smooth_* arc); v253: 43 (+S216); v237 baseline 42
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T43. 3 assumed entries
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T43 — Exactly 2 :assumed entries" begin
    assumed = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :assumed)
    @test assumed == Set([:Axiom_R, :Bridge_B1])
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T44–T45. ENUMERATED KIND SETS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T44 — Steps = {Step_D, Step_E}" begin
    steps = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :step)
    @test steps == Set([:Step_D, :Step_E])
end

@testset "T45 — Corollaries = {Cor_6_14, Cor_6_15, Cor_6_19, Cor_covariant_bypass, Cor_born_singlet, Cor_Y_blind, Cor_cohomology_restriction, Cor_SU3_confinement}" begin
    cors = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.kind == :corollary)
    @test cors == Set([:Cor_6_14, :Cor_6_15, :Cor_6_19, :Cor_covariant_bypass, :Cor_born_singlet, :Cor_Y_blind, :Cor_cohomology_restriction, :Cor_SU3_confinement, :Cor_gamma_orth_universal, :Cor_spectral_action_constant_of_motion, :Cor_gauge_group_rewriting_invariant, :Cor_c_closure_preserves_fixed_point, :Cor_mass_scale_determined, :Cor_zero_free_parameters, :Cor_composition_determinism, :Cor_born_uniqueness_Q24, :Cor_anomaly_cancellation, :Cor_finite_spectral_triple, :Cor_spectral_triple_rewriting_invariant, :Cor_unique_QM_Q24, :Cor_IC_determinism, :Cor_Q102_rosen_instantiation, :Cor_closure_potential_friston_form_trivial, :Cor_closure_potential_rank_equivalence, :Cor_goldstone_gauge_blanket, :Cor_unification_coupling_ratios, :Cor_per_basis_s97_universal, :Cor_SU3_confinement_scale_invariant, :Cor_Q102_developmental_completeness, :Cor_Q102_morphogenesis_time_canonical, :Cor_phi_F_eigenvalue_equivalence_argued, :Cor_Q102_kw_J_equivariant_blanket, :Cor_Q102_kw_algebraic_markov_blanket, :Cor_S183_S216_lorentzian_synthesis])  # v312: +Cor_S183_S216_lorentzian_synthesis; v212 reverted S191
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T46. ROOT ENTRIES — known roots have empty depends_on
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T46 — Root entries have empty depends_on" begin
    for nm in [:Def_1_1, :Axiom_T, :Lemma_OP4a, :Lemma_7_1b]
        @test isempty(getfield(OntologyCatLab, nm).depends_on)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T46b. ROOT SET IS EXHAUSTIVE (G7)
#        T46 checks 4 known roots but doesn't assert they're the ONLY roots.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T46b — Exactly 9 roots (exhaustive)" begin
    roots = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
                if isempty(e.depends_on))
    @test roots == Set([:Def_1_1, :Axiom_T, :Lemma_OP4a, :Lemma_7_1b, :Thm_tree_gauge_trivial, :Lemma_Hurwitz, :Lemma_Gleason, :Lemma_Wedderburn, :Def_joint_meta_claim])  # +1: Def_joint_meta_claim (v223, schema definition with no deps)
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T47. KEY THEOREM SPOT-CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T47 — Key theorem spot-checks" begin
    let t = OntologyCatLab.Thm_1
        @test t.kind == :theorem && t.layer == 3 && t.status == :proved
    end
    let t = OntologyCatLab.Thm_2
        @test t.kind == :theorem && t.layer == 4 && t.status == :proved
    end
    let t = OntologyCatLab.Thm_4
        @test t.kind == :theorem && t.layer == 7 && t.status == :proved
    end
    let t = OntologyCatLab.Thm_5_prime
        @test t.kind == :theorem && t.logic == :probabilistic && t.status == :proved
    end
    let t = OntologyCatLab.Thm_7
        @test t.kind == :theorem && t.layer == 8 && t.status == :proved
    end
    let t = OntologyCatLab.Thm_7_6  # v62: upgraded from conditional to unconditional
        @test t.status == :proved && :Cor_anomaly_cancellation ∈ t.depends_on
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T48. v11 ADDITIONS — Prop_5_8, Cor_6_19
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T48 — v11 additions (Prop_5_8, Cor_6_19)" begin
    let p = OntologyCatLab.Prop_5_8
        @test p.kind == :proposition && p.layer == 6
        @test Set(p.depends_on) == Set([:Thm_5_11])
    end
    let c = OntologyCatLab.Cor_6_19
        @test c.kind == :corollary && c.depends_on == [:Thm_mixed_cross]
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T49. v10 ADDITIONS — 6 spectator/mixed-rep entries
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T49 — v10 spectator/mixed-rep entries present" begin
    for nm in [:Lemma_1_cross_det, :Lemma_bilinear_singlet,
               :Thm_spectator_singlet, :Thm_mixed_cross,
               :Prop_CG_root_cause, :Cor_covariant_bypass]
        @test nm ∈ ENTRY_NAME_SET
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T50. TRANSITIVE REACHABILITY
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T50 — Transitive reachability" begin
    td4 = transitive_deps(:Thm_4, OntologyCatLab.DEPENDENCY_GRAPH)
    @test :Axiom_R ∈ td4 && :Def_T2 ∈ td4
    td7 = transitive_deps(:Thm_7, OntologyCatLab.DEPENDENCY_GRAPH)
    @test :Def_1_1 ∈ td7
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T51. v11 FIX: Thm_5_10 depends_on includes Def_5_3
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T51 — v11 fix: Thm_5_10 depends on Def_5_3" begin
    @test :Def_5_3 ∈ OntologyCatLab.Thm_5_10.depends_on
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T52. TRANSITIVE PROOF-SOUNDNESS (G2)
#       A :proved entry must not transitively depend on any :open entry.
#       Central invariant of the theorem chain.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T52 — :proved entries have no :open transitive dependencies" begin
    open_set = Set(nm for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES) if e.status == :open)
    for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
        e.status ∈ (:proved, :proved_conditional) || continue
        td = transitive_deps(nm, OntologyCatLab.DEPENDENCY_GRAPH)
        open_in_deps = intersect(td, open_set)
        @test isempty(open_in_deps)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T53. SCORECARD KEYS NOT :open OR :subsumed (G3 + G4)
#       Scorecard should never reference a result that isn't actually proved
#       or that has been superseded.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T53 — Scorecard keys are not :open or :subsumed" begin
    for (sid, row) in OntologyCatLab.SCORECARD
        entry = getfield(OntologyCatLab, row.key)
        @test entry.status ∉ (:open, :subsumed)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T54. :proved_conditional ENTRIES HAVE :assumed IN TRANSITIVE DEPS (G5)
#       A conditional result without an actual condition is semantically wrong.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T54 — :proved_conditional entries have ≥1 :assumed transitive dep" begin
    for (nm, e) in zip(ALL_ENTRY_NAMES, ALL_ENTRIES)
        e.status == :proved_conditional || continue
        td = transitive_deps(nm, OntologyCatLab.DEPENDENCY_GRAPH)
        assumed_in_deps = [d for d in td
                           if getfield(OntologyCatLab, d).status == :assumed]
        @test !isempty(assumed_in_deps)
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T55. LOGIC-PROMOTION RULE (G6)
#       Scorecard logic must be ≥ entry logic in the hierarchy
#       classical(1) ≤ possibilistic(2) ≤ probabilistic(3).
#       :bridge(0) is excluded from the check (Bridge_B1 is :assumed,
#       and shouldn't appear as a scorecard key status).
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T55 — Scorecard logic ≥ entry logic (promotion rule)" begin
    for (sid, row) in OntologyCatLab.SCORECARD
        entry = getfield(OntologyCatLab, row.key)
        entry_rank = get(LOGIC_RANK, entry.logic, -1)
        sc_rank    = get(LOGIC_RANK, row.logic, -1)
        # Skip bridge-logic entries (not rankable)
        entry_rank == 0 && continue
        sc_rank    == 0 && continue
        @test sc_rank ≥ entry_rank
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T56. PROVED UNCONDITIONAL SCORECARD COUNT = 46 (G10)
#       v17 header claims "Proved unconditional: 46".  Pin it.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T56 — Scorecard proved unconditional count" begin
    sc = collect(values(OntologyCatLab.SCORECARD))
    proved_unconditional = count(r -> r.status == :proved, sc)
    @test proved_unconditional == 162  # v220: S174 + S175 :verified → :proved (paired algebraic translation)
end

@testset "T56b — Scorecard verified count" begin
    sc = collect(values(OntologyCatLab.SCORECARD))
    verified_count = count(r -> r.status == :verified, sc)
    @test verified_count == 29  # v312: count reconciled to live SCORECARD; v220: S174 + S175 flipped out of :verified
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T57. STATEMENT UNIQUENESS (G12)
#       Duplicate statements indicate copy-paste errors.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T57 — All entry statements are unique" begin
    stmts = [e.statement for e in ALL_ENTRIES]
    @test length(stmts) == length(Set(stmts))
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T58. CATLAB-VERIFIED entries reference existing spec entries
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T58 — CATLAB_VERIFIED entries are valid" begin
    cv = OntologyCatLab.CATLAB_VERIFIED
    @test length(cv) == 9
    for (name, desc) in cv
        @test name ∈ ENTRY_NAME_SET
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T59. CLUSTER DECOMPOSITION (S120)
#       Cross-branch edges share no composition operations.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T59 — S120: Cluster decomposition entry exists and is possibilistic" begin
    e = OntologyCatLab.Thm_cluster_decomposition
    @test e.kind == :theorem
    @test e.status == :proved
    @test e.logic == :possibilistic
    @test :Thm_spectator_singlet ∈ e.depends_on
    @test :Cor_born_singlet ∈ e.depends_on
    @test :Prop_4_7 ∈ e.depends_on  # Church-Rosser → tree structure
    sc = OntologyCatLab.SCORECARD[:S120]
    @test sc.key == :Thm_cluster_decomposition
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T60. COMPOSITION ORTHOGONALITY (S121)
#       ⟨w|ψ₁⟩ = ⟨w|ψ₂⟩ = 0 for conjugated cross product.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T60 — S121: Composition orthogonality entry exists and is classical" begin
    e = OntologyCatLab.Thm_composition_orthogonality
    @test e.kind == :theorem
    @test e.status == :proved
    @test e.logic == :classical
    @test :Thm_cross_unit_norm ∈ e.depends_on
    @test :Thm_spectator_singlet ∈ e.depends_on
    sc = OntologyCatLab.SCORECARD[:S121]
    @test sc.key == :Thm_composition_orthogonality
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T61. COMPOSITION ORTHOGONALITY — algebraic verification
#       For random unit vectors ψ₁, ψ₂ ∈ ℂ³: w = conj(ψ₁ × ψ₂)/|ψ₁ × ψ₂|
#       satisfies ⟨w|ψ₁⟩ = 0, ⟨w|ψ₂⟩ = 0, |w| = 1.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T61 — Composition orthogonality: ⟨w|ψⱼ⟩ = 0 (10 random samples)" begin
    using LinearAlgebra, Random
    cross3(a, b) = [a[2]*b[3]-a[3]*b[2], a[3]*b[1]-a[1]*b[3], a[1]*b[2]-a[2]*b[1]]
    cross = cross3
    rng = Random.MersenneTwister(42)
    for _ in 1:10
        # Haar-random unit vectors in ℂ³
        ψ₁ = randn(rng, ComplexF64, 3); ψ₁ /= norm(ψ₁)
        ψ₂ = randn(rng, ComplexF64, 3); ψ₂ /= norm(ψ₂)
        c = cross(ψ₁, ψ₂)
        nc = norm(c)
        nc < 1e-10 && continue
        w = conj(c) / nc
        # Orthogonality
        @test abs(dot(w, ψ₁)) < 1e-13
        @test abs(dot(w, ψ₂)) < 1e-13
        # Unit norm
        @test abs(norm(w) - 1.0) < 1e-14
        # Born saturation: μ = |det[w|ψ₁|ψ₂]|²
        M = hcat(w, ψ₁, ψ₂)
        μ = abs(det(M))^2
        μ_expected = 1 - abs(dot(ψ₁, ψ₂))^2
        @test abs(μ - μ_expected) < 1e-13
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T62. D₃ BORN SATURATION — μ = 1 at depth ≥ 2
#       Follow D₃ path: compose, take D₃ daughter, repeat.
#       After first step, all Born weights should be exactly 1.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T62 — D₃ Born saturation: μ = 1 at depth ≥ 2 (5 ICs, depth 6)" begin
    using LinearAlgebra, Random
    cross3(a, b) = [a[2]*b[3]-a[3]*b[2], a[3]*b[1]-a[1]*b[3], a[1]*b[2]-a[2]*b[1]]
    cross = cross3
    rng = Random.MersenneTwister(123)
    for _ in 1:5
        p1 = randn(rng, ComplexF64, 3); p1 /= norm(p1)
        p2 = randn(rng, ComplexF64, 3); p2 /= norm(p2)
        p3 = randn(rng, ComplexF64, 3); p3 /= norm(p3)
        # First D₃ step
        c = cross(p1, p2); w = conj(c) / norm(c)
        # D₃ daughter = (w, p1, p2)
        triple = [w, p1, p2]
        for depth in 2:6
            c2 = cross(triple[1], triple[2])
            w2 = conj(c2) / norm(c2)
            triple = [w2, triple[1], triple[2]]
            M = hcat(triple[1], triple[2], triple[3])
            μ = abs(det(M))^2
            @test abs(μ - 1.0) < 1e-12
        end
    end
end

# ═══════════════════════════════════════════════════════════════════════════════
#  T63. HIGGS 4+4 (S122)
#       Higgs lepton split entry exists and depends on Higgs identification.
# ═══════════════════════════════════════════════════════════════════════════════

@testset "T63 — S122: Higgs 4+4 on ℂ¹⁶⁸" begin
    e = OntologyCatLab.Thm_higgs_lepton_split
    @test e.kind == :theorem
    @test e.status == :verified  # downgraded from :proved (v60 cross-audit: computational evidence only)
    @test e.logic == :possibilistic
    @test :Thm_higgs_identification ∈ e.depends_on
    @test :Thm_majorana_singlet ∈ e.depends_on
    sc = OntologyCatLab.SCORECARD[:S122]
    @test sc.key == :Thm_higgs_lepton_split
end

# ═══════════════════════════════════════════════════════════════════════════════
println("\n✓ All 72 testsets complete.")
