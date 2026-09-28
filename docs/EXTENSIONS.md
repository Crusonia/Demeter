# Local scenario and module packages

Packages identify authorship, licensing, compatible model/API versions, declared
evidence status, validation status, and exact input/source bytes. They use the
[existing transition API](MODULE_API.md); no new clinical equations or fitted
parameters are introduced. **Every package run remains validation-only.**

| Origin | Meaning |
| --- | --- |
| `canonical` | Project baseline package listed in the reviewed, versioned catalog |
| `experimental` | Project alternatives listed in that catalog |
| `third_party` | Explicitly registered local package; its publisher declarations are unverified |

Canonical means project ownership, not clinical validity. Only
[`extensions/catalog.yaml`](../extensions/catalog.yaml) assigns the first two
classifications. The local registry cannot assign a classification or register a
`demeter.*` identity. Catalog changes require normal project review. A checksum
detects changed bytes; it does not authenticate a publisher or approve evidence.

## List and run the project packages

Run these commands from the source checkout with `uv sync --group dev` completed:

```powershell
uv run demeter extensions list
uv run demeter extensions run demeter.core@1.0.0 baseline --output outputs/package-baseline.json
uv run demeter extensions run demeter.experiments@1.0.0 reduce_upf_30 --module null --output outputs/package-null.json
```

Omitting `--module` uses the canonical engine with the selected scenario. Module
selection is explicit and recorded; a scenario cannot silently enable Python.
The experimental package exposes `reference` (canonical hazard arithmetic) and
`null` (existing no-diet-effect alternative), plus existing experimental scenarios.

## Register a local package

The [community example](../examples/community_null/package.yaml) can be copied
as a whole directory. It contains no new coefficient or clinical hypothesis.
Although maintained here as a teaching example, its local loading route is always
classified `third_party`.

```powershell
uv run demeter extensions inspect examples/community_null/package.yaml
uv run demeter extensions register examples/community_null/package.yaml
uv run demeter extensions run community.null@1.0.0 reduce_upf_30 --module null --output outputs/community-null.json
```

`inspect`, `register`, and `list` parse manifests and scenarios and verify hashes;
they **do not import package code**. Registration links an absolute manifest path
and its SHA-256 in ignored `outputs/extension-registry.yaml`. It does not copy,
download, install dependencies, or publish a package. Use `--local-registry PATH`
on registration/list/run/compare to maintain a separate registry. Keep the package
directory available. A changed registered version is rejected; publish a new
version, or use a separate registry when relocating an unchanged package.

`run` and `compare` explicitly execute the selected local Python factory. Python
has normal process permissions: this is **not a sandbox**. Inspect the source and
run only packages you trust. The loader prevents declarative evidence overrides
and accidental input mutation; it cannot constrain malicious Python imports.

## Package layout and manifest

```text
my_package/
  package.yaml
  scenario.yaml
  module.py          # optional; class and zero-argument factory in this file
  evidence.yaml      # optional; additive, namespaced records only
  LICENSE
```

Use the complete example manifest as the schema template. Required fields are
`schema_version: 1`, namespaced `package_id`, `version` (`major.minor.patch`),
`authors`, `license`, `description`, `model_versions`, `module_api`,
`health_structures`, `evidence_status`, `validation_status`, `validation_notes`,
`limitations`, `files`, and `scenarios`. `modules` and `evidence` are optional.

- `model_versions` explicitly lists tested Demeter software versions. API
  compatibility uses the public API's major/minor rules. Health structure names
  must match the strict scenario schema. Compatibility is not clinical transport.
- `evidence_status` is `synthetic`, `mixed`, `sourced`, or `unresolved`;
  `validation_status` is `unvalidated` or `software_tested`. These are publisher
  declarations. The actual active evidence audit and run checks are separate.
- `files` maps portable, relative paths to lowercase SHA-256 hashes. Every
  selected scenario, module and evidence file must be listed. Paths stay inside
  the package directory and may not traverse symlinks. Preserve exact bytes;
  use LF for text files committed to this repository. Hash after formatting.
- `scenarios` maps local entry names to YAML paths. Each uses the existing strict
  `Scenario` schema and validation mode. No package field extends that schema.
- `modules` maps names to `{file: module.py, factory: MyModule}`. The factory
  takes no arguments and returns a transition module whose class is defined in
  that pinned file. Single-file entry modules are supported; no sibling-import
  path is added. Imports of Demeter or installed dependencies use the current
  environment. Preserve that environment and source commit as well as package
  files; the manifest does not fingerprint arbitrary transitive imports.

For a new or changed package, compute each file's SHA-256 after final formatting,
update the manifest version, then register it. On Windows,
`Get-FileHash PATH -Algorithm SHA256` prints a hash; convert it to lowercase in the
manifest. Project maintainers additionally pin the manifest itself in the
curated catalog. Do not edit an old package version to hide a source change.

## Evidence additions and override rules

An optional `evidence.yaml` may contain only `parameters`, `sources`, and
`scientific_blockers`. Each new parameter/source key must begin with the full
package namespace, for example `community.null.example_rate`. Records use the
existing [evidence schema](../evidence/README.md), including units, status,
provenance, uncertainty and model role. This is a packaging convention, not an
exemption from Demeter's evidence requirements: project-adopted substantive
numeric parameters must also be represented in `evidence/parameters.yaml`.

The loader rejects collisions even when proposed values are identical, rejects
dataset replacements, and appends blockers without removing existing ones.
It clones the supplied base registry and validates the merged records before
importing Python. The module adapter still rejects unresolved or benchmark-only
dependencies and inconsistent units. New values do not silently replace engine
keys; a replacement equation must explicitly declare its own dependency keys.
The CLI's explicit `--evidence PATH` selects the base registry and records its
hash, as existing commands do; it is not a package override mechanism.

## Compare alternatives

```powershell
uv run demeter extensions compare demeter.core@1.0.0 baseline demeter.experiments@1.0.0 prechronic_baseline --output outputs/structure-comparison.json
uv run demeter extensions compare demeter.core@1.0.0 baseline community.null@1.0.0 reduce_upf_30 --right-module null --output outputs/null-comparison.json
```

Both sides must have equal horizon, mortality vintage, sex, mode and starting
population. Each uses the same base evidence, with separately recorded additive
records. Unlike ordinary scenario comparison, this command permits different
health structures. It reports absolute and relative differences in final-period
life expectancy, final-period T2D-free expectancy, and cumulative deaths. It
preserves both complete runs, including state definitions and allocations.
It does not subtract healthy-state years whose definitions differ. Differences
can reflect starting allocations, scenario assumptions and equations together;
they are descriptive contrasts, not causal attribution or calibrated findings.
These package commands are deterministic conditional evaluations; they do not
propagate uncertainty. Existing uncertainty/sensitivity commands are unchanged
and do not automatically discover or run registered packages.

## Results and reproducibility

Every simulation now includes `metadata.extension_provenance`. Direct Python or
legacy import execution records no registered packages and identifies any
unregistered module explicitly; it never infers authorship from a class name.
Registered runs include the selected scenario/module entry, complete manifest,
classification, file/manifest hashes, base and merged evidence hashes, added
keys, actual evidence audit, and validation/uncertainty scope. The existing
module receipt retains equations, dependency records and source-class hash.

Archive the result, complete package directory, base registry, source checkout,
and locked environment. The [release tool](RELEASES.md) currently builds and
replays canonical runs; it does not automatically archive local third-party
directories or replay package selections. Local registry paths are machine-local.
The curated catalog and examples ship in source checkouts/source archives;
wheel-only users can register external directories but need to supply their own
scenario/evidence paths. There is no remote marketplace, automatic discovery,
dependency resolver, authenticity service or clinical approval in this version.
