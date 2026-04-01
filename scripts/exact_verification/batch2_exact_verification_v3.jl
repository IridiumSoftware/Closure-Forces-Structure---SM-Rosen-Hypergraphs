#!/usr/bin/env julia
#
# batch2_exact_verification_v3.jl — Exact algebraic verification of S97, S98, S105
#
# Strategy: NUMERICAL BOOTSTRAP + EXACT VERIFICATION
#   1. Representation matrices exported from Python (SVD colour assignment, seed 42)
#   2. Order-one kernel computed via exact RREF over ℚ
#   3. S97, S98, S105 verified with exact arithmetic (no floats)
#
# The representation is a DEFINITION (a specific embedding of A_F into End(ℂ⁴⁸)).
# The Python SVD finds the correct colour assignment; Julia verifies mathematical
# properties exactly.  The distinction matters: colour assignment is a gauge choice
# that must be consistent with the composition algebra, but the properties being
# verified (Tr(D²) rigidity, colour centralisation, DOF count) are THEOREMS that
# hold for any correct representation.
#
# Evidence type: algebraic (all verifications exact over ℚ).
#
# Aaron Green — March 31, 2026

using LinearAlgebra

# ═══════════════════════════════════════════════════════════════════════════════
# §1  LOAD REPRESENTATION DATA
# ═══════════════════════════════════════════════════════════════════════════════

include("q48_rep_data.jl")

const N48 = 48
const N_SEC = 24

# ═══════════════════════════════════════════════════════════════════════════════
# §2  EXACT RREF AND NULL SPACE OVER ℚ
# ═══════════════════════════════════════════════════════════════════════════════

function rref_with_pivots!(A::Matrix{Rational{BigInt}})
    m, n = size(A)
    pivots = Int[]
    row = 1
    for col in 1:n
        row > m && break
        pivot_row = 0
        for r in row:m
            if A[r, col] != 0
                pivot_row = r; break
            end
        end
        pivot_row == 0 && continue
        if pivot_row != row
            for j in 1:n; A[row, j], A[pivot_row, j] = A[pivot_row, j], A[row, j]; end
        end
        scale = A[row, col]
        for j in 1:n; A[row, j] //= scale; end
        for r in 1:m
            r == row && continue
            A[r, col] == 0 && continue
            factor = A[r, col]
            for j in 1:n; A[r, j] -= factor * A[row, j]; end
        end
        push!(pivots, col)
        row += 1
    end
    return pivots
end

function exact_nullspace(A::Matrix{Rational{BigInt}})
    m, n = size(A)
    R = copy(A)
    pivots = rref_with_pivots!(R)
    free = setdiff(1:n, pivots)
    nullity = length(free)
    nullity == 0 && return zeros(Rational{BigInt}, n, 0)
    basis = zeros(Rational{BigInt}, n, nullity)
    for (k, fc) in enumerate(free)
        basis[fc, k] = 1
        for (i, pc) in enumerate(pivots)
            basis[pc, k] = -R[i, fc]
        end
    end
    return basis
end

# ═══════════════════════════════════════════════════════════════════════════════
# §3  EXTRACT SECTOR BLOCKS AND BUILD OPPOSITE REPRESENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════

function extract_sector_blocks(M_full::Matrix{Complex{Int}})
    n = N_SEC
    Mo = zeros(Complex{Int}, n, n)
    Mc = zeros(Complex{Int}, n, n)
    for i in 1:n, j in 1:n
        Mo[i,j] = M_full[ORIG_GLOBAL[i], ORIG_GLOBAL[j]]
        Mc[i,j] = M_full[CONJ_GLOBAL[i], CONJ_GLOBAL[j]]
    end
    return Mo, Mc
end

function build_j_matrices()
    n = N_SEC
    J_co = zeros(Int, n, n)
    J_oc = zeros(Int, n, n)
    for i in 1:n
        J_co[J_CO_PERM[i], i] = 1
        J_oc[J_OC_PERM[i], i] = 1
    end
    return J_co, J_oc
end

function build_opposite_rep(Mo, Mc, J_co, J_oc)
    Bo = J_oc * conj.(Mc) * J_co
    Bc = J_co * conj.(Mo) * J_oc
    return Bo, Bc
end

# ═══════════════════════════════════════════════════════════════════════════════
# §4  ORDER-ONE KERNEL (exact RREF)
# ═══════════════════════════════════════════════════════════════════════════════

function compute_orderone_kernel(gen_mats, J_co, J_oc)
    n = N_SEC
    dim_M = n * n

    gen_o = Tuple{Matrix{Complex{Int}}, Matrix{Complex{Int}}}[]
    opp_blocks = Tuple{Matrix{Complex{Int}}, Matrix{Complex{Int}}}[]

    for M_full in gen_mats
        Mo, Mc = extract_sector_blocks(M_full)
        push!(gen_o, (Mo, Mc))
        Bo, Bc = build_opposite_rep(Mo, Mc, J_co, J_oc)
        push!(opp_blocks, (Bo, Bc))
    end

    println("  Building order-one constraint matrix...")
    all_rows_re = Vector{Vector{Int}}()
    all_rows_im = Vector{Vector{Int}}()
    n_gen = length(gen_mats)
    n_eff = 0

    for a in 1:n_gen, b in 1:n_gen
        Ao, Ac = gen_o[a]
        Bo, Bc = opp_blocks[b]
        P1 = Ao * Bo
        P2 = Bc * Ac

        has_new = false
        for i in 1:n, j in 1:n
            row_re = zeros(Int, dim_M)
            row_im = zeros(Int, dim_M)
            any_nz = false
            for p in 1:n, q in 1:n
                col = (p-1)*n + q
                val = Complex{Int}(0)
                p == i && (val += P1[q, j])
                val -= Ac[i, p] * Bo[q, j]
                val -= Bc[i, p] * Ao[q, j]
                q == j && (val += P2[i, p])
                if val != 0
                    row_re[col] = Int(real(val))
                    row_im[col] = Int(imag(val))
                    any_nz = true
                end
            end
            if any_nz
                has_new = true
                any(x -> x != 0, row_re) && push!(all_rows_re, row_re)
                any(x -> x != 0, row_im) && push!(all_rows_im, row_im)
            end
        end
        has_new && (n_eff += 1)
    end

    n_rows = length(all_rows_re) + length(all_rows_im)
    println("    Effective pairs: $n_eff / $(n_gen^2)")
    println("    Constraint rows: $n_rows")

    C = zeros(Rational{BigInt}, n_rows, dim_M)
    idx = 0
    for row in all_rows_re
        idx += 1
        for j in 1:dim_M; C[idx, j] = Rational{BigInt}(row[j]); end
    end
    for row in all_rows_im
        idx += 1
        for j in 1:dim_M; C[idx, j] = Rational{BigInt}(row[j]); end
    end

    println("    Computing exact null space via RREF...")
    t0 = time()
    kernel_basis = exact_nullspace(C)
    t1 = time()
    kernel_dim = size(kernel_basis, 2)
    println("    RREF: $(round(t1-t0; digits=1))s")
    println("    Rank: $(dim_M - kernel_dim)")
    println("    ★ Kernel dimension: $kernel_dim")
    return kernel_basis, kernel_dim
end

# ═══════════════════════════════════════════════════════════════════════════════
# §5  S98 VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

function verify_s98(kernel_basis, E_mats)
    println("\n", "="^60)
    println("  S98 — [D_F, E_{ij}] = 0  (Cor_SU3_confinement)")
    println("="^60)
    n = N_SEC; n_full = N48
    kernel_dim = size(kernel_basis, 2)
    all_zero = true

    for k in 1:kernel_dim
        Mk = reshape(kernel_basis[:, k], n, n)
        D = zeros(Rational{BigInt}, n_full, n_full)
        for i in 1:n, j in 1:n
            oi = ORIG_GLOBAL[i]; cj = CONJ_GLOBAL[j]
            D[oi, cj] = Mk[j, i]  # D[orig, conj] = M^T
            D[cj, oi] = Mk[j, i]  # D[conj, orig] = M
        end
        for (gi, gj, E_full) in E_mats
            E_rat = zeros(Rational{BigInt}, n_full, n_full)
            for a in 1:n_full, b in 1:n_full
                E_rat[a, b] = Rational{BigInt}(real(E_full[a, b]))
            end
            comm = D * E_rat - E_rat * D
            if any(x -> x != 0, comm)
                println("  FAIL: [D_$k, E_$(gi)$(gj)] ≠ 0")
                all_zero = false
            end
        end
    end

    if all_zero
        println("  ★ [D_k, E_{ij}] = 0 for ALL $kernel_dim × 9 generators (exact)")
        println("  S98 PASS ✓")
    else
        println("  S98 FAIL ✗")
    end
    return all_zero
end

# ═══════════════════════════════════════════════════════════════════════════════
# §6  S97 VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

function verify_s97(kernel_basis)
    println("\n", "="^60)
    println("  S97 — Tr(D²) = const  (Thm_gauge_coupling_rigidity)")
    println("="^60)
    n = N_SEC
    kernel_dim = size(kernel_basis, 2)

    G = zeros(Rational{BigInt}, kernel_dim, kernel_dim)
    for k in 1:kernel_dim, l in k:kernel_dim
        fro = sum(kernel_basis[i, k] * kernel_basis[i, l] for i in 1:n*n)
        G[k, l] = 2 * fro
        G[l, k] = G[k, l]
    end

    diag_vals = [G[k, k] for k in 1:kernel_dim]
    off_diag_zero = all(G[k, l] == 0 for k in 1:kernel_dim for l in 1:kernel_dim if k != l)
    diag_constant = length(unique(diag_vals)) == 1

    println("  Gram matrix G_{kl} = Tr(D_k D_l):")
    println("    Dim: $kernel_dim × $kernel_dim")
    println("    Off-diagonal all zero: $off_diag_zero")
    println("    Diagonal constant: $diag_constant")
    if !isempty(diag_vals)
        println("    Value: $(diag_vals[1])")
    end

    ok = off_diag_zero && diag_constant
    println(ok ? "  ★ G = $(diag_vals[1]) × I — S97 PASS ✓" : "  S97 FAIL ✗")
    if !diag_constant
        println("    Distinct values: $(unique(diag_vals))")
    end
    return ok
end

# ═══════════════════════════════════════════════════════════════════════════════
# §7  S105 VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

function verify_s105(kernel_basis)
    println("\n", "="^60)
    println("  S105 — DOF count  (Thm_complex_df_cp)")
    println("="^60)
    n = N_SEC
    kernel_dim = size(kernel_basis, 2)
    dim_M = n * n

    function apply_sigma(v)
        w = similar(v)
        for p in 1:n, q in 1:n
            w[(p-1)*n + q] = v[(J_OC_PERM[q]-1)*n + J_CO_PERM[p]]
        end
        return w
    end

    sym_vecs = zeros(Rational{BigInt}, dim_M, kernel_dim)
    asym_vecs = zeros(Rational{BigInt}, dim_M, kernel_dim)
    for k in 1:kernel_dim
        v = kernel_basis[:, k]
        sv = apply_sigma(v)
        sym_vecs[:, k] = v + sv
        asym_vecs[:, k] = v - sv
    end

    function compute_rank(M)
        nc = size(M, 2)
        nc == 0 && return 0
        R = copy(Matrix(M'))
        return length(rref_with_pivots!(R))
    end

    d_sym = compute_rank(sym_vecs)
    d_asym = compute_rank(asym_vecs)

    println("  Single-gen ℂ⁴⁸:")
    println("    Kernel dim (real M): $kernel_dim")
    println("    J-symmetric:   $d_sym")
    println("    J-antisymmetric: $d_asym")
    @assert d_sym + d_asym == kernel_dim

    real_3gen = 3 * d_sym + 3 * kernel_dim
    imag_3gen = 3 * d_asym + 3 * kernel_dim
    total_3gen = real_3gen + imag_3gen

    println("\n  3-gen ℂ¹⁴⁴:")
    println("    Real-sym:  $real_3gen  (3×$d_sym + 3×$kernel_dim)")
    println("    Imag-asym: $imag_3gen  (3×$d_asym + 3×$kernel_dim)")
    println("    Total:     $total_3gen")
    println("\n  Spec: 531 = 270 + 261")
    println("  Computed: $total_3gen = $real_3gen + $imag_3gen")

    ok = total_3gen == 531
    println(ok ? "  ★ S105 PASS ✓" : "  S105: mismatch — investigate")
    return (d_sym=d_sym, d_asym=d_asym, total_3gen=total_3gen)
end

# ═══════════════════════════════════════════════════════════════════════════════
# §8  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

function main()
    println("="^60)
    println("  BATCH 2 EXACT VERIFICATION v3 — S97, S98, S105")
    println("  Numerical bootstrap + exact ℚ-arithmetic verification")
    println("  Representation: seed 42 (SVD colour assignment)")
    println("="^60)

    J_co, J_oc = build_j_matrices()

    # Collect all 12 generator matrices
    gen_mats = Matrix{Complex{Int}}[]
    E_list = []  # for S98
    for i in 0:2, j in 0:2
        sym = Symbol("REP_E_$(i)$(j)")
        M = @eval $sym
        push!(gen_mats, M)
        push!(E_list, (i, j, M))
    end
    for k in 1:3
        sym = Symbol("REP_S$(k)")
        push!(gen_mats, @eval $sym)
    end
    println("\n  Loaded 12 generator matrices (48×48)")

    # Compute kernel
    println("\n── Order-one kernel ──")
    t0 = time()
    kernel_basis, kernel_dim = compute_orderone_kernel(gen_mats, J_co, J_oc)
    t1 = time()
    println("  Time: $(round(t1-t0; digits=1))s")

    # Verify
    s98_ok = verify_s98(kernel_basis, E_list)
    s97_ok = verify_s97(kernel_basis)
    s105 = verify_s105(kernel_basis)

    # Summary
    println("\n", "="^60)
    println("  SUMMARY")
    println("="^60)
    println("  Kernel dim: $kernel_dim (single-gen, expect 60)")
    println("  S97: ", s97_ok ? "PASS ✓" : "FAIL ✗")
    println("  S98: ", s98_ok ? "PASS ✓" : "FAIL ✗")
    println("  S105: ", s105.total_3gen == 531 ? "PASS ✓" : "INVESTIGATE")
    if s97_ok && s98_ok
        println("\n  ★ Evidence upgrade: computational → algebraic")
    end
    println("="^60)
end

main()
