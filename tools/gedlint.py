"""Genealogical plausibility linter - the checks gedcheck.py is blind to.

gedcheck.py guards STRUCTURE (dangling refs, level jumps, duplicate blocks): a file can
pass it perfectly and still say a mother was born after her son. This covers MEANING, and
between them they cover the same ground as Ancestry's Pro Tools Tree Checker (duplicates,
people with no relationships, people with no sources, date logic) without expiring when a
tree is rebuilt.

Thresholds follow Gramps' "Verify the Data" defaults where one exists; each is a flag so a
genuine historical outlier can be tuned rather than argued with.

usage: python3 tools/gedlint.py <gedcom> [--json] [--only CLASS] [--max-age 110]
exit status 0 = clean, 1 = findings.
"""
import argparse
import json
import sys
from collections import defaultdict

import gedlib

THIS_YEAR = 2026


def _age(birth, event):
    if birth[0] is None or event[0] is None:
        return None
    return event[0] - birth[0]


def chronology(indis, fams, args):
    """Per-person and per-couple date logic."""
    out = []
    for i in indis.values():
        b, d = i['birt'], i['deat']
        if b[0] and d[0]:
            if d[0] < b[0]:
                out.append(('death-before-birth', f'{gedlib.display(i)}: died {d[0]}, born {b[0]}'))
            elif d[0] - b[0] > args.max_age:
                out.append(('implausible-lifespan',
                            f'{gedlib.display(i)}: {d[0] - b[0]} years'))
        for field, label in (('birt', 'birth'), ('deat', 'death')):
            y = i[field][0]
            if y and y > THIS_YEAR:
                out.append(('future-date', f'{gedlib.display(i)}: {label} dated {y}'))

    for f in fams.values():
        my = f['marr'][0]
        if not my:
            continue
        for role in ('husb', 'wife'):
            pid = f[role]
            if not pid or pid not in indis:
                continue
            p = indis[pid]
            age = _age(p['birt'], f['marr'])
            if age is None:
                continue
            if age < 0:
                out.append(('marriage-before-birth',
                            f'{gedlib.display(p)}: married {my}, born {p["birt"][0]}'))
            elif age < args.min_marriage_age:
                out.append(('child-marriage',
                            f'{gedlib.display(p)}: aged {age} at marriage {my} ({f["id"]})'))
            if p['deat'][0] and my > p['deat'][0]:
                out.append(('marriage-after-death',
                            f'{gedlib.display(p)}: married {my}, died {p["deat"][0]}'))
        h, w = f.get('husb'), f.get('wife')
        if h in indis and w in indis:
            hb, wb = indis[h]['birt'][0], indis[w]['birt'][0]
            if hb and wb and abs(hb - wb) > args.max_spouse_gap:
                out.append(('spouse-age-gap',
                            f'{f["id"]}: {abs(hb - wb)} years between '
                            f'{indis[h]["name"]} and {indis[w]["name"]}'))
    return out


def parenthood(indis, fams, args):
    """Parent ages at each child's birth, and posthumous births."""
    out = []
    for f in fams.values():
        for role, lo, hi, label in (
                ('wife', args.min_parent_age, args.max_mother_age, 'mother'),
                ('husb', args.min_parent_age, args.max_father_age, 'father')):
            pid = f[role]
            if pid not in indis:
                continue
            p = indis[pid]
            for cid in f['chil']:
                if cid not in indis:
                    continue
                c = indis[cid]
                age = _age(p['birt'], c['birt'])
                if age is None:
                    continue
                if age < lo:
                    out.append((f'{label}-too-young',
                                f'{gedlib.display(p)} aged {age} at birth of '
                                f'{gedlib.display(c)}'))
                elif age > hi:
                    out.append((f'{label}-too-old',
                                f'{gedlib.display(p)} aged {age} at birth of '
                                f'{gedlib.display(c)}'))
                # A child born after the mother's death year is impossible; after the
                # father's is normal within a year, so only flag a clear gap.
                pd = p['deat'][0]
                if pd and c['birt'][0]:
                    slack = 0 if role == 'wife' else 1
                    if c['birt'][0] > pd + slack:
                        out.append(('born-after-parent-died',
                                    f'{gedlib.display(c)} born {c["birt"][0]}, '
                                    f'{label} {p["name"]} died {pd}'))
    return out


def sibling_spacing(indis, fams, args):
    """Children of one mother born impossibly close together."""
    out = []
    for f in fams.values():
        dated = []
        for cid in f['chil']:
            if cid in indis:
                o = gedlib._ordinal(indis[cid]['birt'])
                if o and indis[cid]['birt'][1]:      # need at least a month to be meaningful
                    dated.append((o, cid))
        dated.sort()
        for (o1, a), (o2, b) in zip(dated, dated[1:]):
            gap = o2 - o1
            if 0 < gap < args.min_sibling_gap:
                out.append(('siblings-too-close',
                            f'{indis[a]["name"]} and {indis[b]["name"]} born {gap} days '
                            f'apart in {f["id"]} (twins not marked?)'))
    return out


def structure(indis, fams, args):
    """Tree Checker parity: isolated people, unsourced people, gender mismatches, cycles."""
    out = []
    for i in indis.values():
        if not i['famc'] and not i['fams']:
            out.append(('no-relationships', gedlib.display(i)))
        if i['sources'] == 0:
            out.append(('no-sources', gedlib.display(i)))
    for f in fams.values():
        if f['husb'] in indis and indis[f['husb']]['sex'] == 'F':
            out.append(('parent-sex-mismatch', f'{f["id"]}: HUSB {indis[f["husb"]]["name"]} is F'))
        if f['wife'] in indis and indis[f['wife']]['sex'] == 'M':
            out.append(('parent-sex-mismatch', f'{f["id"]}: WIFE {indis[f["wife"]]["name"]} is M'))

    parents = defaultdict(set)
    for f in fams.values():
        for c in f['chil']:
            for role in ('husb', 'wife'):
                if f[role]:
                    parents[c].add(f[role])

    def ancestors_of(start):
        seen, stack = set(), [start]
        while stack:
            n = stack.pop()
            for p in parents.get(n, ()):
                if p == start:
                    return True
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        return False

    for i in indis:
        if ancestors_of(i):
            out.append(('self-ancestry-cycle', gedlib.display(indis[i])))
    return out


REGISTRATION = __import__('re').compile(r'\b(\d{3,7}/\d{4})\b')


def _registrations(indis, path):
    """Registration numbers cited on each person, read from citation PAGE lines.

    A shared registration is NOT on its own a duplicate signal: a marriage certificate
    is legitimately cited on bride, groom and both sets of parents, and a birth
    certificate on the child and both parents. It only becomes diagnostic when the two
    people also carry the same name and year (see below).
    """
    import io
    import re as _re
    text = io.open(path, encoding='utf-8', errors='replace').read()
    out = defaultdict(set)
    for blk in _re.split(r'\n(?=0 @)', text):
        m = _re.match(r'0 (@[^@]+@) INDI', blk)
        if not m:
            continue
        for ln in blk.split('\n'):
            if _re.match(r'^\d PAGE ', ln):
                out[m.group(1)].update(REGISTRATION.findall(ln))
    return out


def duplicates(indis, fams, args):
    """Same surname + given + birth year within a window: merge candidates, not merges.

    Promoted to 'duplicate-confirmed' when the pair also cites the same registration
    number, which in practice means two records were built from one source document.
    """
    out = []
    regs = _registrations(indis, args.gedcom)
    buckets = defaultdict(list)
    for i in indis.values():
        if i['surname'] and i['given'] and i['birt'][0]:
            buckets[(i['surname'].lower(), i['given'].split()[0].lower())].append(i)
    for (sur, giv), group in buckets.items():
        group.sort(key=lambda x: x['birt'][0])
        for a, b in zip(group, group[1:]):
            if abs(a['birt'][0] - b['birt'][0]) <= args.dup_year_window:
                shared = regs[a['id']] & regs[b['id']]
                cls = 'duplicate-confirmed' if shared else 'duplicate-candidate'
                note = f' [both cite {", ".join(sorted(shared))}]' if shared else ''
                out.append((cls, f'{gedlib.display(a)} vs {gedlib.display(b)}{note}'))
    return out


def reciprocity(indis, fams, args):
    """FAM<->INDI pointer asymmetry: a FAM names someone whose own INDI record

    lacks the matching FAMS/FAMC, or vice versa. gedcheck.py only checks that a
    pointer resolves to a real record, never that the record points back
    (the it1220/it.762/it.982 defect class - spot-fixed twice before this
    check existed, in only one direction each time).
    """
    out = []
    for f in fams.values():
        for role in ('husb', 'wife'):
            pid = f[role]
            if pid and pid in indis and f['id'] not in indis[pid]['fams']:
                out.append(('fam-missing-fams',
                            f'{f["id"]} {role.upper()} {gedlib.display(indis[pid])} '
                            f'has no matching FAMS'))
        for cid in f['chil']:
            if cid in indis and f['id'] not in indis[cid]['famc']:
                out.append(('fam-missing-famc',
                            f'{f["id"]} CHIL {gedlib.display(indis[cid])} '
                            f'has no matching FAMC'))
    for i in indis.values():
        for fid in i['fams']:
            fam = fams.get(fid)
            if fam and i['id'] not in (fam['husb'], fam['wife']):
                out.append(('indi-missing-fam-role',
                            f'{gedlib.display(i)} FAMS {fid} but {fid} '
                            f'names neither HUSB nor WIFE as {i["id"]}'))
        for fid in i['famc']:
            fam = fams.get(fid)
            if fam and i['id'] not in fam['chil']:
                out.append(('indi-missing-fam-chil',
                            f'{gedlib.display(i)} FAMC {fid} but {fid} '
                            f'has no matching CHIL'))
    return out


CHECKS = {
    'chronology': chronology,
    'parenthood': parenthood,
    'spacing': sibling_spacing,
    'structure': structure,
    'duplicates': duplicates,
    'reciprocity': reciprocity,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gedcom')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--only', choices=sorted(CHECKS), action='append')
    ap.add_argument('--max-age', type=int, default=110)
    ap.add_argument('--min-marriage-age', type=int, default=14)
    ap.add_argument('--min-parent-age', type=int, default=14)
    ap.add_argument('--max-mother-age', type=int, default=52)
    ap.add_argument('--max-father-age', type=int, default=75)
    ap.add_argument('--max-spouse-gap', type=int, default=30)
    ap.add_argument('--min-sibling-gap', type=int, default=200)
    ap.add_argument('--dup-year-window', type=int, default=2)
    args = ap.parse_args()

    indis, fams = gedlib.load(args.gedcom)
    findings = []
    for name in (args.only or sorted(CHECKS)):
        findings += CHECKS[name](indis, fams, args)

    if args.json:
        print(json.dumps([{'class': c, 'detail': d} for c, d in findings], indent=1))
    else:
        by_class = defaultdict(list)
        for c, d in findings:
            by_class[c].append(d)
        print(f'{len(indis)} people, {len(fams)} families, {len(findings)} findings\n')
        for c in sorted(by_class, key=lambda k: -len(by_class[k])):
            print(f'== {c} ({len(by_class[c])})')
            for d in by_class[c]:
                print(f'   {d}')
            print()
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
