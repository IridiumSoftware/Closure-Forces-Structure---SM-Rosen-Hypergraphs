#!/usr/bin/env python3
"""
q102_build_v1.py — Build Q₁₀₂ = Q₅₁ ∪ C(Q₅₁) and test KO-dimension

Part 1: Construct Q₁₀₂ from K₆³ + C-closure
Part 2: KO-dimension sign checks

Usage:
  python3 q102_build_v1.py [--seed S] [--n_ic N]
"""

import numpy as np
import argparse
from collections import defaultdict, Counter

def cross_C3(a, b):
    return np.array([a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2],
                     a[0]*b[1]-a[1]*b[0]], dtype=np.complex128)

def normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-15 else np.zeros_like(v)

def compose_colour(p1, p2):
    return normalize(np.conj(cross_C3(p1, p2)))

def haar_C3(rng):
    return normalize(rng.standard_normal(3) + 1j * rng.standard_normal(3))

def fidelity(a, b):
    return abs(np.vdot(a, b))**2

G0_TOPO = [(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]

def complete_ternary(n):
    return [(i,j,k) for i in range(n) for j in range(n) if j!=i
            for k in range(n) if k!=i and k!=j]


def build_multiway(edges, psi_init, depth):
    psi = dict(psi_init)
    next_vid = max(psi_init.keys()) + 1
    all_edges = [(0, s1, s2, s3) for s1, s2, s3 in edges]
    compose_cache = {}
    vertex_depth = {v: 0 for v in psi_init}

    for d in range(depth):
        for _, v1, v2, v3 in [e for e in all_edges if e[0] == d]:
            key = (v1, v2)
            if key not in compose_cache:
                w = compose_colour(psi[v1], psi[v2])
                if np.linalg.norm(w) < 1e-10: continue
                psi[next_vid] = w
                compose_cache[key] = next_vid
                vertex_depth[next_vid] = d + 1
                next_vid += 1
            w = compose_cache[key]
            all_edges.append((d+1, w, v2, v3))
            all_edges.append((d+1, w, v1, v3))
            all_edges.append((d+1, w, v1, v2))

    return psi, vertex_depth, all_edges


def build_c_closed_quotient(seed_edges, psi_init, depth=4, threshold=0.999):
    """Build Q = (M(seed) ∪ C(M(seed))) / gauge."""

    # Build original multiway
    psi_orig, depth_orig, edges_orig = build_multiway(seed_edges, psi_init, depth)

    # Build conjugate multiway (from conjugated ICs)
    psi_init_conj = {v: np.conj(psi_init[v]) for v in psi_init}
    psi_conj, depth_conj, edges_conj_raw = build_multiway(seed_edges, psi_init_conj, depth)

    # Offset conjugate IDs
    offset = max(psi_orig.keys()) + 1
    psi_conj_off = {v + offset: psi_conj[v] for v in psi_conj}
    depth_conj_off = {v + offset: depth_conj[v] for v in depth_conj}
    edges_conj = [(d, v1+offset, v2+offset, v3+offset) for d, v1, v2, v3 in edges_conj_raw]

    # Union
    psi_all = {}; depth_all = {}; source = {}
    for v, p in psi_orig.items():
        psi_all[v] = p; depth_all[v] = depth_orig[v]; source[v] = 'orig'
    for v, p in psi_conj_off.items():
        psi_all[v] = p; depth_all[v] = depth_conj_off[v]; source[v] = 'conj'

    # Cluster
    all_vids = sorted(psi_all.keys())
    clusters = []; vid_to_cid = {}
    for v in all_vids:
        matched = False
        for ci, (_, rp, _) in enumerate(clusters):
            if fidelity(psi_all[v], rp) > threshold:
                vid_to_cid[v] = ci; matched = True; break
        if not matched:
            vid_to_cid[v] = len(clusters)
            clusters.append((v, psi_all[v], source[v]))

    n_cl = len(clusters)
    q_psi = {i: clusters[i][1] for i in range(n_cl)}

    # Track origins
    cl_sources = defaultdict(set)
    for v in all_vids:
        cl_sources[vid_to_cid[v]].add(source[v])
    cl_origin = {}
    for ci in range(n_cl):
        srcs = cl_sources[ci]
        cl_origin[ci] = 'orig_only' if srcs == {'orig'} else ('conj_only' if srcs == {'conj'} else 'both')

    # Tiers
    orig_cids = set(vid_to_cid[v] for v in range(6))
    gen1_cids = set()
    for v, d in depth_all.items():
        if d == 1:
            c = vid_to_cid[v]
            if c not in orig_cids: gen1_cids.add(c)
    q_tier = {}
    for c in range(n_cl):
        if c in orig_cids: q_tier[c] = 'A'
        elif c in gen1_cids: q_tier[c] = 'B'
        else: q_tier[c] = 'C'

    # Hyperedges
    q_he = set()
    for edges_list in [edges_orig, edges_conj]:
        for _, v1, v2, v3 in edges_list:
            if v1 in vid_to_cid and v2 in vid_to_cid and v3 in vid_to_cid:
                q_he.add((vid_to_cid[v1], vid_to_cid[v2], vid_to_cid[v3]))

    return {
        'n_cl': n_cl, 'q_psi': q_psi, 'q_tier': q_tier,
        'q_he': q_he, 'cl_origin': cl_origin,
    }


def build_J(Q):
    """Build J (C-involution) as permutation matrix."""
    n = Q['n_cl']
    J = np.zeros((n, n))
    j_map = {}
    for c in range(n):
        psi_c = np.conj(Q['q_psi'][c])
        for c2 in range(n):
            if fidelity(psi_c, Q['q_psi'][c2]) > 0.999:
                J[c, c2] = 1
                j_map[c] = c2
                break
    return J, j_map


def run_diagnostics(Q, label):
    n = Q['n_cl']
    cl_origin = Q['cl_origin']
    q_tier = Q['q_tier']

    print(f"\n{'='*60}")
    print(f"  {label}: {n} vertices")
    print(f"{'='*60}")

    orig = sum(1 for v in cl_origin.values() if v == 'orig_only')
    conj = sum(1 for v in cl_origin.values() if v == 'conj_only')
    both = sum(1 for v in cl_origin.values() if v == 'both')
    print(f"\n  Origin: {orig} orig + {conj} conj + {both} overlap")

    # Tier structure
    tc = Counter(q_tier.values())
    for t in sorted(tc):
        o = sum(1 for c in range(n) if q_tier[c]==t and cl_origin[c]=='orig_only')
        co = sum(1 for c in range(n) if q_tier[c]==t and cl_origin[c]=='conj_only')
        b = sum(1 for c in range(n) if q_tier[c]==t and cl_origin[c]=='both')
        print(f"  Tier {t}: {tc[t]} (orig:{o}, conj:{co}, both:{b})")

    print(f"  Hyperedges: {len(Q['q_he'])}")

    # Rosen closure
    sources = set(); targets = set()
    for c1, c2, c3 in Q['q_he']:
        sources.update([c1, c2, c3])
        targets.add(c1)
    print(f"  Rosen-closed: sources={len(sources)}/{n}, targets={len(targets)}/{n}")

    # C-involution
    J, j_map = build_J(Q)
    row_ok = np.allclose(J.sum(axis=1), 1) and np.allclose(J.sum(axis=0), 1)
    j2 = np.allclose(J @ J, np.eye(n))
    fixed = sum(1 for c in range(n) if j_map.get(c, -1) == c)
    min_fid = 1.0
    for c in range(n):
        psi_c = np.conj(Q['q_psi'][c])
        best = max(fidelity(psi_c, Q['q_psi'][c2]) for c2 in range(n))
        min_fid = min(min_fid, best)

    print(f"\n  J (C-involution):")
    print(f"    Permutation matrix: {row_ok}")
    print(f"    J² = I: {j2}")
    print(f"    Fixed points: {fixed}")
    print(f"    Min C-match fidelity: {min_fid:.6f}")

    # Tier mapping under J
    tier_map = Counter()
    for c in range(n):
        if c in j_map:
            tier_map[(q_tier[c], q_tier[j_map[c]])] += 1
    print(f"    Tier mapping under C:")
    for (s, t), cnt in sorted(tier_map.items()):
        print(f"      {s} → {t}: {cnt}")

    # KO-dimension
    gamma = np.array([1.0 if cl_origin[c] == 'orig_only' else -1.0 for c in range(n)])
    Gamma = np.diag(gamma)
    jg_comm = np.linalg.norm(J @ Gamma - Gamma @ J, 'fro')
    jg_anti = np.linalg.norm(J @ Gamma + Gamma @ J, 'fro')

    print(f"\n  KO-dimension (sector chirality):")
    print(f"    γ split: {int(np.sum(gamma > 0))} orig, {int(np.sum(gamma < 0))} conj")
    print(f"    ||[J, γ]|| = {jg_comm:.6f}")
    print(f"    ||{{J, γ}}|| = {jg_anti:.6f}")
    if jg_anti < 1e-10 and j2:
        print(f"    ★ J² = +1, Jγ = -γJ → KO-dim ∈ {{4, 6}}")
        print(f"    With ε = +1 (J² = +1): KO-dim 6 candidate ✓")
    elif jg_comm < 1e-10 and j2:
        print(f"    J² = +1, Jγ = +γJ → KO-dim 0")
    else:
        print(f"    Indeterminate")

    return J, j_map, gamma


def check_q48_embedding(Q102, psi_init):
    """Check if Q₄₈ (from G₀) embeds in Q₁₀₂."""
    print(f"\n  Q₄₈ embedding check:")
    Q48 = build_c_closed_quotient(G0_TOPO, psi_init, depth=5)
    n48 = Q48['n_cl']
    n102 = Q102['n_cl']

    matched = 0
    for c48 in range(n48):
        for c102 in range(n102):
            if fidelity(Q48['q_psi'][c48], Q102['q_psi'][c102]) > 0.999:
                matched += 1
                break
    print(f"    Q₄₈ clusters: {n48}")
    print(f"    Found in Q₁₀₂: {matched}/{n48}")
    print(f"    Q₄₈ ⊂ Q₁₀₂: {'YES' if matched == n48 else 'NO'}")


def ic_independence(n_ic, seed):
    print(f"\n{'='*60}")
    print(f"  IC-INDEPENDENCE ({n_ic} ICs)")
    print(f"{'='*60}")

    rng_master = np.random.default_rng(seed + 9000)
    results = []
    for ic in range(n_ic):
        s = rng_master.integers(0, 2**31)
        rng = np.random.default_rng(s)
        psi_init = {v: haar_C3(rng) for v in range(6)}
        Q = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)
        orig = sum(1 for v in Q['cl_origin'].values() if v == 'orig_only')
        conj = sum(1 for v in Q['cl_origin'].values() if v == 'conj_only')
        both = sum(1 for v in Q['cl_origin'].values() if v == 'both')

        J, jm = build_J(Q)
        j2 = np.allclose(J @ J, np.eye(Q['n_cl']))
        fixed = int(np.trace(J))

        results.append({'n_cl': Q['n_cl'], 'orig': orig, 'conj': conj,
                        'both': both, 'j2': j2, 'fixed': fixed})

    print(f"  n_cl: {[r['n_cl'] for r in results]}")
    print(f"  orig: {[r['orig'] for r in results]}")
    print(f"  conj: {[r['conj'] for r in results]}")
    print(f"  both: {[r['both'] for r in results]}")
    print(f"  J²=I: {[r['j2'] for r in results]}")
    print(f"  fixed: {[r['fixed'] for r in results]}")

    n_cls = [r['n_cl'] for r in results]
    print(f"\n  IC-independent: {'YES' if len(set(n_cls)) == 1 else 'NO'} "
          f"(unique: {sorted(set(n_cls))})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--n_ic', type=int, default=10)
    args = parser.parse_args()

    print("="*60)
    print("  Q₁₀₂ = Q₅₁ ∪ C(Q₅₁): Construction + KO-dimension")
    print("="*60)

    rng = np.random.default_rng(args.seed)
    psi_init = {v: haar_C3(rng) for v in range(6)}

    # Build Q₁₀₂
    Q102 = build_c_closed_quotient(complete_ternary(6), psi_init, depth=4)

    J, j_map, gamma = run_diagnostics(Q102, "Q₁₀₂ = Q₅₁ ∪ C(Q₅₁)")

    # Q₄₈ embedding
    check_q48_embedding(Q102, psi_init)

    # IC independence
    ic_independence(args.n_ic, args.seed)

    # Summary
    n = Q102['n_cl']
    orig = sum(1 for v in Q102['cl_origin'].values() if v == 'orig_only')
    conj = sum(1 for v in Q102['cl_origin'].values() if v == 'conj_only')
    both = sum(1 for v in Q102['cl_origin'].values() if v == 'both')
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  |Q₁₀₂| = {n}")
    print(f"  Expected: 102 (= 51 + 51)")
    print(f"  Split: {orig} orig + {conj} conj + {both} overlap")
    print(f"  Is 102: {'YES' if n == 102 else 'NO'}")
    jg_anti = np.linalg.norm(J @ np.diag(gamma) + np.diag(gamma) @ J, 'fro')
    print(f"  KO-dim 6 candidate: {'YES' if jg_anti < 1e-10 else 'NO'}")
    print(f"  Gate passed: {'PROCEED to Part 3' if n >= 100 and jg_anti < 1e-10 else 'STOP'}")


if __name__ == '__main__':
    main()
