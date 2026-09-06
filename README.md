# family-tree-kit

Tooling and method for running family-history research with an LLM agent against a
canonical GEDCOM file, with none of the family in it.

This is the scaffolding extracted from a real project: an inherited 1990s Family Tree
Maker file that grew, over three months of agent-driven research, from roughly 640 people
with one source record to 3,300 people with 175 source records and 12,000 logged hint
decisions. Everything here is the part that generalises. The tree, the ledgers and the
research notes stay private.

**It contains no personal data.** The only GEDCOM in the repo is a synthetic fixture.
`tools/privacy_scan.py` refuses a commit that mentions anything on a denylist kept outside
the repo.

## The shape of it

- **The GEDCOM in your own files is the source of truth.** Ancestry, findmypast,
  FamilySearch and the rest are research surfaces: disposable hint engines that you upload
  to and never round-trip from. An export from a platform destroys your citation grades and
  renumbers every id.
- **A fact is not folded until it carries a citation.** Prose notes hold the reasoning and
  the negatives. Structured citations hold what software can read.
- **Everything searched is registered**, including what came back empty and what positive
  control proved the search was working. The register is what stops an agent re-running the
  same dry search next month.
- **Decisions are keyed on the record, not on the platform's hint id.** Platform hints reset
  to zero every time a tree is rebuilt. A ledger outside the platform is the only memory.
- **Spend follows the graph.** Rings computed from the tree decide who gets a deep dive,
  who gets one record per fact, and who gets nothing.

## Tools

| Tool | What it answers |
|---|---|
| `tools/gedcheck.py` | Is the file structurally sound? Nine checks, each added after it caught a real defect. |
| `tools/gedlint.py` | Does the file make sense? Impossible ages, parent-age outliers, duplicate people, unsourced people. Gramps-derived thresholds, all flags. |
| `tools/gapranker.py` | Which end-of-line ancestor next? Closeness times record reachability, using civil-registration start dates per jurisdiction. |
| `tools/rings.py` | Who is in scope? Ring 0 blood, 1 in-law, 2 in-law+1, 3 beyond, 4 imported. |
| `tools/side_balance.py` | Is the tree lopsided, and is it a head start, an effort gap, or a records gap? |
| `tools/privacy_scan.py` | Does anything private appear in the tracked files? |

`tools/gedlib.py` is the shared minimal reader: stdlib only, reads the tags the tools use,
assumes a file that `gedcheck.py` passes.

```bash
./check.sh          # runs every tool against fixtures/sample.ged
```

## Docs

- [How the tree was built](docs/how-the-tree-was-built.md): the honest account, with the
  measurements that forced each tool into existence.
- [Evidence rules](docs/evidence-rules.md): the eight rules the agent may never bend.
- [Methodology](docs/methodology.md): the Genealogical Proof Standard and the three
  analytical layers, as the project applies them.
- [Rings](docs/rings.md): the spend policy and the second tier for imported people.
- [Research bias](docs/research-bias.md): why an inherited tree grows lopsided and how to
  measure it.
- [Prior art](docs/prior-art.md): what exists already and what this borrows.
- [Roadmap](docs/roadmap.md): what is ported, what is still in the private project.
- [Agent playbook](playbook/PLAYBOOK.md): the working loop and the pitfalls, written for
  an LLM agent.

## Critique wanted, and where the gaps are

This is published to be picked apart, by people and by other models. Open an issue on
anything: a check that is wrong, a rule that is too strict, a ranker that rewards the
wrong thing. None of the tools are gatekept; if a private one on the
[roadmap](docs/roadmap.md) would help you, ask and it moves up the list.

The method was built on a tree that is deep in Australia and shallow everywhere the
records are harder: Ireland before 1864, Scotland, England outside the census, and the
India Office registers. Region-specific research lanes for those are the next thing
wanted, and contributions from people who know those archives are the most valuable
kind.

## Licence

MIT. The methodology draws on the Board for Certification of Genealogists' Genealogical
Proof Standard and Elizabeth Shown Mills' Evidence Explained, cited in the docs rather
than reproduced.
