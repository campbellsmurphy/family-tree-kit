# Agent playbook

For an LLM agent working a family tree against a canonical GEDCOM. This is the generic
core of a much longer private skill; the private version is mostly history of what broke.

## Two layers

The **canonical GEDCOM** in your own files is the source of truth. **Platforms** (Ancestry,
findmypast, FamilySearch, MyHeritage) are hint engines and record search surfaces: upload
to them, never round-trip from them. The wiki always wins.

## How to start

1. Run `gedcheck.py` and `gedlint.py`. Do not research on a file that fails either.
2. Recompute `rings.py`. Read the register and the ledger stats before opening any person.
   The platform's pending-hint counter is the platform's memory and it resets on every
   rebuild; it is never a measure of outstanding work.
3. Pick targets from `gapranker.py`, then re-rank against side (see docs/research-bias.md)
   and against how unresearched the person is (source and note counts), never by hint
   volume.
4. Route each target to the right source before touching a browser. Newspapers, gazettes,
   free civil indexes and cemetery databases are API or query-string jobs. Login-walled
   images are browser jobs and cost the most; batch them.

## The working loop

1. **Check what is held.** Grep the tree and the register for the person. Read their
   notes. Half of what a hint offers is already in the file.
2. **Read the record**, not the index. An index is a search key; attach nothing without
   opening the image where one exists. If you open an image and take a fact off it, save
   the image in the same pass and put the path in the citation.
3. **Verify identity** with at least two independent anchors before folding. On a mismatch,
   enumerate the innocent explanations first: remarriage, married versus maiden surname,
   index mangling, age rounding, nickname drift.
4. **Fold** with the safe-edit pattern: snapshot, assert the exact old block is present,
   replace, single write, then structural check, counts, dangling refs, connectivity.
5. **Cite** on the fact, with a quality grade and the fold date. A fold without a citation
   is not complete.
6. **Register** every search with `register.py`, including nils. An absent nil needs the
   positive control that proves the search worked; a nil in a corpus whose coverage you have
   not established is coverage-unknown. A zero returned while rate-limited is void, not a nil.
   Before calling a person exhausted, run `--exhausted` and read the verdict per corpus.
7. **Log the hint decision** keyed on the record, not the hint id.
8. **Report** the tally with the fraction: which side, which ring, how many were new versus
   already held.

## Pitfalls that cost real sessions

- **Married surnames.** A tree that shows women under maiden names will make a worker
  reject the correct record for carrying the married one. Every spec states the married
  surname and says not to reject on it.
- **Specs without relatives collapse to "needs image".** Carry parents, spouse, children.
- **Hint-ranked batches re-derive cited facts.** Rank by source count, ascending.
- **Volunteer-run indexes are shared infrastructure.** Cap concurrency around three, sleep
  between requests, back off on 429, stop, and mark the zero void.
- **"Confirmed" from a worker means the article exists**, not that it is your person.
  Identity verdicts are the judge's job, never a worker's.
- **Same-surname is not kin.** Never assert a relationship the canonical tree does not
  hold without a record that names it.
- **Two retellings are not two sources.** Check the accounts do not share an upstream.
- **A stale note is not evidence of an open gap.** Tags outrank notes; check the structured
  data before believing prose that says something is missing.
- **Duplicate people.** Run the duplicate check at the end of every enumeration pass,
  before folding.
- **A "left" decision records that a hint exists**, not what the record says. Revisiting
  one is real work; say so, and do not call the inventory new.
- **Read-only workers cannot do this job.** Every free index needs a query string.
- **Living people are never targets.** Sensitive people in the file are flagged and handled
  by the judge, facing the family, never by a worker.

## Costs

A hint review is about two calls per person plus fold time; a mature tree is about 80
percent duplicates. Batch five to eight people per report. Work the free index before
buying any certificate; know which registries print parents on a death entry and which
never do, so you do not buy a certificate hoping for a generation it cannot give.
