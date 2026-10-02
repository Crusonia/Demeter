# Check model parity during development

Save complete outputs before a change and compare them after it. This catches
code changes as well as changes to active inputs. The existing registry comparison
runs both registries through the current code; release replay instead requires
identical archived source bytes. This check fills the gap between those tools.

From a trusted source checkout, before editing or switching to a reviewed branch:

```bash
uv run python scripts/check_model_parity.py snapshot --output outputs/parity-before.json
```

After the change, using the same environment and the saved reference:

```bash
uv run python scripts/check_model_parity.py compare --reference outputs/parity-before.json --output outputs/parity-after.json
```

Both commands work in PowerShell, macOS and Linux. Keep the reference outside a
checkout you intend to remove. Outputs are never overwritten; use new names for
each checkpoint. Comparison returns exit code 1 when outputs differ and saves
the paths of mismatches. A damaged reference or changed checking contract fails
before recomputing outputs. Comparison reads JSON and executes only the currently
installed trusted model; it does not execute source from the reference.
Capture refuses a wheel or editable installation that loads Demeter from another
checkout, rather than attributing that runtime to the current checkout's receipts.

The fixed contract covers the complete original horizons of baseline, reduced
UPF, both PreChronic scenarios, dynamic dietary response and GLP-1 access. It
retains annual outputs, all final age cells, original-cohort state time,
diagnostic life tables, active hazard evidence and flows. Four seed-42 paired uncertainty draws for legacy
and PreChronic interventions retain sampled inputs and annual intervals. These
small runs test deterministic software behavior, not convergence of an empirical
uncertainty interval.

Results are compared with the existing release replay tolerances: relative
`1e-10`, absolute `1e-8`. Types, keys, dimensions, labels, state definitions,
active evidence records and validation-only warnings must match too. Exact
equality is reported separately from tolerance-based agreement. Only the explicit
registry identity paths `/metadata/evidence_sha256` and
`/healthspan/evidence_sha256` are removed from simulation outputs; uncertainty
removes only `/metadata/evidence_sha256`. Source bundle hashes and other provenance
inside results remain checked. Commit, dirty status, Python version, runtime
source hashes, registry hashes and scenario file hashes are retained separately
for both runs, so the receipt exposes the revisions being compared.

A passing parity check establishes unchanged behavior under this contract. It
does not establish correct equations, independent validation, clinical calibration
or scientific acceptance. Intentional behavior changes require inspecting the
reported differences and validating the new semantics, not overwriting the old
reference or widening tolerances. Checksums detect accidental modification; they
do not authenticate a reference obtained from an untrusted publisher.
