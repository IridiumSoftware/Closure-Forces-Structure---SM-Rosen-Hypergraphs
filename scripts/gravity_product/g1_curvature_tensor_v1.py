#!/usr/bin/env python3
"""
g1_curvature_tensor_v1.py — G1 Session 5: Position-Decomposed Curvature

Each ternary hyperedge (c₁,c₂,c₃) has three vertex POSITIONS with
distinct roles: pos1 (F-role, composed), pos2 (A-role, composed),
pos3 (S-role, spectator). The curvature contribution from pos1-pos2
(the composition pair) may differ from pos1-pos3 or pos2-pos3.

If the position-decomposed curvature has a preferred SIGNATURE
(one sign for composition pairs, opposite for spectator pairs),
this is a candidate for Lorentz signature.

Diagnostics:
  A. Curvature by position pair type (1-2, 1-3, 2-3) within each HE
  B. Does composition-pair curvature differ from spectator-pair curvature?
  C. The "curvature matrix" K_{ij} per hyperedge
  D. Eigenvalue structure of K — signature test
  E. Tier × position interaction
  F. IC-independence

Usage:
  python3 g1_curvature_tensor_v1.py [--seed S] [--n_ic N]
"""

import numpy as np
import argparse
import time
from collections import defaultdict
from scipy.optimize import linprog

# ═══════════════════════════════════════════════════════════════════════════════
# CORE (compact)
# ═══════════════════════════════════════════════════════════════════════════════

def cross_C3(a, b):
    return np.array([a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],
                     a[0]*b[1]-a[1]*b[0]], dtype=np.complex128)
def normalize(v):
    n=np.linalg.norm(v); return v/n if n>1e-15 else np.zeros_like(v)
def compose_colour(p1,p2): return normalize(np.conj(cross_C3(p1,p2)))
def haar_C3(rng): return normalize(rng.standard_normal(3)+1j*rng.standard_normal(3))
def fidelity(a,b): return abs(np.vdot(a,b))**2
def born_weight(p1,p2,p3,d):
    if d%2==1: t1,t2,t3=np.conj(p1),np.conj(p2),p3.copy()
    else: t1,t2,t3=p1.copy(),p2.copy(),np.conj(p3)
    return abs(np.linalg.det(np.column_stack([t1,t2,t3])))**2

G0_TOPO=[(0,1,2),(1,2,3),(2,3,4),(3,4,5),(4,5,0),(5,0,1)]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD Q₂₄
# ═══════════════════════════════════════════════════════════════════════════════

def build_Q24(rng, depth=5):
    psi={v:haar_C3(rng) for v in range(6)}
    nv=6; vd={v:0 for v in range(6)}
    edges=[(0,s1,s2,s3) for s1,s2,s3 in G0_TOPO]; cc={}
    for d in range(depth):
        for _,v1,v2,v3 in [e for e in edges if e[0]==d]:
            k=(v1,v2)
            if k not in cc:
                psi[nv]=compose_colour(psi[v1],psi[v2])
                cc[k]=nv; vd[nv]=d+1; nv+=1
            w=cc[k]
            edges.append((d+1,w,v2,v3))
            edges.append((d+1,w,v1,v3))
            edges.append((d+1,w,v1,v2))
    av=sorted(psi.keys()); nvt=len(av)
    uf=list(range(nvt)); vi={v:i for i,v in enumerate(av)}
    def find(x):
        while uf[x]!=uf[uf[x]]: uf[x]=uf[uf[x]]
        while uf[x]!=x: uf[x]=uf[uf[x]]; x=uf[x]
        return x
    def union(x,y):
        a,b=find(x),find(y)
        if a!=b: uf[a]=b
    pa=np.array([psi[v] for v in av])
    fm=np.abs(pa@pa.conj().T)**2
    for i in range(nvt):
        for j in range(i+1,nvt):
            if fm[i,j]>0.999: union(i,j)
    cm=defaultdict(list)
    for v in av: cm[find(vi[v])].append(v)
    cr=sorted(cm.keys()); rc={r:i for i,r in enumerate(cr)}
    vc={}
    for r,vs in cm.items():
        c=rc[r]
        for v in vs: vc[v]=c
    ncl=len(cr)
    qp={}
    for r,vs in cm.items():
        c=rc[r]; qp[c]=psi[min(vs,key=lambda v:vd[v])]
    orig=set(vc[v] for v in range(6))
    g1c=set()
    for v,d in vd.items():
        if d==1:
            c=vc[v]
            if c not in orig: g1c.add(c)
    rem=set(range(ncl))-orig-g1c
    ce={}
    for r,vs in cm.items():
        c=rc[r]; ce[c]=min(vd[v] for v in vs)
    qt={}
    for c in orig: qt[c]='A'
    for c in g1c: qt[c]='B'
    for c in rem: qt[c]='C_even' if ce[c]%2==0 else 'C_odd'

    uhe=defaultdict(list)
    for de,v1,v2,v3 in edges:
        c1,c2,c3=vc[v1],vc[v2],vc[v3]
        uhe[(c1,c2,c3)].append((de,born_weight(psi[v1],psi[v2],psi[v3],de)))
    hb={he:np.mean([bw for _,bw in uhe[he]]) for he in uhe}

    firing={}
    for (c1,c2,c3) in uhe:
        if (c1,c2) not in firing:
            wp=compose_colour(qp[c1],qp[c2])
            if np.linalg.norm(wp)>1e-10:
                bc,bf=None,0
                for ci in range(ncl):
                    f=fidelity(wp,qp[ci])
                    if f>bf: bf,bc=f,ci
                if bf>0.999: firing[(c1,c2)]=bc

    adj=np.zeros((ncl,ncl))
    for (c1,c2,c3) in uhe:
        adj[c1,c2]=1;adj[c2,c1]=1;adj[c1,c3]=1
        adj[c3,c1]=1;adj[c2,c3]=1;adj[c3,c2]=1
    np.fill_diagonal(adj,0)
    return ncl, qp, qt, uhe, hb, firing, adj


# ═══════════════════════════════════════════════════════════════════════════════
# TERNARY ORC PER EDGE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_all_edge_orc(ncl, adj, uhe, hb, firing):
    from collections import deque
    dist=np.full((ncl,ncl),np.inf); np.fill_diagonal(dist,0)
    for s in range(ncl):
        q=deque([s])
        while q:
            v=q.popleft()
            for u in range(ncl):
                if adj[v,u]>0 and dist[s,u]>dist[s,v]+1:
                    dist[s,u]=dist[s,v]+1; q.append(u)

    # Precompute walk measures
    walk={}
    for v in range(ncl):
        mu=np.zeros(ncl)
        for (c1,c2,c3) in hb:
            if c1==v and (c1,c2) in firing: mu[firing[(c1,c2)]]+=1
            if c2==v and (c1,c2) in firing: mu[firing[(c1,c2)]]+=1
        s=np.sum(mu)
        if s>1e-15: mu/=s
        walk[v]=mu

    def W1(mx,my):
        sx=np.where(mx>1e-15)[0]; sy=np.where(my>1e-15)[0]
        if len(sx)==0 or len(sy)==0: return 0.0
        nx,ny=len(sx),len(sy)
        c=np.array([dist[sx[i],sy[j]] for i in range(nx) for j in range(ny)])
        Ae=np.zeros((nx+ny,nx*ny)); be=np.zeros(nx+ny)
        for i in range(nx):
            for j in range(ny): Ae[i,i*ny+j]=1.0
            be[i]=mx[sx[i]]
        for j in range(ny):
            for i in range(nx): Ae[nx+j,i*ny+j]=1.0
            be[nx+j]=my[sy[j]]
        r=linprog(c,A_eq=Ae,b_eq=be,bounds=[(0,None)]*(nx*ny),method='highs')
        return r.fun if r.success else 0.0

    # Compute κ for all simple edges
    edge_kappa = {}
    for i in range(ncl):
        for j in range(i+1,ncl):
            if adj[i,j]>0:
                k = 1.0 - W1(walk[i], walk[j])
                edge_kappa[(i,j)] = k
                edge_kappa[(j,i)] = k

    return edge_kappa


# ═══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

def run_session(seed, n_ic):
    print(f"\n{'='*70}")
    print(f"  G1 Session 5: Position-Decomposed Curvature (Tensor Structure)")
    print(f"  {n_ic} ICs, seed {seed}")
    print(f"{'='*70}")

    rng_master = np.random.default_rng(seed)

    all_k12 = []; all_k13 = []; all_k23 = []
    all_signatures = []

    for ic in range(n_ic):
        rng = np.random.default_rng(rng_master.integers(0, 2**31))
        ncl, qp, qt, uhe, hb, firing, adj = build_Q24(rng)
        edge_kappa = compute_all_edge_orc(ncl, adj, uhe, hb, firing)

        # A: For each hyperedge, decompose curvature by position pair
        # Position pair types:
        #   (1,2) = composition pair (pos1 × pos2 → w)
        #   (1,3) = F-role to S-role (cross-coupling)
        #   (2,3) = A-role to S-role (weak-spectator)

        k12_list = []; k13_list = []; k23_list = []
        he_matrices = []  # 3×3 curvature matrix per HE

        for (c1, c2, c3), bw in hb.items():
            # Get curvature for each pair
            k12 = edge_kappa.get((c1, c2), edge_kappa.get((c2, c1), 0))
            k13 = edge_kappa.get((c1, c3), edge_kappa.get((c3, c1), 0))
            k23 = edge_kappa.get((c2, c3), edge_kappa.get((c3, c2), 0))

            k12_list.append(k12)
            k13_list.append(k13)
            k23_list.append(k23)

            # Curvature "matrix" for this HE
            K = np.array([[0, k12, k13],
                          [k12, 0, k23],
                          [k13, k23, 0]])
            he_matrices.append(K)

        k12_arr = np.array(k12_list)
        k13_arr = np.array(k13_list)
        k23_arr = np.array(k23_list)

        all_k12.append(np.mean(k12_arr))
        all_k13.append(np.mean(k13_arr))
        all_k23.append(np.mean(k23_arr))

        if ic == 0:
            print(f"\n  IC #{ic}: {ncl} clusters, {len(hb)} hyperedges")

            # A: Position-pair curvature
            print(f"\n  A. Curvature by position pair:")
            print(f"    (1,2) composition: ⟨κ⟩ = {np.mean(k12_arr):+.4f} ± {np.std(k12_arr):.4f}")
            print(f"    (1,3) F-spectator: ⟨κ⟩ = {np.mean(k13_arr):+.4f} ± {np.std(k13_arr):.4f}")
            print(f"    (2,3) A-spectator: ⟨κ⟩ = {np.mean(k23_arr):+.4f} ± {np.std(k23_arr):.4f}")

            # B: Composition vs spectator
            comp_mean = np.mean(k12_arr)
            spec_mean = np.mean(np.concatenate([k13_arr, k23_arr]))
            print(f"\n  B. Composition (1,2) vs spectator (1,3)+(2,3):")
            print(f"    Composition ⟨κ⟩: {comp_mean:+.4f}")
            print(f"    Spectator ⟨κ⟩:   {spec_mean:+.4f}")
            print(f"    Difference:       {comp_mean - spec_mean:+.4f}")
            if comp_mean * spec_mean < 0:
                print(f"    → OPPOSITE SIGNS: candidate for signature")
            elif abs(comp_mean - spec_mean) > 0.1:
                print(f"    → DIFFERENT MAGNITUDES but same sign")
            else:
                print(f"    → SIMILAR values")

            # C: Curvature matrix eigenvalues
            print(f"\n  C. Curvature matrix eigenvalues (sample of 10 HEs):")
            sig_counts = defaultdict(int)
            all_eigs = []
            for i, K in enumerate(he_matrices):
                eigs = sorted(np.linalg.eigvalsh(K))
                all_eigs.append(eigs)
                # Signature: count (neg, zero, pos) eigenvalues
                n_neg = sum(1 for e in eigs if e < -0.01)
                n_pos = sum(1 for e in eigs if e > 0.01)
                n_zero = 3 - n_neg - n_pos
                sig = (n_neg, n_zero, n_pos)
                sig_counts[sig] += 1

                if i < 10:
                    tier_label = f"({qt[list(hb.keys())[i][0]]},{qt[list(hb.keys())[i][1]]},{qt[list(hb.keys())[i][2]]})"
                    print(f"    HE#{i} {tier_label}: eigs = [{eigs[0]:+.3f}, {eigs[1]:+.3f}, {eigs[2]:+.3f}]")

            # D: Signature distribution
            print(f"\n  D. Signature distribution across {len(he_matrices)} HEs:")
            print(f"    (−,0,+) means (n_negative, n_zero, n_positive) eigenvalues")
            for sig in sorted(sig_counts.keys()):
                count = sig_counts[sig]
                pct = count / len(he_matrices) * 100
                print(f"    {sig}: {count} ({pct:.1f}%)")

            all_signatures.append(sig_counts)

            # Mean eigenvalues
            eig_arr = np.array(all_eigs)
            print(f"\n    Mean eigenvalues: [{np.mean(eig_arr[:,0]):+.4f}, "
                  f"{np.mean(eig_arr[:,1]):+.4f}, {np.mean(eig_arr[:,2]):+.4f}]")
            print(f"    Eigenvalue σ:     [{np.std(eig_arr[:,0]):.4f}, "
                  f"{np.std(eig_arr[:,1]):.4f}, {np.std(eig_arr[:,2]):.4f}]")

            # E: Tier × position interaction
            print(f"\n  E. Tier × position interaction:")
            tier_pos = defaultdict(lambda: {'12': [], '13': [], '23': []})
            for (c1,c2,c3), (k12v, k13v, k23v) in zip(hb.keys(),
                    zip(k12_list, k13_list, k23_list)):
                tp = (qt[c1], qt[c2], qt[c3])
                tier_pos[tp]['12'].append(k12v)
                tier_pos[tp]['13'].append(k13v)
                tier_pos[tp]['23'].append(k23v)

            print(f"    {'Tier pattern':>25} | {'κ(1,2)':>8} | {'κ(1,3)':>8} | {'κ(2,3)':>8} | {'n':>4}")
            print(f"    {'─'*60}")
            for tp in sorted(tier_pos.keys(), key=lambda x: -len(tier_pos[x]['12'])):
                v12 = np.mean(tier_pos[tp]['12'])
                v13 = np.mean(tier_pos[tp]['13'])
                v23 = np.mean(tier_pos[tp]['23'])
                n = len(tier_pos[tp]['12'])
                if n >= 3:
                    print(f"    {str(tp):>25} | {v12:+8.4f} | {v13:+8.4f} | {v23:+8.4f} | {n:>4}")

            # F: Does (1,2) have systematically different sign from (1,3) and (2,3)?
            sign_12 = np.sign(k12_arr)
            sign_13 = np.sign(k13_arr)
            sign_23 = np.sign(k23_arr)
            opp_13 = np.mean(sign_12 * sign_13 < 0)
            opp_23 = np.mean(sign_12 * sign_23 < 0)
            print(f"\n  F. Sign opposition test:")
            print(f"    κ(1,2) opposite sign to κ(1,3): {opp_13*100:.1f}% of HEs")
            print(f"    κ(1,2) opposite sign to κ(2,3): {opp_23*100:.1f}% of HEs")

    # Summary
    print(f"\n{'─'*70}")
    print(f"  Summary across {n_ic} ICs:")
    print(f"    ⟨κ(1,2)⟩: {np.mean(all_k12):+.4f} ± {np.std(all_k12):.4f}")
    print(f"    ⟨κ(1,3)⟩: {np.mean(all_k13):+.4f} ± {np.std(all_k13):.4f}")
    print(f"    ⟨κ(2,3)⟩: {np.mean(all_k23):+.4f} ± {np.std(all_k23):.4f}")

    # Is there a signature?
    k12m = np.mean(all_k12); k13m = np.mean(all_k13); k23m = np.mean(all_k23)
    if k12m > 0 and k13m < 0 and k23m < 0:
        print(f"\n  SIGNATURE: (+,−,−) — composition positive, spectator negative")
    elif k12m < 0 and k13m > 0 and k23m > 0:
        print(f"\n  SIGNATURE: (−,+,+) — composition negative, spectator positive")
    elif abs(k12m - k13m) > 0.1 or abs(k12m - k23m) > 0.1:
        print(f"\n  ASYMMETRY: position pairs have different curvature magnitudes")
    else:
        print(f"\n  NO SIGNATURE: all position pairs have similar curvature")


def main():
    parser = argparse.ArgumentParser(description="G1 Session 5: Curvature Tensor")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n_ic", type=int, default=10)
    args = parser.parse_args()
    t0 = time.time()
    run_session(args.seed, args.n_ic)
    print(f"\n{'='*70}")
    print(f"  Total time: {time.time()-t0:.1f}s")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
