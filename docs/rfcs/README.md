# Scientific RFCs

An RFC records a proposed scientific/model change before implementation. Start
with an issue using the **Scientific model or evidence change** form, then copy
[TEMPLATE.md](TEMPLATE.md) to `RFC-<issue-number>-short-slug.md` in this directory.
The issue number is the stable ID. Small evidence-only corrections may use the
complete evidence record in a PR as described in the
[review policy](../SCIENTIFIC_REVIEW.md).

Open a draft PR for the RFC. The author marks its status `proposed`; discussion
may result in `accepted`, `rejected`, `deferred`, or `withdrawn`. The maintainer
records the rationale and review links before merging a disposition. Acceptance
approves the stated design and scope; it does not assert implementation or
scientific validity. Implement within the active phase, link the implementation
PR, and update those separate fields with actual evidence.

Retain rejected and deferred records when they explain a material decision.
For a substantive replacement, create a new RFC, mark the old one `superseded`
and link both directions. Do not renumber records or erase objections. Corrections
to spelling/links can use an ordinary PR without changing the decision's meaning.

The merged RFC files and their Git/PR history form the register. The template is
not an accepted proposal, and no historical decision is retroactively described
as reviewed by this process.
