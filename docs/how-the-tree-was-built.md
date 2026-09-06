# How the tree was built

An honest account. Every number below was measured on the real project; names are left out.

## The inheritance

The starting point was a Family Tree Maker 16 file, a 1996-vintage Windows program, last
edited in 2014, found in a parent's cloud drive alongside its own backups. It held about
640 people. 92 percent of them were on the side of the family that parent had researched
for twenty years. The other parent's side had 22 people. The partner's side had none.

Getting it out of the proprietary `.FTW` binary took a strings extraction to prove what was
inside, then a free desktop genealogy program to import it and export GEDCOM 5.5.1. The
import left artefacts that kept turning up for weeks: quoted nicknames that had eaten the
surname (`/"Ern/`), note fragments that had become fake people, a marriage that already
carried a date the agent did not expect.

## The audit that shaped everything

Three weeks in, an audit of the file found **one source record across 1,027 people**. The
research had been real; it was all in prose. 1,583 notes carried citations, negative
searches and reasoning that no software could query and that an agent could only read.
That is why the same sources kept being re-pulled: four bad fleet specs in a row asked
workers to find records the notes already held.

Three tools came out of that audit, and they are the core of the method:

- **A structured citation writer.** A fold is not complete until the fact carries a
  `SOUR` pointer with a `PAGE`, a `QUAY` grade and the date it was folded. The rule was
  set by the person who inherited a tree with no citations and had to rebuild the
  provenance from scratch: the tree has to outlive its author and be handable to someone
  else.
- **A searched-corpus register.** One line per search: person, corpus, name forms tried,
  date window, result, and for a nil result the positive control that proved the search
  was working. Answers "have we already searched this person here?" in one second before
  a worker is dispatched. It grew to 9,500 rows.
- **A hint-decision ledger** keyed on the record's own identity (platform, collection,
  person, year, place) and never on the platform's hint id. Platform hints are computed
  per tree and destroyed when the tree is replaced; every GEDCOM refresh reset thousands
  of triaged hints to unreviewed. The ledger reached 12,000 rows. The single most
  expensive mistake in the project was a session that read the platform's "9,286 pending"
  counter as outstanding work and spent a night re-harvesting hints the ledger had already
  decided.

## The platform is an engine, not a home

The canonical file lives in a plain-text wiki. Ancestry gets an upload artefact built from
it, and is used for what it is good at: hints and record search on a logged-in browser.
Nothing comes back the other way. A real test of round-tripping an export destroyed all
1,732 citation quality grades and renumbered every person id, which would have broken
every reference the wiki was written against.

There is no partner API for Ancestry outside two desktop vendors, no route to one, and the
desktop program cannot be driven headlessly. The browser is the API. FamilySearch's API
excludes personal use by policy. Both facts cost days to establish and are recorded so
nobody spends them again.

## Checks that accreted from defects

`gedcheck.py` has nine structural checks. Each exists because it caught a class the others
were blind to: dangling pointers, level jumps, a pointer repeated in one record, an event
block repeated, the same name line twice, a singleton sub-tag repeated inside one event,
a structural line concatenated onto the previous one with no newline (invisible to grep,
swallowed silently by every parser, twelve found in one sweep), records stranded after the
trailer, and one id defined by two blocks.

Two of them are easy to write wrong. A dangling-ref check must match pointer lines only,
or it flags deleted ids that notes legitimately quote as breadcrumbs. A duplicate-pointer
check must be limited to the link tags, or it flags a repeated `SOUR`.

`gedlint.py` covers meaning: a file passes every structural check while claiming a mother
was born after her son. Its first run found four duplicate children the research loop
had created in one night, each pair citing the same birth registration. Duplicate
detection now runs at the end of every enumeration pass, before anything is folded.

## Ranking what to do next

Ranking end-of-line ancestors by generation alone is the obvious mistake. A distant
ancestor born in Victoria in 1860 is a far better bet than a closer one born in Kerry in
1820, because Victorian civil registration exists from 1853 and Irish parish coverage
before the Famine mostly does not. `gapranker.py` multiplies closeness by reachability,
where reachability comes from a table of civil-registration start dates per jurisdiction.

That same logic is one reason the tree grows lopsided. See [research bias](research-bias.md).

## Spend follows the graph

Rings are computed from the tree, never hand-tagged: the root, their blood ancestors and
every descendant of those ancestors are ring 0; spouses of ring 0 are ring 1; parents and
siblings of ring 1 are ring 2; everyone else is ring 3 and gets no research budget. People
imported from other researchers' trees carry a tag that puts them in ring 4, are excluded
from every queue and every upload, and leave only when a primary record corroborates them.

## The agent loop, and what it got wrong

The research ran as chained agent sessions, each writing a handoff for its successor, with
fleets of cheaper workers for volume and the main agent as judge. The failures are the
useful part:

- Read-only workers returned 109 of 110 verdicts as "needs image", because every free
  index needs a query string their fetch tool could not send. A shell fixed it.
- Specs built from dates and places alone made a worker reject the exact cemetery plot the
  tree already cited, because the surname was the married name. Every spec now carries
  parents, spouse, children and the married surname.
- Ranking targets by hint count spends the budget re-deriving facts on the people already
  researched hardest. Rank by how unresearched the record is: source and note counts.
- Eight concurrent workers produced 91 HTTP 429s from volunteer-run indexes. A zero
  returned while rate-limited is void, not a nil, and is registered as such.
- 471 citations claimed a first-hand image read and 12 recorded a held image. The rule
  now: save the image in the same pass you read it, and put the path in the citation.
- The loop's own briefing files bloated until starting an iteration cost more tokens than
  the research it did. A tool now emits a short resume brief; the megafiles are consulted
  per target.

## Where it stands

3,360 people, 959 families, 175 source records, 12,342 hint decisions, about 9,500
register rows, nine structural checks clean. The under-researched sides are now ranked
first by policy, which is the correction the bias measurement demanded.
