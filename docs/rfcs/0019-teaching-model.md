# RFC-19: A synthetic stock-and-flow teaching example

- Status: proposed for educational use
- Issue: [#19](https://github.com/Crusonia/Demeter/issues/19)
- Author: Codex, at the maintainer's direction, 2026-09-28
- Scientific assessment: not performed; no empirical claim proposed
- Scientific use: validation-only

## Scope and alternatives

Teach conservation, balancing feedback and delayed response with two containers
of abstract tokens. This is an isolated arithmetic example, not a new health,
agricultural, behavioral or economic mechanism. It cannot calibrate Demeter.
Population, geography, empirical period and design-register clinical/actor IDs
are inapplicable. No clinical definition or existing model equation changes.

The alternative is teaching only through the full age-structured health engine;
the smaller example makes a first step checkable by hand. Instant response and
zero transfer are useful alternative scenarios, not empirical null findings.

## Evidence and equations

Three new `toy_*` registry records have synthetic status, grade E and
`benchmark_only` role so the health engine cannot consume them. Initial stock is
100 tokens (fixed by the exercise); target transfer fraction is 0.25 per step
(uniform 0.1–0.4 for sensitivity experiments); response closes 0.5 of the gap per
step (uniform 0.25–1). These ranges are authored assumptions, not confidence
intervals. No external source, extraction, licence restriction or source receipt
applies; the example code and values are Demeter-authored under MIT.

The discrete step is one abstract tick, with no conversion to clinical years.
Initial received stock and effective fraction are zero by definition. At each
tick, first update `effective += response * (target - effective)`, then move
`flow = remaining * effective` tokens from remaining to received. Stocks are
boundary values; flow is an interval count, not a continuous hazard. Fraction
bounds are [0, 1]; stock is nonnegative. Depletion reduces future flow at a fixed
fraction: a balancing feedback. Response below one introduces gradual adjustment.

The example owns both stocks and never links to the health engine. Scenario
length is an execution choice; coefficient experiments use a copied registry.
Results retain the registry hash and all three parameter records.

## Predeclared checks and disposition

Check first-step arithmetic (12.5 tokens transferred), two-step remaining stock
(71.09375), conservation at every tick, zero/full transfer, immediate response,
rejected missing/unresolved/wrong-unit inputs and out-of-bounds fractions. Confirm
that changing toy parameters cannot alter canonical health results or active
health uncertainty dependencies. Execute notebook cells in order from a fresh
output directory in CI, including a scenario null and existing module null.

There is no calibration or empirical holdout for invented token dynamics. The
tutorial separately runs existing historical diagnostics, retaining their
limitations. Expected output precision is arithmetic, not scientific precision.

Independent software/scientific review is not claimed. Maintainer disposition is
recorded by the implementation PR; merging this teaching example is not scientific
acceptance. No known author financial interest; AI-assisted authorship disclosed.
Rollback removes the example, its registry entries and learning links without
changing the health engine. Empirical interpretation would require a new RFC.
