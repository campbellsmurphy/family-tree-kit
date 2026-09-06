# Roadmap

What is ported, what is still in the private project, and what has never been built.

## Ported (runs on the fixture via `check.sh`)

- `gedlib.py`, `gedcheck.py`, `gedlint.py`, `gapranker.py`, `rings.py`: personal
  defaults removed, otherwise as they run on the real tree.
- `side_balance.py`: new, written for this kit from the measurement in
  [research bias](research-bias.md).
- `privacy_scan.py`: new.

## In the private project, to port next (in order of value)

1. **Structured citation writer** (`cite.py`, about 440 lines). Writes a `SOUR`/`PAGE`/
   `QUAY` block on a fact at fold time, with an `--audit` that lists facts with no citation
   and a `--verify` that checks the value against the citation. Needs its source-record
   templates generalised.
2. **Searched-corpus register** (about 380 lines, JSONL). Add, query, stats; a nil result
   requires a positive control. Port with a JSON Schema and an RLP-compatible CSV export.
3. **Hint-decision ledger** (about 340 lines, JSONL). Keyed on platform, collection,
   person, year, place; `--check <name>` before opening anyone; `--stats`.
4. **Share-edition builder** (about 570 lines). Strips living people to bare identity,
   removes a named side by construction, removes every internal and sensitive string.
   Port as the missing living-people stripper CLI, with tests.
5. **Upload artefact builder**: strips the imported tier and its pointers.
6. **Tree views and typed queries** (`tree_views.py`, `tree_mcp.py`): project the tree
   into markdown a wiki search can serve, and answer `find_person`, `relationship_path`,
   `end_of_lines`, `stats`.
7. **Novelty gate**: per-report verdicts of novel, already held, already searched, against
   the GEDCOM and the register.
8. **Registry identifier resolver**: check a civil-registration number against the
   registry's own index before it is folded.

## Not portable, and why

- The agent skill itself (about 200 KB) is mostly project history: which sessions broke
  what, which platform limits tripped when. The generic parts are in the
  [playbook](../playbook/PLAYBOOK.md).
- Platform navigation notes (Ancestry, findmypast, RootsIreland): tied to logged-in
  browser sessions and to UI that changes.
- Fleet supervisors for third-party model CLIs: tied to specific quota meters and
  sandboxes.
- The Trove, state-registry and cemetery clients: worth porting eventually, but each
  carries an API key or a rate-limit etiquette that has to be documented first.

## Never built, and wanted

- Living-detection rule with tests (age cap, no death event, descendant of a living person).
- A synthetic complete population to compare the tree against, per Calderón-Bernal et al.
- A pre-commit hook wiring for `privacy_scan.py`.
