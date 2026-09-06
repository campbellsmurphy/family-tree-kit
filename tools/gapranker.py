"""Rank the tree's end-of-line ancestors by how worth researching they are next.

An end-of-line is a direct ancestor with no parents recorded. Ranking them by generation
alone is the obvious mistake: a 6th-great-grandparent born in Victoria in 1860 is a far
better bet than a 3rd-great born in Kerry in 1820, because Victorian civil registration
exists from 1853 and Irish Catholic parish coverage before the Famine mostly does not.

So the score multiplies two things:
  closeness      - how few generations up, i.e. how much of the tree hangs off them
  reachability   - whether records plausibly exist for that place and year

Reachability uses civil-registration start dates per jurisdiction, read from the sourced
table tools/civil_registration.csv. Before the start date the answer is parish/church
registers, which are patchy and often not online, so the score drops rather than going to
zero; before any indexed register it bottoms out.

With --register, the searched-corpus register adjusts the score: every controlled ABSENT
nil lowers it (one reachable corpus is exhausted), while coverage-unknown, void and
not-indexed rows leave it alone, because those gaps are still open.

usage: python3 tools/gapranker.py <gedcom> --root @I1@ [--top 30] [--json]
"""
import argparse
import csv
import json
import os
import re
from collections import deque

import gedlib

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'civil_registration.csv')


def load_jurisdictions(path=CSV):
    """-> [(compiled pattern, civil_from, church_index_from, label)] from the sourced CSV."""
    out = []
    with open(path, encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            out.append((re.compile(row['pattern'], re.I), int(row['civil_from']),
                        int(row['church_index_from']), row['jurisdiction']))
    return out


JURISDICTIONS = load_jurisdictions()


def reachability(place, year):
    """-> (score 0..1, explanation). Unknown place is the worst case: nothing to search."""
    if not place:
        return (0.15, 'no birth place recorded')
    for pattern, civil, church, label in JURISDICTIONS:
        if pattern.search(place):
            if year is None:
                return (0.45, f'{label}, no year')
            if year >= civil:
                return (1.0, f'{label} civil reg from {civil}')
            if year >= church:
                gap = civil - year
                # Church registers thin out the further back you go before civil registration.
                return (max(0.2, 0.7 - gap / 200), f'{label}, {gap}y before civil reg {civil}, church index from {church}')
            return (0.2, f'{label}, before any indexed register ({church})')
    return (0.35, 'jurisdiction not recognised')


def search_state(pid, register_rows):
    """What the register says about this person: counts by outcome class."""
    c = {'hit': 0, 'absent': 0, 'coverage-unknown': 0, 'not-indexed': 0, 'not-online': 0, 'void': 0, 'unclear': 0}
    key = pid.strip('@').lower()
    for r in register_rows:
        if (r.get('person') or '').strip('@').lower() != key:
            continue
        k = r.get('nil_class') if r.get('result') == 'nil' else r.get('result')
        if k in c:
            c[k] += 1
    return c


def inferred_place(pid, indis, fams):
    """Where to look when the person's own birth place is blank.

    A missing birth place usually means we never recorded it, not that the person is
    unresearchable. Their children's births and their spouse's birth put them in a
    jurisdiction, which is exactly what a researcher would reason from. Returns
    (place, how) so the report can show the inference rather than hide it.
    """
    for fid in indis[pid]['fams']:
        f = fams.get(fid, {})
        for cid in f.get('chil', []):
            p = indis.get(cid, {}).get('birt_place')
            if p:
                return (p, "child's birth")
        for role in ('husb', 'wife'):
            sid = f.get(role)
            if sid and sid != pid:
                p = indis.get(sid, {}).get('birt_place')
                if p:
                    return (p, "spouse's birth")
    return (None, None)


def ancestors(indis, fams, root):
    """-> {id: generation}, generation 0 = root. Follows parents only."""
    parents_of = {}
    for f in fams.values():
        for c in f['chil']:
            parents_of.setdefault(c, []).extend(p for p in (f['husb'], f['wife']) if p)
    gen, q = {root: 0}, deque([root])
    while q:
        n = q.popleft()
        for p in parents_of.get(n, ()):
            if p not in gen:
                gen[p] = gen[n] + 1
                q.append(p)
    return gen, parents_of


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gedcom')
    ap.add_argument('--root', required=True, help='home person xref, e.g. @I1@')
    ap.add_argument('--top', type=int, default=30)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--all-rings', action='store_true', help='include ring-3 (beyond) people; default drops them')
    ap.add_argument('--register', help='register.jsonl; controlled absent nils lower the score, unqualified nils do not')
    args = ap.parse_args()

    indis, fams = gedlib.load(args.gedcom)
    rings = gedlib.load_rings()
    register_rows = []
    if args.register and os.path.exists(args.register):
        with open(args.register, encoding='utf-8') as fh:
            register_rows = [json.loads(l) for l in fh if l.strip()]
    gen, parents_of = ancestors(indis, fams, args.root)

    rows = []
    for pid, g in gen.items():
        if g == 0 or pid not in indis:
            continue
        if parents_of.get(pid):          # has at least one parent: not an end of line
            continue
        if not args.all_rings and rings.get(pid, 0) >= 3:   # ring 3 gets no budget (see docs/rings.md)
            continue
        i = indis[pid]
        year = i['birt'][0]
        place, via = i['birt_place'], None
        if not place:
            place, via = inferred_place(pid, indis, fams)
        reach, why = reachability(place, year)
        if via:
            reach *= 0.8          # inferred jurisdiction, so discount but do not discard
            why = f'{why} (via {via})'
        closeness = 1.0 / g
        score = closeness * reach
        searched = search_state(pid, register_rows) if register_rows else None
        if searched:
            # Each controlled absent nil says one reachable corpus is exhausted for this person.
            # Coverage-unknown, void and not-indexed rows leave the score alone: the gap is still open.
            score *= 1.0 / (1.0 + 0.5 * searched['absent'])
        rows.append({
            'score': round(score, 4),
            'gen': g,
            'id': pid,
            'name': i['name'] or '[no name]',
            'born': year,
            'place': place or '',
            'place_inferred': bool(via),
            'reach': round(reach, 2),
            'why': why,
            'sources': i['sources'],
            'ring': rings.get(pid, 0),
            'searched': searched,
        })
    rows.sort(key=lambda r: -r['score'])

    if args.json:
        print(json.dumps(rows[:args.top], indent=1))
        return

    total_anc = sum(1 for p, g in gen.items() if g > 0)
    print(f'{total_anc} direct ancestors of {indis[args.root]["name"]}, '
          f'{len(rows)} of them end-of-line\n')
    print(f'{"score":>6} {"gen":>3}  {"born":>5}  {"src":>3}  name / place / why')
    for r in rows[:args.top]:
        print(f'{r["score"]:>6.3f} {r["gen"]:>3}  {str(r["born"] or "?"):>5}  '
              f'{r["sources"]:>3}  {r["name"]}')
        print(f'{"":>21}{r["place"] or "[no place]"}  -- {r["why"]}')
        if r['searched'] and any(r['searched'].values()):
            print(f'{"":>21}searched: ' + ', '.join(f'{k} {v}' for k, v in r['searched'].items() if v))


if __name__ == '__main__':
    main()
