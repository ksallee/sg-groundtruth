# Reports

One file per behaviour that should change, written for the team that owns the API rather than for a
caller working around it.

A report is not a finding. A finding records what the API does and ends in a line telling a caller what
to do about it. A report states what the caller had a right to expect, what happened instead, what it
costs, and the change that would fix it. Those are two audiences and two documents. A `verdict:` states
what was measured and issues no rule the measurement does not hold, so a proposal has nowhere to sit on
a finding.

A report never restates its evidence. `evidence:` names the entries that hold the calls, the responses
and the error strings verbatim, and the index and the site render this report under them. The **Actual**
section quotes only what the reader needs to see the defect.

| key | is |
|---|---|
| `evidence` | corpus paths, without the `.md`, of every entry that measured this. Each has to exist |
| `endpoints` | the calls, in the spelling the cards in `corpus/endpoints/` are named by |
| `kind` | `api` when the behaviour should change, `docs` when the behaviour is defensible and undocumented |
| `status` | `unreported`, `reported`, `acknowledged`, `fixed` or `wontfix` |
| `ticket` | the vendor's own reference. Required once `status` is past `unreported` |
| `confirmed` | `YYYY-MM-DD`, the last date the behaviour was observed |
| `summary` | one line: what the API does that it should not |

Sections, all five: **Expected**, **Actual**, **Reproduce**, **Impact**, **Proposed change**.

**Reproduce** is a transcript someone without this repository can run: `curl`, `$SITE` and `$TOKEN` for
the host and the bearer, and no probe harness. A report they cannot run themselves is a claim.

`confirmed` is what makes this list the re-probe queue. After a Flow Production Tracking release, the
reports name which probes to run again and which verdicts go stale if a fix landed.

## What belongs here

A 2xx that did not do what was asked, a successful call that removed data the caller never named,
and a contract the API states in one place and breaks in another. Those are the `silent`, `destructive`
and `trap` classes, and they are candidates rather than a queue: an unknown query parameter being
ignored is a design choice, not a defect. Three reports a reader can act on beat fifty they have to
triage.

Nothing here is filed against a person or a team. Say what happened, what it costs, and what would fix
it, and stop.
