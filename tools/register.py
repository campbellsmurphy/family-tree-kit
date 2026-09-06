#!/usr/bin/env python3
"""The searched-corpus register: what has been searched, for whom, and what came back.

Answers, in one second and before any worker is dispatched: have we already searched
this person in this corpus, and what did we find? It exists because an audit of a
real tree found every documented negative living in prose notes nobody could query,
so the same dry searches were re-run for weeks.

Append-only JSONL, one row per search. A row is never edited; a correction is a new
row with `supersedes` set to the old row's id.

THE QUALIFIED NEGATIVE. "Not found" is four different facts, and only one of them
closes a gap:

  result=nil  nil_class=absent            searched a corpus that covers the place and
                                          period, with a positive control that proved
                                          the search worked. Counts toward exhaustion.
  result=nil  nil_class=not-indexed       the corpus holds the register but it is not
                                          name-searchable for that period. Browse job.
  result=nil  nil_class=not-online        the register exists but is not in this corpus
                                          at all. Different corpus needed.
  result=nil  nil_class=coverage-unknown  searched, nothing, and nobody has established
                                          whether the corpus covers that place and period.
                                          Does NOT count toward exhaustion.
  result=void                             a zero returned while rate-limited, throttled,
                                          logged out or erroring. Not a nil at all.

An `absent` row is refused without a `--control`: the search that returned rows in the
same corpus, same period, same district, proving the query path was working.

usage:
  register.py --add --person @I7@ --corpus "irishgenealogy.ie civil" --query "CASEY, Cork, 1922-1926" \
      --years 1922-1926 --place "Cork" --record-type birth --result nil --nil-class absent \
      --control "CASEY Cork 1924 returns 41 rows" --by session-3
  register.py --check "Norah Casey"        # everything searched for one person (name or xref)
  register.py --corpus irishgenealogy       # everything worked in one corpus
  register.py --negatives                   # every nil, with class and control
  register.py --exhausted @I7@              # is this person exhausted for the corpora searched?
  register.py --stats
  register.py --schema                      # the row schema as JSON Schema
  register.py --export-csv log.csv          # Research-Like-a-Pro compatible columns

The register path is $FTK_REGISTER, else data/register.jsonl.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import date

NIL_CLASSES = ('absent', 'not-indexed', 'not-online', 'coverage-unknown')
RESULTS = ('hit', 'nil', 'void', 'unclear')

SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'title': 'family-tree-kit searched-corpus register row',
    'type': 'object',
    'required': ['id', 'date', 'person', 'corpus', 'query', 'result'],
    'properties': {
        'id': {'type': 'string', 'description': 'sha1 of person+corpus+query+date'},
        'date': {'type': 'string', 'format': 'date'},
        'by': {'type': 'string', 'description': 'who or which session ran the search'},
        'person': {'type': 'string', 'description': 'xref like @I7@, or a name if not yet in the tree'},
        'person_name': {'type': 'string'},
        'corpus': {'type': 'string', 'description': 'the collection searched, named the way its own site names it'},
        'query': {'type': 'string', 'description': 'exact terms, every spelling variant tried, filters'},
        'years': {'type': 'string', 'description': 'date window searched, e.g. 1922-1926'},
        'place': {'type': 'string', 'description': 'jurisdiction or district the search was scoped to'},
        'record_type': {'type': 'string', 'description': 'birth, marriage, death, burial, census, newspaper, probate, ...'},
        'result': {'enum': list(RESULTS)},
        'nil_class': {'enum': list(NIL_CLASSES)},
        'control': {'type': 'string', 'description': 'the positive control that proved an absent nil is real'},
        'refs': {'type': 'array', 'items': {'type': 'string'}, 'description': 'record references found, for a hit'},
        'why_absence_matters': {'type': 'string', 'description': 'what an absent nil would mean, if anything'},
        'next': {'type': 'string', 'description': 'the search this one points to'},
        'note': {'type': 'string'},
        'supersedes': {'type': 'string', 'description': 'id of a row this one corrects'},
    },
}

RLP_COLUMNS = ['date', 'person_name', 'person', 'record_type', 'corpus', 'query', 'years', 'place',
               'result', 'nil_class', 'control', 'refs', 'why_absence_matters', 'next', 'note', 'by']


def register_path():
    return os.environ.get('FTK_REGISTER', os.path.join(os.environ.get('FTK_DATA', 'data'), 'register.jsonl'))


def rows():
    p = register_path()
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    superseded = {r['supersedes'] for r in out if r.get('supersedes')}
    return [r for r in out if r['id'] not in superseded]


def name_for_xref(gedcom, xref):
    if not gedcom or not os.path.exists(gedcom) or not xref.startswith('@'):
        return None
    hit = False
    with open(gedcom, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.startswith(f'0 {xref} INDI'):
                hit = True
            elif hit:
                if line.startswith('1 NAME '):
                    return line[7:].strip().replace('/', '').strip()
                if line.startswith('0 '):
                    return None
    return None


def add(a):
    if a.result == 'nil' and not a.nil_class:
        sys.exit('a nil needs --nil-class: ' + ', '.join(NIL_CLASSES))
    if a.result == 'nil' and a.nil_class == 'absent' and not a.control:
        sys.exit('an ABSENT nil needs --control: the search in the same corpus and period that returned rows. '
                 'Without one, record it as coverage-unknown.')
    if a.result != 'nil' and a.nil_class:
        sys.exit('--nil-class only applies to result=nil')
    when = a.date or date.today().isoformat()
    row = {
        'id': hashlib.sha1(f'{a.person}|{a.corpus}|{a.query}|{when}'.encode()).hexdigest()[:12],
        'date': when, 'by': a.by, 'person': a.person,
        'person_name': a.person_name or name_for_xref(a.gedcom, a.person),
        'corpus': a.corpus, 'query': a.query, 'years': a.years, 'place': a.place,
        'record_type': a.record_type, 'result': a.result, 'nil_class': a.nil_class,
        'control': a.control, 'refs': a.ref or [], 'why_absence_matters': a.why,
        'next': a.next, 'note': a.note, 'supersedes': a.supersedes,
    }
    row = {k: v for k, v in row.items() if v not in (None, [], '')}
    p = register_path()
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    with open(p, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    print('logged', row['id'], row['result'], row.get('nil_class', ''), row['corpus'], 'for', row.get('person_name') or row['person'])


def show(rs, limit=60):
    for r in rs[:limit]:
        tag = r['result'] + (f'/{r["nil_class"]}' if r.get('nil_class') else '')
        print(f'{r["date"]}  {tag:22s} {r["corpus"]:32s} {r.get("person_name") or r["person"]}')
        print(f'{"":12}{r["query"]}' + (f'  [{r["years"]}]' if r.get('years') else ''))
        if r.get('control'):
            print(f'{"":12}control: {r["control"]}')
        if r.get('refs'):
            print(f'{"":12}refs: {", ".join(r["refs"])}')
    if len(rs) > limit:
        print(f'... {len(rs) - limit} more')


def matches_person(r, key):
    k = key.lower().strip('@')
    return k in (r.get('person') or '').lower().strip('@') or k in (r.get('person_name') or '').lower()


def exhausted(rs, key):
    """Per corpus: is this person exhausted there? Only controlled absents count."""
    mine = [r for r in rs if matches_person(r, key)]
    if not mine:
        print(f'{key}: nothing registered. Not exhausted; not started.')
        return
    by_corpus = {}
    for r in mine:
        c = by_corpus.setdefault(r['corpus'], {'hit': 0, 'absent': 0, 'coverage-unknown': 0, 'not-indexed': 0, 'not-online': 0, 'void': 0, 'unclear': 0})
        c[r.get('nil_class') if r['result'] == 'nil' else r['result']] += 1
    print(f'{key}: {len(mine)} searches across {len(by_corpus)} corpora')
    for corpus, c in sorted(by_corpus.items()):
        if c['hit']:
            verdict = 'FOUND'
        elif c['absent']:
            verdict = 'EXHAUSTED (controlled absent)'
        elif c['coverage-unknown'] or c['void'] or c['unclear']:
            verdict = 'OPEN: nil not qualified, do not count as searched'
        else:
            verdict = 'OPEN: register not searchable here, needs a different route'
        counts = ', '.join(f'{k} {v}' for k, v in c.items() if v)
        print(f'  {corpus:32s} {verdict:48s} {counts}')


def stats(rs):
    from collections import Counter
    print(f'{len(rs)} rows, {len({r["person"] for r in rs})} people, {len({r["corpus"] for r in rs})} corpora')
    res = Counter(r['result'] + (f'/{r["nil_class"]}' if r.get('nil_class') else '') for r in rs)
    for k, v in res.most_common():
        print(f'  {k:28s} {v}')
    uncontrolled = [r for r in rs if r.get('nil_class') == 'absent' and not r.get('control')]
    if uncontrolled:
        print(f'  WARNING {len(uncontrolled)} absent rows without a control (legacy rows?)')


def export_csv(rs, path):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=RLP_COLUMNS, extrasaction='ignore')
        w.writeheader()
        for r in rs:
            r = dict(r)
            r['refs'] = '; '.join(r.get('refs', []))
            w.writerow(r)
    print(f'wrote {len(rs)} rows to {path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--add', action='store_true')
    ap.add_argument('--check')
    ap.add_argument('--corpus')
    ap.add_argument('--negatives', action='store_true')
    ap.add_argument('--exhausted')
    ap.add_argument('--stats', action='store_true')
    ap.add_argument('--schema', action='store_true')
    ap.add_argument('--export-csv')
    ap.add_argument('--gedcom', default=os.environ.get('FTK_GED'), help='to resolve a person xref to a name')
    ap.add_argument('--person'); ap.add_argument('--person-name'); ap.add_argument('--query')
    ap.add_argument('--years'); ap.add_argument('--place'); ap.add_argument('--record-type')
    ap.add_argument('--result', choices=RESULTS); ap.add_argument('--nil-class', choices=NIL_CLASSES)
    ap.add_argument('--control'); ap.add_argument('--ref', action='append')
    ap.add_argument('--why'); ap.add_argument('--next'); ap.add_argument('--note')
    ap.add_argument('--by'); ap.add_argument('--date'); ap.add_argument('--supersedes')
    a = ap.parse_args()

    if a.schema:
        print(json.dumps(SCHEMA, indent=1)); return
    if a.add:
        for f in ('person', 'corpus', 'query', 'result'):
            if not getattr(a, f):
                sys.exit(f'--add needs --{f}')
        add(a); return
    rs = rows()
    if a.check:
        show([r for r in rs if matches_person(r, a.check)])
    elif a.corpus and not a.add:
        show([r for r in rs if a.corpus.lower() in r['corpus'].lower()])
    elif a.negatives:
        show([r for r in rs if r['result'] in ('nil', 'void')])
    elif a.exhausted:
        exhausted(rs, a.exhausted)
    elif a.stats:
        stats(rs)
    elif a.export_csv:
        export_csv(rs, a.export_csv)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
