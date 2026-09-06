# Research bias in an inherited tree

The question that prompted this document: the tree kept growing on one side. Was that
because records were available there, or because of how the tooling was designed?

Both, and they compound. Here is the measurement from the original project, run with
`tools/side_balance.py` against the current file, the earliest snapshot, and the
hint-decision ledger.

| side | at inheritance | now | growth | citations per person | ledger rows per person | top birth countries |
|---|---:|---:|---:|---:|---:|---|
| inherited side | 588 (92%) | 2,530 (78%) | 4.3x | 2.32 | 3.1 | Australia 45%, England 7% |
| other parent's side | 22 | 476 | 21.6x | 2.22 | 3.6 | Australia 39%, Ireland 4% |
| partner's side | 0 | 235 | new | 1.53 | 3.4 | India 38% |

Read it in three parts.

**The head start is the dominant cause.** The inherited side started with 27 times the
people. It has grown less in proportion than the other sides, yet it added more people in
absolute terms than the other two sides hold in total.

**Effort per person is roughly even.** Ledger rows per person, the best proxy for research
attention, are within 15 percent across the sides. The tree was not neglecting anyone. It
was doing the same work per person on a population that was already lopsided.

**Availability shows up in citations per person, not in growth.** The partner's side, born
mostly in India, carries a third fewer citations per person: the relevant registers sit
behind a subscription wall and a daily view limit. The Irish-born line is small because
pre-1864 Irish parish coverage is thin and the 1922 record loss took the census.

## How the tooling compounds the head start

- **Hint engines scale with what exists.** Every person uploaded generates hints for
  siblings, spouses and children. A side with 2,000 people produces 2,000 people's worth of
  hints; a side with 22 produces 22.
- **A closeness-times-reachability ranker prefers the reachable.** `gapranker.py` scores
  Victorian 1860 above Kerry 1820 on purpose. That is correct for yield per token and wrong
  for balance, and it needs a counterweight.
- **Sibling and co-resident enumeration is widest where census substitutes exist.**
  Australian electoral rolls and newspapers, English census pages: all on the inherited
  side.
- **The agent's own notion of "next" is the tree it can see.** Nothing in a loop that
  picks from end-of-lines will ever pick a person who is not in the file yet, and the
  missing sides were missing.

## The correction

1. Measure it. `side_balance.py` with a baseline snapshot and the ledger, after every
   large pass.
2. Rank against side inside ring 0: the under-researched sides first, deceased, under-sourced.
3. Prefer records that name relatives over records that confirm dates. A death registration
   naming parents is the single richest document for extending a thin line backwards.
4. State the fraction. A report that says "268 people added" without saying 93 percent
   were on one side is how the bias hides.

## Prior art

Calderón-Bernal, Alburez-Gutierrez and Zagheni (European Journal of Population, 2025,
open access) simulate a fully recorded population and infuse three structural biases
(lineage survival, limited collateral coverage, selective omission) to measure what
genealogies get wrong. Their method, compare the tree against a synthetic complete
population, is the rigorous version of what `side_balance.py` approximates with a
baseline snapshot. Nothing found in the published literature names the "records digitised
and free" gradient or the "inherited branch" effect as a measured quantity; that is the
gap this measurement fills.
