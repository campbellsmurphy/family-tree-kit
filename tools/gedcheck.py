"""Nine structural checks on a GEDCOM 5.5.1 file, in one place.

Each was added because it caught a class the others were blind to:
  1 dangling refs        - a pointer to a record id that does not exist
  2 level sequence       - a line whose level jumps by more than one
  3 duplicate pointers   - the same pointer twice in one record (it.426)
  4 duplicate events     - the same event block twice on one record (it.450)
  5 duplicate NAME lines - two 1 NAME lines on one INDI (it.455)
  6 duplicate sub-tags   - the same singleton sub-tag twice in ONE event block (it.484)
  7 embedded tag mid-line - a structural line concatenated onto the end of the previous
                            one with no newline (it.567). Checks 1-6 are ALL blind to it:
                            the file greps fine and the words are all present, but every
                            GEDCOM parser swallows the second line into the first line's
                            value, so the note silently vanishes on export. Twelve were
                            found in one sweep, eleven of them pre-existing and three on
                            direct-line records.
  9 duplicate xref definition - the same `0 @Xnnn@ TYPE` appearing twice (it.1008). Checks
                            1-8 are ALL blind to it: they iterate every record BLOCK, so a
                            reused id is checked twice as two separate records rather than
                            flagged as one id defined twice. Every tool that instead parses
                            the file into an xref-keyed dict (query helpers,
                            ad-hoc GEDCOM-surgery python) silently keeps only the LAST
                            definition, so a stale duplicate FAM/INDI left behind by an
                            incomplete repair (it.933 created a replacement family but never
                            deleted the erroneous original, both headed `0 @F718@ FAM`) makes
                            every downstream read of that id wrong for as long as it survives.

Two of them are easy to write WRONG, and both traps are guarded here (it.461):
  - a dangling-ref check must match POINTER LINES ONLY (`^\\d+ TAG @X@$`), or it flags
    deleted ids merely quoted inside NOTE prose;
  - a duplicate-pointer check must be limited to HUSB/WIFE/CHIL/FAMS/FAMC, or it flags
    a legitimately repeated `1 SOUR @S3@`.

usage: python3 tools/gedcheck.py <gedcom>
exit status 0 = clean, 1 = something to look at.
"""
import io, re, sys
from collections import Counter

PTR = re.compile(r'^(\d+) (\w+) (@[^@]+@)\s*$')
LINKS = {'HUSB', 'WIFE', 'CHIL', 'FAMS', 'FAMC'}
EVENT = {'BIRT', 'DEAT', 'MARR', 'BURI', 'BAPM', 'CHR', 'DIV', 'RESI', 'IMMI', 'OCCU'}

# ⚠ Deliberately a NAMED tag list, not `\w+`. Note prose is full of things like
# "volume 10a page 268" and "born 1 SEP 1891", and a generic `\d+ \w+` pattern flags every
# one of them. Only tags that actually begin a structural line belong here.
# ⚠⚠ Two false-positive classes were measured on the live file when this was first written
# (it.568) and BOTH are guarded above, because either one alone makes the check unusable:
#   - "the it.383 NOTE stopped there"  -> the 3 of 383 read as a level. Hence no-digit-before.
#   - "@F36@ read '1 HUSB @I58@'"      -> a note QUOTING a gedcom line. Hence no-quote-before.
# A quoted example inside prose is the normal way a research note documents a structural repair,
# so flagging it would train the reader to ignore the check.
EMBEDDED = re.compile(
    r"(?<![\d'\"`])"          # not a digit: 'it.383 NOTE' is prose, not a level
    r'(?<=\S)'                 # something ran into it, i.e. no newline before it
    r'\d (NOTE|CONT|CONC|NAME|SOUR|PAGE|QUAY|DATA|TEXT|BIRT|DEAT|MARR|BURI'
    r'|FAMC|FAMS|HUSB|WIFE|CHIL|SEX|TITL|ABBR|PUBL|REPO|NICK) ')


def records(text):
    for blk in re.split(r'\n(?=0 @)', text):
        m = re.match(r'0 (@[^@]+@) (\w+)', blk)
        if m:
            yield m.group(1), m.group(2), blk


def check(path):
    text = io.open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\n')
    recs = list(records(text))
    ids = {rid for rid, _, _ in recs}
    problems = []

    # 1 dangling refs - POINTER LINES ONLY
    for rid, _, blk in recs:
        for ln in blk.split('\n')[1:]:
            m = PTR.match(ln)
            if m and m.group(3) not in ids:
                problems.append(f'dangling ref {m.group(3)} on {rid} ({m.group(2)})')

    # 2 level sequence
    prev = None
    for n, ln in enumerate(lines, 1):
        m = re.match(r'^(\d+) ', ln)
        if not m:
            continue
        lvl = int(m.group(1))
        if prev is not None and lvl > prev + 1:
            problems.append(f'level jump {prev}->{lvl} at line {n}: {ln[:60]}')
        prev = lvl

    # 3 duplicate pointer lists - link tags only
    for rid, _, blk in recs:
        seen = Counter()
        for ln in blk.split('\n')[1:]:
            m = PTR.match(ln)
            if m and m.group(2) in LINKS:
                seen[(m.group(2), m.group(3))] += 1
        for (tag, tgt), c in seen.items():
            if c > 1:
                problems.append(f'duplicate pointer {tag} {tgt} x{c} on {rid}')

    # 4 duplicate event blocks - same tag+DATE+PLAC twice at level 1
    for rid, _, blk in recs:
        blines = blk.split('\n')
        evs = []
        for i, ln in enumerate(blines):
            m = re.match(r'^1 (\w+)\s*$', ln)
            if not m or m.group(1) not in EVENT:
                continue
            date = plac = ''
            for sub in blines[i + 1:]:
                if re.match(r'^1 ', sub):
                    break
                d = re.match(r'^2 DATE (.*)', sub)
                p = re.match(r'^2 PLAC (.*)', sub)
                if d:
                    date = d.group(1)
                if p:
                    plac = p.group(1)
            evs.append((m.group(1), date, plac))
        for ev, c in Counter(evs).items():
            if c > 1 and (ev[1] or ev[2]):
                problems.append(f'duplicate event {ev} x{c} on {rid}')

    # 5 duplicate NAME lines on an INDI. ⚠ MORE THAN ONE 1 NAME IS LEGAL GEDCOM - a woman
    # properly carries a maiden and a married name. it.455 was about the SAME name twice,
    # so compare values, never the count (this check was first written wrong at it.478).
    for rid, typ, blk in recs:
        if typ != 'INDI':
            continue
        for nm, c in Counter(re.findall(r'^1 NAME (.*)$', blk, re.M)).items():
            if c > 1:
                problems.append(f'identical NAME "{nm}" x{c} on {rid}')

    # 6 duplicate sub-tags INSIDE one event block (it.484). Checks 1-5 are all blind to this:
    # a second `2 PLAC` on one BIRT is not a duplicate event, not a duplicate pointer and not a
    # duplicate NAME. Only tags that may appear ONCE per event are counted - SOUR and NOTE
    # legitimately repeat, so they are excluded.
    for rid, _, blk in recs:
        blines = blk.split('\n')
        for i, ln in enumerate(blines):
            m = re.match(r'^1 (\w+)', ln)
            if not m or m.group(1) not in EVENT:
                continue
            subs = Counter()
            for sub in blines[i + 1:]:
                if re.match(r'^1 ', sub):
                    break
                s = re.match(r'^2 (DATE|PLAC|TYPE|CAUS|AGE) ', sub)
                if s:
                    subs[s.group(1)] += 1
            for tag, c in subs.items():
                if c > 1:
                    problems.append(f'duplicate {tag} x{c} inside {m.group(1)} on {rid}')

    # 7 a structural line concatenated onto the previous one (it.567)
    for n, ln in enumerate(lines, 1):
        m = EMBEDDED.search(ln)
        if m:
            problems.append(f'embedded {m.group(1)} mid-line at line {n}: ...{ln[max(0, m.start()-40):m.start()+30]}')

    # 8 the trailer must be the LAST line: a conformant reader stops at TRLR, so any
    #   record after it is invisible to every parser while still counting here (it.612)
    trlr = [n for n, ln in enumerate(lines, 1) if ln.strip() == '0 TRLR']
    if not trlr:
        problems.append('no 0 TRLR trailer - the file does not terminate')
    else:
        if len(trlr) > 1:
            problems.append(f'{len(trlr)} TRLR lines at {trlr} - there must be exactly one')
        stranded = sum(1 for ln in lines[trlr[0]:] if ln.startswith('0 @'))
        if stranded:
            problems.append(
                f'0 TRLR at line {trlr[0]} with {stranded} top-level record(s) AFTER it - '
                'invisible to every conformant reader, including tree uploads')

    # 9 duplicate xref definition - the same id defined by more than one top-level block
    for rid, c in Counter(rid for rid, _, _ in recs).items():
        if c > 1:
            problems.append(f'duplicate xref definition {rid} x{c} - two separate 0-level blocks share this id')

    ni = sum(1 for _, t, _ in recs if t == 'INDI')
    nf = sum(1 for _, t, _ in recs if t == 'FAM')
    print(f'{path}\n{ni} individuals / {nf} families / {len(recs)} records')
    for p in problems:
        print('  ⚠', p)
    print('CLEAN - all nine checks pass' if not problems else f'{len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(check(sys.argv[1]))
