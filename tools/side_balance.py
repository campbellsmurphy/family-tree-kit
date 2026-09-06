#!/usr/bin/env python3
"""Measure how lopsided the tree is between family sides, and whether the lopsidedness
is a head start, an effort gap, or a records gap.

Every inherited tree is unbalanced: someone researched one side for twenty years and
handed it over. Hint engines, sibling enumeration and any "closest end-of-line first"
ranker then grow the tree in proportion to what is already there, so the head start
compounds unless you measure it and rank against it.

You name the sides by giving one representative person per side (usually the root's
parents, and the root's partner). Everyone is assigned to the nearest seed over the
family graph, with the root (and optionally other cut points) removed so the sides do
not bleed into each other through the root.

For each side it reports: people, mean citations per person, share with zero citations,
mean notes per person, and the top birth countries (a proxy for record reachability).
Give it an earlier snapshot with --baseline to see growth per side since then, and a
JSONL ledger with --ledger (any file whose rows carry an "xref" field) to see effort
per side.

usage:
  python3 tools/side_balance.py tree.ged --root @I1@ --side paternal=@I2@ --side maternal=@I3@
         [--side partner=@I4@] [--cut @I5@] [--baseline old.ged] [--ledger decisions.jsonl] [--json]
"""
import argparse
import collections
import json
import re


def parse(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    indi, fam = {}, {}
    for blk in re.split(r'(?=^0 @)', text, flags=re.M):
        m = re.match(r'^0 @([^@]+)@ (INDI|FAM)', blk)
        if m:
            (indi if m.group(2) == 'INDI' else fam)[m.group(1)] = blk
    return indi, fam


def assign_sides(indi, fam, seeds, cut):
    adj = collections.defaultdict(set)
    for blk in fam.values():
        mem = re.findall(r'^1 (?:HUSB|WIFE|CHIL) @([^@]+)@', blk, re.M)
        for a in mem:
            for c in mem:
                if a != c:
                    adj[a].add(c)
    side = dict(seeds)
    q = collections.deque(seeds)
    while q:
        x = q.popleft()
        for y in adj[x]:
            if y in cut or y in side:
                continue
            side[y] = side[x]
            q.append(y)
    return side


def stats(ids, indi):
    n = len(ids)
    if not n:
        return {'people': 0}
    sour = [len(re.findall(r'^\d SOUR ', indi[i], re.M)) for i in ids]
    note = [len(re.findall(r'^\d NOTE', indi[i], re.M)) for i in ids]
    countries = collections.Counter()
    for i in ids:
        m = re.search(r'^1 BIRT\n(?:2 DATE [^\n]+\n)?2 PLAC ([^\n]+)', indi[i], re.M)
        if m:
            countries[m.group(1).split(',')[-1].strip()] += 1
    return {
        'people': n,
        'mean_citations': round(sum(sour) / n, 2),
        'pct_zero_citations': round(100 * sum(1 for s in sour if s == 0) / n),
        'mean_notes': round(sum(note) / n, 2),
        'top_birth_countries': countries.most_common(4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gedcom')
    ap.add_argument('--root', required=True, help='the home person; removed from the graph so sides stay separate')
    ap.add_argument('--side', action='append', required=True, metavar='LABEL=@Ixx@',
                    help='one representative person per side; repeatable')
    ap.add_argument('--cut', action='append', default=[], help='extra people to remove from the graph (e.g. the root\'s children)')
    ap.add_argument('--baseline', help='an earlier snapshot of the same tree, same xrefs')
    ap.add_argument('--ledger', help='JSONL of research decisions with an "xref" field per row')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    seeds = {}
    for s in a.side:
        label, _, xref = s.partition('=')
        seeds[xref.strip('@')] = label
    cut = {x.strip('@') for x in [a.root] + a.cut}

    indi, fam = parse(a.gedcom)
    imported = {i for i, b in indi.items() if '1 _TIER imported' in b}
    side = assign_sides(indi, fam, seeds, cut)
    groups = collections.defaultdict(list)
    for i in indi:
        if i not in imported:
            groups[side.get(i, 'unassigned')].append(i)

    report = {label: stats(ids, indi) for label, ids in groups.items()}

    if a.baseline:
        b_indi, _ = parse(a.baseline)
        base = collections.Counter(side.get(i, 'unassigned') for i in b_indi if i not in imported)
        for label in report:
            then = base.get(label, 0)
            report[label]['baseline_people'] = then
            report[label]['growth_x'] = round(report[label]['people'] / then, 1) if then else None

    if a.ledger:
        eff = collections.Counter()
        with open(a.ledger) as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                x = (row.get('xref') or '').strip('@')
                eff[side.get(x, 'unassigned') if x else 'no-xref'] += 1
        for label in report:
            n = report[label]['people']
            report[label]['ledger_rows'] = eff.get(label, 0)
            report[label]['ledger_rows_per_person'] = round(eff.get(label, 0) / n, 2) if n else None

    if a.json:
        print(json.dumps(report, indent=1))
        return
    total = sum(r['people'] for r in report.values())
    print(f'{a.gedcom}: {total} people in the primary tier, {len(imported)} imported (excluded)\n')
    for label, r in sorted(report.items(), key=lambda kv: -kv[1]['people']):
        pct = 100 * r['people'] / total if total else 0
        print(f'{label:12s} {r["people"]:5d} ({pct:2.0f}%)  cit/person {r.get("mean_citations", 0):.2f}  '
              f'zero-cit {r.get("pct_zero_citations", 0)}%  notes/person {r.get("mean_notes", 0):.2f}')
        if 'baseline_people' in r:
            print(f'{"":12s} baseline {r["baseline_people"]} -> x{r["growth_x"]}')
        if 'ledger_rows' in r:
            print(f'{"":12s} ledger rows {r["ledger_rows"]} ({r["ledger_rows_per_person"]} per person)')
        if r.get('top_birth_countries'):
            print(f'{"":12s} born: ' + ', '.join(f'{c} {n}' for c, n in r['top_birth_countries']))
    print('\nRead it as: a side with FEWER people but SIMILAR citations and ledger rows per person is a')
    print('head-start gap, not a neglect gap. Fix it by ranking targets against side, not just closeness.')


if __name__ == '__main__':
    main()
