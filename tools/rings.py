#!/usr/bin/env python3
"""Per-person research RING tag, computed from the canonical GEDCOM.

Policy:
  ring 0  blood      the root person, every blood ancestor of theirs, and every descendant of those ancestors
  ring 1  in-law     spouse of a ring-0 person (married-in), not themselves ring 0
  ring 2  in-law+1   parents and siblings of a ring-1 person, and the spouses of those, not already ringed
  ring 3  beyond     everyone else in the file: research budget ZERO, keep as context / second tier only
  ring 4  imported   anyone carrying `1 _TIER imported` (other people's trees, unverified): budget ZERO

usage: python3 tools/rings.py <gedcom> --root @I1@ [--json out.json] [--csv out.csv]
"""
import argparse, json, csv, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gedlib

ap = argparse.ArgumentParser()
ap.add_argument('gedcom')
ap.add_argument('--root', required=True)
ap.add_argument('--json'); ap.add_argument('--csv')
a = ap.parse_args()

indis, fams = gedlib.load(a.gedcom)
assert a.root in indis, f"root {a.root} not in file"

def parents(p):
    out = []
    for f in indis[p]['famc']:
        fam = fams.get(f)
        if fam:
            out += [x for x in (fam['husb'], fam['wife']) if x]
    return out
def children(p):
    out = []
    for f in indis[p]['fams']:
        fam = fams.get(f)
        if fam: out += fam['chil']
    return out
def spouses(p):
    out = []
    for f in indis[p]['fams']:
        fam = fams.get(f)
        if fam: out += [x for x in (fam['husb'], fam['wife']) if x and x != p]
    return out
def siblings(p):
    out = set()
    for f in indis[p]['famc']:
        fam = fams.get(f)
        if fam: out |= set(fam['chil'])
    out.discard(p); return list(out)

ring = {}
# ring 0: ancestors of root, then all their descendants
anc = set(); stack = [a.root]
while stack:
    p = stack.pop()
    if p in anc or p not in indis: continue
    anc.add(p); stack += parents(p)
blood = set(anc); stack = list(anc)
while stack:
    p = stack.pop()
    for c in children(p):
        if c in indis and c not in blood:
            blood.add(c); stack.append(c)
for p in blood: ring[p] = 0
# ring 1
for p in list(blood):
    for s in spouses(p):
        if s in indis and s not in ring: ring[s] = 1
# ring 2
r1 = [p for p, r in ring.items() if r == 1]
for p in r1:
    cand = parents(p) + siblings(p)
    cand += [s for c in cand if c in indis for s in spouses(c)]
    for c in cand:
        if c in indis and c not in ring: ring[c] = 2
imported = {x for x in gedlib.imported_set(a.gedcom) if x.startswith('@I')}
for p in indis:
    ring.setdefault(p, 3)
for p in imported:
    ring[p] = 4

counts = {r: sum(1 for v in ring.values() if v == r) for r in (0, 1, 2, 3, 4)}
print(f"{os.path.basename(a.gedcom)}: {len(indis)} people, root {a.root} {indis[a.root]['name']}")
print(f"  ancestors of root: {len(anc)-1}")
for r, lab in ((0,'ring 0 blood'),(1,'ring 1 in-law'),(2,'ring 2 in-law+1'),(3,'ring 3 beyond'),(4,'ring 4 imported')):
    print(f"  {lab:18s} {counts[r]:5d}  ({100*counts[r]/len(indis):.0f}%)")
if a.json:
    json.dump({p: ring[p] for p in sorted(ring, key=lambda x: int(x.strip('@I')))}, open(a.json, 'w'), indent=0)
if a.csv:
    w = csv.writer(open(a.csv, 'w')); w.writerow(['id', 'ring', 'name', 'birth', 'death', 'sources'])
    for p in sorted(ring, key=lambda x: int(x.strip('@I'))):
        i = indis[p]; w.writerow([p, ring[p], i['name'], i['birt'][0], i['deat'][0], i['sources']])
