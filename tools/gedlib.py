"""Minimal GEDCOM 5.5.1 reader shared by gedlint.py, gapranker.py and tree_mcp.py.

Deliberately not a general parser: it reads the tags this project actually uses and
ignores the rest. gedcheck.py already guards structural integrity, so nothing here
re-validates syntax - this assumes a file that gedcheck passes.
"""
import io
import os
import re

DATE_YEAR = re.compile(r'\b(\d{3,4})\b')
MONTHS = {m: i for i, m in enumerate(
    'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split(), 1)}
EVENTS = {'BIRT', 'DEAT', 'MARR', 'BURI', 'BAPM', 'CHR', 'DIV'}


def parse_date(val):
    """-> (year, month, day, qualifier). Any part may be None.

    Handles the common forms: '12 MAR 1891', 'MAR 1891', '1891',
    'ABT 1891', 'BEF 1891', 'BET 1891 AND 1893' (takes the first year).
    """
    if not val:
        return (None, None, None, None)
    up = val.upper()
    qual = None
    for q in ('ABT', 'BEF', 'AFT', 'EST', 'CAL', 'BET'):
        if up.startswith(q):
            qual = q
            break
    years = DATE_YEAR.findall(up)
    year = int(years[0]) if years else None
    month = next((MONTHS[t] for t in up.split() if t in MONTHS), None)
    day = None
    parts = up.split()
    for i, t in enumerate(parts):
        if t in MONTHS and i and parts[i - 1].isdigit() and len(parts[i - 1]) <= 2:
            day = int(parts[i - 1])
    return (year, month, day, qual)


def _ordinal(d):
    """Rough day-number for spacing comparisons. None unless year is known."""
    year, month, day, _ = d
    if year is None:
        return None
    return year * 365 + (month or 6) * 30 + (day or 15)


def _blocks(text):
    for blk in re.split(r'\n(?=0 @)', text):
        m = re.match(r'0 (@[^@]+@) (\w+)', blk)
        if m:
            yield m.group(1), m.group(2), blk


def _events(blk):
    """-> {tag: {'date':..., 'plac':...}} for level-1 event blocks."""
    out = {}
    cur = None
    for ln in blk.split('\n'):
        m = re.match(r'^1 (\w+)', ln)
        if m:
            cur = m.group(1) if m.group(1) in EVENTS else None
            if cur:
                out.setdefault(cur, {'date': None, 'plac': None})
            continue
        if cur:
            d = re.match(r'^2 DATE (.+)', ln)
            p = re.match(r'^2 PLAC (.+)', ln)
            if d:
                out[cur]['date'] = d.group(1).strip()
            elif p:
                out[cur]['plac'] = p.group(1).strip()
    return out


def resolve(path):
    """Hook for projects that relocate the GEDCOM; identity by default."""
    return path


def load(path):
    """-> (indis, fams). Each is {id: record-dict}."""
    text = io.open(resolve(path), encoding='utf-8', errors='replace').read()
    indis, fams = {}, {}
    for rid, kind, blk in _blocks(text):
        lines = blk.split('\n')
        if kind == 'INDI':
            name = next((l[7:].strip() for l in lines if l.startswith('1 NAME ')), '')
            given, _, rest = name.partition('/')
            surname = rest.rstrip('/').strip()
            ev = _events(blk)
            indis[rid] = {
                'id': rid,
                'name': name.replace('/', '').strip(),
                'given': given.strip(),
                'surname': surname,
                'sex': next((l[6:].strip() for l in lines if l.startswith('1 SEX ')), ''),
                'birt': parse_date(ev.get('BIRT', {}).get('date')),
                'deat': parse_date(ev.get('DEAT', {}).get('date')),
                'birt_place': ev.get('BIRT', {}).get('plac'),
                'deat_place': ev.get('DEAT', {}).get('plac'),
                'has_death_record': 'DEAT' in ev,
                'famc': [l[7:].strip() for l in lines if l.startswith('1 FAMC ')],
                'fams': [l[7:].strip() for l in lines if l.startswith('1 FAMS ')],
                'sources': sum(1 for l in lines if re.match(r'^\d SOUR @', l)),
                'apids': [l.split(' ', 2)[2].strip()
                          for l in lines if re.match(r'^\d _APID ', l)],
            }
        elif kind == 'FAM':
            ev = _events(blk)
            fams[rid] = {
                'id': rid,
                'husb': next((l[7:].strip() for l in lines if l.startswith('1 HUSB ')), None),
                'wife': next((l[7:].strip() for l in lines if l.startswith('1 WIFE ')), None),
                'chil': [l[7:].strip() for l in lines if l.startswith('1 CHIL ')],
                'marr': parse_date(ev.get('MARR', {}).get('date')),
            }
    return indis, fams


def load_rings(path=None):
    """Newest data/rings-*.json (from tools/rings.py) -> {id: ring}. Empty dict if none."""
    import glob, json, os
    if path is None:
        cands = sorted(glob.glob(os.path.join(os.environ.get('FTK_DATA', 'data'), 'rings-*.json')))
        if not cands:
            return {}
        path = cands[-1]
    return json.load(open(path))


def imported_set(path):
    """Ids of INDI and FAM records that are STILL second tier. A tagged INDI whose every FAMS family has been
    promoted (tag removed) counts as promoted too, even if the chain forgot to strip its own tag."""
    import re
    raw = io.open(resolve(path), encoding='utf-8', errors='replace').read()
    recs = re.split(r'(?m)^(?=0 )', raw)
    tag = lambda r: bool(re.search(r'^1 _TIER imported', r, re.M))
    fams = {m.group(1): tag(r) for r in recs for m in [re.match(r'0 (@F\d+@) FAM', r)] if m}
    out = {f for f, t in fams.items() if t}
    for r in recs:
        m = re.match(r'0 (@I\d+@) INDI', r)
        if not m or not tag(r): continue
        fs = re.findall(r'^1 FAMS (@F\d+@)', r, re.M)
        if fs and all(not fams.get(f, False) for f in fs): continue   # parent of a promoted family: promoted
        out.add(m.group(1))
    return out


def display(ind):
    """Name with year range, for report lines."""
    b, d = ind['birt'][0], ind['deat'][0]
    span = f" ({b or '?'}-{d or '?'})" if (b or d) else ''
    return f"{ind['name'] or '[no name]'}{span} {ind['id']}"
