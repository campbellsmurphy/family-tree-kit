"""Rank the tree's end-of-line ancestors by how worth researching they are next.

An end-of-line is a direct ancestor with no parents recorded. Ranking them by generation
alone is the obvious mistake: a 6th-great-grandparent born in Victoria in 1860 is a far
better bet than a 3rd-great born in Kerry in 1820, because Victorian civil registration
exists from 1853 and Irish Catholic parish coverage before the Famine mostly does not.

So the score multiplies two things:
  closeness      - how few generations up, i.e. how much of the tree hangs off them
  reachability   - whether records plausibly exist for that place and year

Reachability uses civil-registration start dates per jurisdiction. Before the start date
the answer is parish/church registers, which are patchy and often not online, so the score
drops rather than going to zero.

usage: python3 tools/gapranker.py <gedcom> --root @I1@ [--top 30] [--json]
"""
import argparse
import json
import re
from collections import deque

import gedlib

# Civil registration begins. Year, and a label for the report.
JURISDICTIONS = [
    (r'victoria|vic\b',                      1853, 'Victoria'),
    (r'new south wales|nsw\b',               1856, 'NSW'),
    (r'queensland|qld\b',                    1856, 'Queensland'),
    (r'south australia',                     1842, 'South Australia'),
    (r'western australia|wa\b',              1841, 'Western Australia'),
    (r'tasmania|van diemen',                 1838, 'Tasmania'),
    (r'new zealand',                         1848, 'New Zealand'),
    (r'scotland',                            1855, 'Scotland'),
    (r'ireland|kerry|cork|limerick|clare',   1864, 'Ireland'),
    (r'england|wales|london|lancashire',     1837, 'England & Wales'),
    (r'india',                               1865, 'India (European returns)'),
    (r'germany|prussia|bavaria',             1876, 'Germany'),
    (r'denmark',                             1874, 'Denmark'),
    (r'canada|ontario',                      1869, 'Canada (Ontario)'),
]


def reachability(place, year):
    """-> (score 0..1, explanation). Unknown place is the worst case: nothing to search."""
    if not place:
        return (0.15, 'no birth place recorded')
    low = place.lower()
    for pattern, start, label in JURISDICTIONS:
        if re.search(pattern, low):
            if year is None:
                return (0.45, f'{label}, no year')
            if year >= start:
                return (1.0, f'{label} civil reg from {start}')
            gap = start - year
            # Parish registers thin out the further back you go before civil registration.
            return (max(0.2, 0.7 - gap / 200), f'{label}, {gap}y before civil reg {start}')
    return (0.35, 'jurisdiction not recognised')


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
    args = ap.parse_args()

    indis, fams = gedlib.load(args.gedcom)
    rings = gedlib.load_rings()
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


if __name__ == '__main__':
    main()
