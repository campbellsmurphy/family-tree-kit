# Rings: the spend policy

Rings are computed from the GEDCOM by `tools/rings.py` and never hand-tagged. Pick a root
(in the original project, the youngest generation, so both parents' sides count as blood).

| ring | who | budget |
|---|---|---|
| 0 blood | the root, their blood ancestors, every descendant of those ancestors | full |
| 1 in-law | spouse of a ring-0 person | normal |
| 2 in-law+1 | parents and siblings of a ring-1 person, and their spouses | light: one record per fact, no deep dives |
| 3 beyond | everyone else | zero; context only, never a worker, loop or browser target |
| 4 imported | anyone carrying `1 _TIER imported` | zero; leaves this ring only by promotion |

Rules that follow:

- Recompute after every fold. The rings file goes stale within a day on an active tree.
- Rankers drop ring 3 and above by default; an `--all-rings` flag restores them.
- Rings govern spend, not whether arrived evidence may be folded. Do not commission ring-3
  work, but fold a confirmed primary record when it lands.
- Living people are never worker targets, whatever their ring.

## The second tier

Other people's trees and FamilySearch parent sets are amalgamated inside the canonical file
as second-tier records: every such person and family carries `1 _TIER imported`, a
quality-1 citation naming the external id, and a note saying it is not evidence. They exist
for context. They are excluded from every queue, every share edition and every platform
upload (the upload artefact is built by stripping them structurally).

**Promotion**: when a primary record independently corroborates the imported parents, cite
it at quality 2 or 3 and delete the tier line from the family and from both parents. Rings
recompute on the next run.

## Within ring 0, rank by side

An inherited tree is lopsided, and every hint engine and closeness ranker compounds the
head start. The original project's correction: ring 0 first, and within ring 0 the
under-researched sides before the inherited one; deceased or born before 1930; and
under-sourced (fewer than two citations and fewer than three notes). Rank a record by
whether it names a parent, a sibling or a spouse, not by whether it confirms a date already
held. See [research bias](research-bias.md).
