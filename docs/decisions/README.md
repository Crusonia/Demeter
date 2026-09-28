# Decision log and ADR process

Use an architecture decision record for a major engine, module/interface,
operator-order, persistence, compatibility or release-design choice. If the
choice also changes scientific semantics, link a [scientific RFC](../rfcs/README.md).
A decision record does not activate later-phase mechanisms.

Open an issue, copy [TEMPLATE.md](TEMPLATE.md) to
`ADR-<issue-number>-short-slug.md`, and open a PR. Use the issue number as a stable
ID. Record context, alternatives, consequences, invariants, migration and tests.
Link relevant design registers and scientific-review requirements. Do not label
planned validation as completed.

Start with `proposed`. The maintainer records `accepted`, `rejected` or `deferred`
and the reason, review links and decision PR. Keep decision status separate from
implementation and scientific validation. An accepted design can remain
unimplemented; an implemented alpha can remain scientifically unvalidated.

Supersede substantive decisions through a new record and reciprocal links. Retain
the original rationale and dissent. Reopen when evidence or a failed invariant
changes the premise. Routine typo/link fixes do not require a new decision ID.
The directory and Git/PR history are the decision register; add each new ADR to
the table below in its PR.

## Existing decisions

| Record | Evidence and scope |
| --- | --- |
| [Health engine choice](../ENGINE_DECISION.md) | Existing NumPy/explicit-equation decision; retained as a legacy record. No retrospective claim of RFC review or scientific acceptance. |
| [Module API 1.0](../MODULE_API.md) | Implemented through [PR #46](https://github.com/Crusonia/Demeter/pull/46); typed contracts and annual health adapter. Broader domain adapters and scientific calibration remain open. |
| [Reproducible releases](ADR-21-reproducible-releases.md) | Issue #21; inspectable source/data/result snapshots, model cards and explicit numerical replay. Clinical fitting remains deferred. |

Templates contain prompts, not decisions. New entries must point to actual records
and review evidence rather than guessed dates or reviewer approvals.
