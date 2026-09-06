# Prior art

Surveyed 2026-09-07. What exists, and what this kit borrows or deliberately does not.

## GEDCOM libraries and validators

- python-gedcom (nickreynke), GPL-2, GEDCOM 5.5, maintained. GPL is the reason this kit
  ships its own stdlib reader rather than depending on it.
- ged4py (andy-z), MIT, 5.5.1 read-only parser tuned for large files.
- gedcom-lite and gedcom-skills (vaelen, 2026), MIT, stdlib-only 5.5.1 and 7 with
  round-trip fidelity and a Claude Code plugin wrapper. Closest in spirit to `gedcheck.py`.
- FamilySearch GEDCOM 7 spec repo (Apache-2.0) and the GEDCOM-registries YAML: a
  machine-readable tag vocabulary worth adopting for the structural checker.
- Gramps "Verify the Data" (GPL-2): the nearest prior art to `gedlint.py`; its thresholds
  are where ours came from.

## LLM and agent genealogy

- mattprusak/autoresearch-genealogy (MIT, the most-starred prior art): an Obsidian research
  template with a negative-search log, autonomous research prompts and archive guides for
  Ireland, England and Wales, Scotland and Australia. Markdown only.
- sliday/genealogy-research (MIT): the best negative-result model found. A nil must carry
  place, years, denomination, record type and spellings, and be classed not-indexed,
  not-online or coverage-unknown. `register.py` adopts that taxonomy.

- Open-Genealogy / GRA (Steve Little), CC-BY-NC-SA-4.0. The most rigorous published
  playbook: three-layer evidence classification, five-element citations, a five-state
  confidence scale, hard never-fabricate rules. The NC licence means cite, do not copy.
- Family Locket's Claude custom skill turns a research log into a footnoted report. Its
  published failure: the model left two conflicting death dates unreconciled. Correlation
  with what is already held has to be its own explicit step.
- raphink's MCP servers (Geni, newspapers, archives). Key failure: the model invented
  kinship between two same-surname people. The fix was a ground-truth tree every claim is
  checked against before a relationship is asserted, which is this kit's canonical-GEDCOM
  design.
- Gramps MCP servers (several, AGPL): CRUD bridges with no evidence rules.
- "Turn anything into a GEDCOM" prompts: both major models emit importable GEDCOM from a
  self-contradicting article and handle the contradiction silently.

## Method

- Genealogical Proof Standard (Board for Certification of Genealogists).
- Evidence Explained (Mills, 4th ed. 2024); QuickLesson 11 on identity and the FAN
  principle.
- Research Like a Pro (Family Locket): research-log templates in xlsx and Airtable.
  Columns: date, objective, repository, citation, search parameters, results including nil,
  comments. Nobody ships a machine-readable schema for it.

## Privacy and fixtures

- Gramps' GEDCOM export has a four-mode living-people filter. No maintained standalone
  privatiser exists in Python; a documented living-detection rule with tests is a gap.
- Public fixtures: royal92.ged (public domain), findmypast/gedcom-samples (fictional
  trees), GEDCOM 7 minimal and maximal samples. Tamura Jones' torture tests are
  copyrighted and link-only.

## What this kit borrows

- MIT and stdlib-only in the hot path.
- Gramps' rule catalogue as the semantic-lint baseline, thresholds as flags.
- Record-identity keys for hint decisions and an append-only ledger.
- The GPS three-layer classification, cited not copied.
- Relationship assertions checked against the canonical file before write.
- Fixtures only in the repo; the real file, the ledgers and share editions ignored.

## What is still missing from the ecosystem, and on this kit's roadmap

- A living-people stripper as its own CLI with tests.
