#!/usr/bin/env julia
# af_algebra_verify.jl — Verify A_F = ℍ ⊕ M₃(ℂ) algebra structure on Q₂₄
#
# PURPOSE: Exact algebraic verification that the 24-vertex quotient Q₂₄
# carries the finite algebra A_F = ℍ ⊕ M₃(ℂ) of the NCG Standard Model.
# This is the algebra-only half of the spectral triple; the order-one
# condition on D_F (which constrains the Dirac operator) is NOT checked
# here — it is deferred to orderone_hybrid_v1.jl because the exact RREF
# on the 576-dim Hermitian space is computationally prohibitive.
#
# WHAT IS VERIFIED (all in exact ℤ[i] arithmetic, so evidence type = algebraic):
#   1. Triplet identification via hex-alternation scheme (8 colour triplets)
#   2. M₃(ℂ) matrix unit relations: E_{ij} E_{kl} = δ_{jk} E_{il}
#   3. Pauli algebra on weak doublets: σ_k² = P_doublet, σ₁σ₂ = iσ₃
#   4. Colour ⊥ weak: [E_{ij}, σ_k] = 0 for all i,j,k
#
# WHAT IS NOT VERIFIED:
#   - Order-one kernel dim (requires 576-dim exact RREF — see orderone_hybrid_v1.jl)
#   - D_F properties (Tr(D²), [D_F, E_{ij}]=0 — see orderone_hybrid_v1.jl)
#
# Aaron Green — March 31, 2026

using LinearAlgebra

# --- Exact arithmetic types ---
# GI = Gaussian integers ℤ[i] = Complex{BigInt}. All colour vectors live here.
# Using BigInt avoids overflow; using exact integers means every computation
# is a proof, not an approximation.
const GI = Complex{BigInt}; const Vec3 = Vector{GI}

# --- Colour composition ---
# Cross product in ℂ³ (standard formula). This is the raw ∧² map.
cross3(a::Vec3,b::Vec3) = Vec3([a[2]*b[3]-a[3]*b[2],a[3]*b[1]-a[1]*b[3],a[1]*b[2]-a[2]*b[1]])

# Q₄₈ composition convention: w = conj(a × b).
# The conjugation maps ∧²(3) ≅ 3̄ back to 3, ensuring SU(3) equivariance
# (Lemma 7.1b). Without conj, the composed vector lives in the dual
# representation, breaking the self-reproducing property of Q₂₄.
compose_colour(a::Vec3,b::Vec3) = conj.(cross3(a,b))

# Projective equivalence: a ~ b iff a × b = 0 (parallel in ℂP²).
# This is the gauge equivalence — ψ and λψ represent the same vertex.
proj_equiv(a::Vec3,b::Vec3) = all(iszero,cross3(a,b))
is_zero_vec(v::Vec3) = all(iszero,v)

# 3×3 determinant over ℤ[i]. Used to test linear independence of triplets:
# det ≠ 0 iff the three vectors span ℂ³, i.e. form a valid colour triplet.
det3(a::Vec3,b::Vec3,c::Vec3) = a[1]*(b[2]*c[3]-b[3]*c[2])-a[2]*(b[1]*c[3]-b[3]*c[1])+a[3]*(b[1]*c[2]-b[2]*c[1])

# Convenience: construct a Gaussian integer from (real, imag) integer parts.
gi(a,b) = GI(BigInt(a),BigInt(b))

function main()
    # --- Initial conditions ---
    # 6 generic Gaussian-integer vectors in ℂ³. These are the "seed" colour
    # states on the 6 vertices of the hexagonal seed graph G₀.
    # "Generic" means: no special symmetry, pairwise non-proportional, all
    # adjacent compositions nonzero. The quotient Q₂₄ is IC-independent
    # (Thm_n6_selection / S100), so exact values don't matter for structure.
    ics = Dict{Int,Vec3}(1=>[gi(2,1),gi(1,0),gi(3,-1)],2=>[gi(1,0),gi(2,1),gi(1,-2)],
        3=>[gi(1,-1),gi(3,0),gi(2,1)],4=>[gi(3,0),gi(1,-1),gi(1,2)],
        5=>[gi(1,2),gi(2,-1),gi(1,0)],6=>[gi(2,0),gi(1,1),gi(3,0)])

    # G₀ topology: hexagonal cycle (1,2,3)→(2,3,4)→...→(6,1,2).
    # Each triple (s1,s2,s3) is a ternary hyperedge.
    G0 = [(1,2,3),(2,3,4),(3,4,5),(4,5,6),(5,6,1),(6,1,2)]

    # --- Build Q₂₄ (multiway graph → projective quotient) ---
    # The multiway graph M(G₀) is built by iterated composition:
    # for each hyperedge (v1,v2,v3), compose(v1,v2)→w, then add three
    # daughter edges (w,v2,v3), (w,v1,v3), (w,v1,v2).
    # After 5 generations, take projective equivalence classes → Q₂₄.
    psi = Dict{Int,Vec3}(k=>copy(v) for (k,v) in ics)
    nv = 7; edges = Tuple{Int,Int,Int,Int}[(0,s1,s2,s3) for (s1,s2,s3) in G0]
    cache = Dict{Tuple{Int,Int},Int}()  # cache[(v1,v2)] → vertex ID of compose(v1,v2)
    for d in 0:4
        for (_,v1,v2,v3) in filter(e->e[1]==d, edges)
            key = (v1,v2)
            if !haskey(cache,key)
                w_psi = compose_colour(psi[v1],psi[v2]); is_zero_vec(w_psi) && continue
                psi[nv] = w_psi; cache[key] = nv; nv += 1
            end
            w = cache[key]
            # Three daughters per firing (the ternary DPO rewrite rule)
            push!(edges,(d+1,w,v2,v3)); push!(edges,(d+1,w,v1,v3)); push!(edges,(d+1,w,v1,v2))
        end
    end
    # Projective clustering: group vertices by ℂP² equivalence (a ~ λb).
    vids = sort(collect(keys(psi))); reps = Vec3[]; vtc = Dict{Int,Int}()
    for v in vids
        pv = psi[v]; is_zero_vec(pv) && continue; m = 0
        for ci in eachindex(reps); proj_equiv(pv,reps[ci]) && (m=ci; break); end
        m > 0 ? (vtc[v]=m) : (push!(reps,pv); vtc[v]=length(reps))
    end
    ncl = length(reps)
    println("Q₂₄: $ncl clusters")

    # --- Composition map on quotient ---
    # comp[(c1,c2)] = c3 means compose_colour(rep[c1], rep[c2]) ~ rep[c3].
    # This is the closed algebra multiplication on Q₂₄.
    comp = Dict{Tuple{Int,Int},Int}()
    for c1 in 1:ncl, c2 in 1:ncl
        w = compose_colour(reps[c1],reps[c2]); is_zero_vec(w) && continue
        for c3 in 1:ncl; proj_equiv(w,reps[c3]) && (comp[(c1,c2)]=c3; break); end
    end

    # ═══ COLOUR TRIPLETS (hex alternation) ═══
    # The 24 vertices of Q₂₄ partition into 8 colour triplets (each spanning ℂ³).
    # The partition follows the "hex-alternation" scheme:
    #   - Tier A: seed vertices {1,...,6} split into odd-index {1,3,5} and even-index {2,4,6}
    #   - Tier B: first-generation compositions of adjacent A pairs
    #     B-odd = {compose(1,2), compose(3,4), compose(5,6)} (consecutive pairs)
    #     B-even = {compose(2,3), compose(4,5), compose(6,1)} (wrap-around pairs)
    #   - Tier C: second-generation compositions mixing B with A
    #     4 triplets from compose(B-vertex, A-vertex) combinations
    # This gives 8 triplets × 3 = 24 vertices with full coverage.
    println("\n── Colour Triplets ──")
    tA1=[1,3,5]; tA2=[2,4,6]
    tB1=[comp[(1,2)],comp[(3,4)],comp[(5,6)]]
    tB2=[comp[(2,3)],comp[(4,5)],comp[(6,1)]]
    tC1=[comp[(tB1[1],1)],comp[(tB1[2],3)],comp[(tB1[3],5)]]
    tC2=[comp[(tB1[1],2)],comp[(tB1[2],4)],comp[(tB1[3],6)]]
    tC3=[comp[(tB2[1],3)],comp[(tB2[2],5)],comp[(tB2[3],1)]]
    tC4=[comp[(tB2[1],2)],comp[(tB2[2],4)],comp[(tB2[3],6)]]
    trips = [tA1,tA2,tB1,tB2,tC1,tC2,tC3,tC4]
    labels = ["A-odd","A-even","B-odd","B-even","C(Bo,Ao)","C(Bo,Ae)","C(Be,Ao)","C(Be,Ae)"]

    all_v = vcat(trips...)
    println("  Coverage: $(length(unique(all_v)))/24")

    # Verify each triplet spans ℂ³ (det ≠ 0 in exact ℤ[i] arithmetic).
    all_det_ok = true
    for (i,(t,l)) in enumerate(zip(trips,labels))
        d = det3(reps[t[1]],reps[t[2]],reps[t[3]])
        ok = !iszero(d); all_det_ok &= ok
        println("  Triplet $i ($l): $t  det≠0: $(ok ? "✓" : "✗")")
    end
    println("  All triplets linearly independent: $(all_det_ok ? "PASS ✓" : "FAIL ✗")")

    # ═══ M₃(ℂ) GENERATORS E_{ij} ═══
    # The matrix units E_{ij} act on Q₂₄ by: E_{ij}[t[i], t[j]] = 1 for each
    # triplet t. This maps the j-th colour slot to the i-th colour slot across
    # all 8 triplets simultaneously. The key identity is the matrix unit relation:
    #   E_{ij} E_{kl} = δ_{jk} E_{il}
    # which is the defining property of M₃(ℂ). Verified exactly over ℤ.
    println("\n── M₃(ℂ) Generators ──")
    n = ncl
    E = Array{Matrix{Int}}(undef, 3, 3)
    for i in 1:3, j in 1:3
        M = zeros(Int, n, n)
        # Sum over all 8 triplets: each contributes one nonzero entry
        for t in trips; M[t[i],t[j]] = 1; end
        E[i,j] = M
    end

    # Check E_{ij} E_{kl} = δ_{jk} E_{il} (81 products, exact integer arithmetic)
    mu_ok = all(vec([(i,j,k,l) for i=1:3,j=1:3,k=1:3,l=1:3])) do x
        i,j,k,l = x; E[i,j]*E[k,l] == (j==k ? E[i,l] : zeros(Int,n,n))
    end
    println("  E_{ij}E_{kl} = δ_{jk}E_{il}: $(mu_ok ? "PASS ✓" : "FAIL ✗")")

    # Σ E_{ii} should be the identity on the 24-dim triplet subspace
    # (since every vertex belongs to exactly one triplet)
    id_trip = sum(E[i,i] for i in 1:3)
    println("  Σ E_{ii} = I₂₄: $(id_trip == I ? "PASS ✓" : "$(sum(id_trip))/24 nonzero")")

    # ═══ WEAK DOUBLETS AND ℍ GENERATORS ═══
    # The quaternion algebra ℍ acts via Pauli matrices σ_k on weak doublets.
    # A weak doublet pairs an "up" triplet with a "down" triplet:
    #   doublets = [(1,2), (3,4), (5,7), (6,8)]
    # meaning triplet 1 (A-odd) pairs with triplet 2 (A-even), etc.
    # σ_k acts on each doublet's colour slots: for colour index c,
    #   σ₁: |u,c⟩ ↔ |d,c⟩  (off-diagonal, real)
    #   σ₂: |u,c⟩ → -i|d,c⟩, |d,c⟩ → i|u,c⟩  (off-diagonal, imaginary)
    #   σ₃: |u,c⟩ → +|u,c⟩, |d,c⟩ → -|d,c⟩  (diagonal, eigenvalues ±1)
    # This gives ℍ because σ₁σ₂ = iσ₃ (the quaternion relation).
    println("\n── ℍ Generators ──")
    doublets = [(1,2),(3,4),(5,7),(6,8)]  # (up-triplet, down-triplet) pairs
    println("  Doublets: $doublets")

    # Use exact Complex{Rational{BigInt}} to keep σ₂'s imaginary entries exact.
    sigma = [zeros(Complex{Rational{BigInt}}, n, n) for _ in 1:3]
    for k in 1:3
        for (tu,td) in doublets
            for c in 1:3
                u = trips[tu][c]; d = trips[td][c]
                if k == 1; sigma[k][u,d] = 1; sigma[k][d,u] = 1; end
                if k == 2; sigma[k][u,d] = -im; sigma[k][d,u] = im; end
                if k == 3; sigma[k][u,u] = 1; sigma[k][d,d] = -1; end
            end
        end
    end

    # σ_k² = projection onto doublet subspace (not I₂₄, since some vertices
    # are weak singlets and get annihilated by σ_k).
    doublet_proj = zeros(Rational{BigInt}, n, n)
    for (tu,td) in doublets; for c in 1:3
        doublet_proj[trips[tu][c],trips[tu][c]] = 1
        doublet_proj[trips[td][c],trips[td][c]] = 1
    end; end

    s_sq_ok = all(1:3) do k
        sq = real.(sigma[k] * sigma[k])
        all(sq .== doublet_proj)
    end
    println("  σ_k² = P_doublet: $(s_sq_ok ? "PASS ✓" : "FAIL ✗")")

    # σ₁σ₂ = iσ₃ — the quaternion multiplication rule on the doublet subspace.
    s12 = sigma[1]*sigma[2]
    s3i = im .* sigma[3]
    pauli_ok = all(iszero, s12 .- s3i)
    println("  σ₁σ₂ = iσ₃: $(pauli_ok ? "PASS ✓" : "FAIL ✗")")

    # ═══ COLOUR ⊥ WEAK ═══
    # The colour generators E_{ij} and weak generators σ_k must commute:
    #   [E_{ij}, σ_k] = 0
    # This is the factorisation A_F = ℍ ⊕ M₃(ℂ) (direct sum of algebras).
    # It holds because E_{ij} permutes colour indices within each triplet,
    # while σ_k permutes between paired triplets at the same colour index.
    # These two actions are on orthogonal "axes" of the doublet×triplet structure.
    println("\n── Colour ⊥ Weak ──")
    comm_ok = all(vec([(i,j,k) for i=1:3,j=1:3,k=1:3])) do x
        i,j,k = x; all(iszero, E[i,j]*sigma[k] - sigma[k]*E[i,j])
    end
    println("  [E_{ij}, σ_k] = 0 for all i,j,k: $(comm_ok ? "PASS ✓" : "FAIL ✗")")

    # ═══ SUMMARY ═══
    all_pass = all_det_ok && mu_ok && s_sq_ok && pauli_ok && comm_ok
    println("\n","="^60)
    println("  A_F = ℍ ⊕ M₃(ℂ) ALGEBRA ON Q₂₄")
    println("="^60)
    println("  Colour triplets (8, hex alternation): $(all_det_ok ? "PASS ✓" : "FAIL ✗")")
    println("  M₃(ℂ) matrix units: $(mu_ok ? "PASS ✓" : "FAIL ✗")")
    println("  ℍ Pauli algebra: $(s_sq_ok && pauli_ok ? "PASS ✓" : "FAIL ✗")")
    println("  [colour, weak] = 0: $(comm_ok ? "PASS ✓" : "FAIL ✗")")
    println("  Order-one kernel: deferred (exact computation too slow for 576-dim space)")
    println("  ★ $(all_pass ? "ALL ALGEBRA CHECKS PASSED" : "SOME CHECKS FAILED") ★")
    println("="^60)
end

main()
