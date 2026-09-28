# Module and extension API 1.0

Demeter exposes versioned exchange contracts and an executable **health hazard
extension point**. A researcher can replace transition equations from an ordinary
Python package without changing the cohort engine, and add evidence dependencies
using an explicitly supplied registry. Python and CLI execution work offline.

API 1.0 describes the software contract, independently of the `0.1.0a1` model
release. It does not assert scientific maturity. These experiments remain
validation-only. Broader domain interfaces below are designs, not active models.

## Run an extension

```powershell
uv run demeter simulate scenarios/reduce_upf_30.yaml --transition-module demeter.examples.transition_modules:DietaryTransitions --output outputs/module-reference.json
uv run demeter simulate scenarios/reduce_upf_30.yaml --transition-module demeter.examples.transition_modules:NoDietEffect --output outputs/module-null.json
```

`DietaryTransitions` independently expresses the existing hazard formula using
only public contracts. `NoDietEffect` supplies registered baseline hazards and
ignores dietary modifiers: an alternative hypothesis, not an empirical claim.
Read the complete [example source](../src/demeter/examples/transition_modules.py).
Neither example imports private model or transition helpers.

```python
from demeter.schema import EvidenceRegistry, Scenario
from demeter.model import simulate
from demeter.examples.transition_modules import NoDietEffect
from demeter.health.module import simulation_series

registry = EvidenceRegistry.from_yaml("evidence/parameters.yaml")
scenario = Scenario.from_yaml("scenarios/reduce_upf_30.yaml")
result = simulate(registry, scenario, transition_module=NoDietEffect())
series = simulation_series(result)
print(series["population"].model_dump_json())
print(result.metadata["transition_module"])
```

For your package, replace the explicit import with your implementation. The CLI
accepts `importable.package:factory`, a named zero-argument callable returning a
`TransitionModule`. Install trusted code in the same environment first. There is
no automatic discovery, remote download, expression evaluation or module import
from scenario YAML. Python imports execute with the caller's permissions; the
contracts validate scientific exchanges, not sandbox arbitrary code.

## Shared typed contracts

Public types live in [`demeter.contracts`](../src/demeter/contracts.py).
Frozen Pydantic models provide JSON round trips and generated schemas, such as
`ModuleSpec.model_json_schema()`. Unknown fields and nonfinite numbers fail.
Values, nested axes and dependency snapshots use immutable tuples.

| Contract | Meaning |
| --- | --- |
| `Axis` | Named, ordered unique labels; reordering changes the contract. |
| `Port` | Shared quantity key, measurement definition, stock/flow/hazard/auxiliary kind, exact unit, labelled axes, and point/rate/interval-total time basis. |
| `Quantity` | Finite row-major values matching the product of axis sizes. A scalar has no axes and one value. Stocks/hazards are nonnegative. |
| `TimeSeries` | One unchanged port at increasing year coordinates. Point/rate observations have one time per row; interval totals have one more boundary than rows. |
| `ParameterDependency` | Exact registry key and unit; the registry supplies status, grade, provenance and uncertainty. |
| `ModuleSpec` | Namespaced ID, module/API versions, domain, step, input/output ports, dependencies, equation description and limitations. |
| `TransitionInterface` | Engine-provided health states, source/destination transitions, baseline-rate keys and ports. |
| `TransitionInputs` | Year, annual step, validated scenario JSON, interface, living stocks, dietary modifiers and immutable parameter snapshots. |
| `TransitionModule` | `describe(interface) -> ModuleSpec` and `hazards(inputs) -> Quantity`. |

`require_connection` requires an exact port match, including measurement
definition. Numeric shape alone is insufficient. People/thousands of people,
availability/intake, probabilities/hazards and different currency price years
are not interchangeable. Conversions, renaming and aggregation require explicit,
tested adapters. Unit tokens are checked exactly; there is no symbolic dimensional
algebra or inferred unit conversion.

An interval flow row is the amount moved between its two boundaries, not a rate.
Point samples of rates do not specify within-interval interpolation or integrals.
Preserve stock/flow identities when resampling; name death, migration, loss and
external-transfer sinks. `Transition` explicitly names current health sources
and destinations. `simulation_series(result)` exports recorded annual aggregate
stocks and death/transition counts without recalculation. Stock rows include the
initial boundary; flow rows exclude it. Keep the parent result's scenario,
registry hash, cohort tables and module provenance with these exchanges.

## Domain contracts and ownership

These are exchange designs across the mature architecture. The executable
adapter supports health hazards today; later rows do not activate broader models.

| Owner | Inputs | Output contract | Runtime status |
| --- | --- | --- | --- |
| Population | State composition, mortality, explicit birth/migration assumptions | People by age/sex/state at boundaries; interval deaths/births/migration; period/cohort life-table years | Current engine; birth/migration flows are zero |
| Nutrition | Defined exposure paths and registered response parameters | Relative UPF and dimensionless progression/recovery multipliers at the documented annual phase | Current UPF response; other causal exposures remain unresolved |
| Health | Population, dietary multipliers, baseline hazards, intervention modifiers | Labelled per-year hazards; realized people moved; mortality, prevalence and healthspan with definitions | API 1.0 hazard replacement; engine owns flow operator |
| Intervention | Eligible people and access/adoption/capacity schedules | Treatment people, interval starts/stops/restarts and conditional modifiers | Existing GLP-1 engine; arbitrary replacement needs a future adapter |
| Provider | Health flows, diagnosis/population-specific utilization mappings, payer/service-line definitions | Visits/admissions/procedures as interval counts; capacity; allowed spending, revenue and cost as separate accounts | Design only; no one-for-one disease-to-revenue assumption |
| Economics | Defined goods/actors, prices, quantities, contracts and budgets | Prices per defined good, purchases, counterpart transfers and actor revenue/cost/margin with currency/price year | Design only; transfers are not additional social value |
| Agriculture | Demand, land, inputs, weather and practices | Hectare stocks; production/losses in defined mass units; quality, inventory and capacity with region/product axes | Design only; no automatic practice-to-health effect |

Provider utilization must match actual diagnoses, populations and time windows.
Economic units encode currency and price year; food units preserve edible versus
as-purchased and availability versus intake bases. Scenarios declare what changes,
what stays fixed, eligibility and time path. Feedback uses information available
at that time, not future outcomes. These requirements complement the strict
current `Scenario` schema and the broader [scenario catalog](SCENARIO_CATALOG.md).

Each stock has one owner. Other modules propose named transfers or hazards; only
the owner applies them. A future linked runtime must declare operator order,
feedback delays, adapters and reconciliation tests. Reject duplicate stock writers
and inconsistent steps instead of creating implicit algebraic loops. The current
adapter has a fixed annual order; it is not a general-purpose scheduler.

## Executable annual health contract

1. The engine supplies the interface for legacy, risk_1 or risk_2 states.
2. `describe` declares the supplied three input ports and hazard output, required
   evidence keys, equations and limitations. Duplicate declarations, incompatible
   ports, unsupported API versions, non-health domains and nonannual steps fail.
3. Dependencies must exist, be resolved health-model inputs, match units and
   declare uncertainty. Benchmark records cannot become coefficients. Extra
   dependencies appear in the active/synthetic audit and result metadata.
   The declared hazard dependencies replace canonical baseline-hazard keys;
   unused baseline hazards need not be resolved. Other engine dependencies stay
   required, and a module cannot redefine a core parameter's units.
4. Each year, the module receives an immutable **start-of-year living stock**
   snapshot and the **current year-end dietary-response multipliers**, plus
   scenario JSON and parameter snapshots. Stocks include children; the engine
   applies adult eligibility. They are not survivor or post-transition stocks.
5. Return one finite nonnegative scalar hazard per transition in the supplied
   order. Outputs are revalidated even after bypassing Pydantic construction.
6. Existing GLP-1 modifiers, mortality, competing transitions and aging follow
   the engine's established order. Original-population and initial-PreChronic
   accounts continue to use the same hazards. Modules cannot replace stocks or
   move a person twice through an unchecked transfer.

Modules must be deterministic, stateless functions of declared inputs. Do not
read undeclared files, sample an internal RNG, retain cross-run state, mutate
global evidence, or hide substantive numeric coefficients in source. Coefficients
belong in the supplied registry. Alternative equation forms need distinct IDs or
versions and a documented hypothesis, not unrecorded constructor settings.

`ParameterValue.evidence_json` preserves the full source/uncertainty record;
`inputs.value(key)` fails for undeclared keys. Modules never receive the engine's
mutable registry or stock array. These protections prevent accidental mutation;
review and tests are still required to assess Python equations and evidence.

For uncertainty, draw externally from registered distributions and reuse each
registry draw in both scenarios. Evaluation is conditional on supplied values.
`TimeSeries` distinguishes fixed, conditional and sampled outputs; sampled output
requires a draw ID. Preserve joint draw identity across module boundaries;
independent resampling of shared parameters loses covariance. The current CLI
uncertainty/sensitivity/leverage commands select canonical equations. Use explicit
Python calls for custom runs rather than assuming those commands select a module.

Canonical dietary-pathway routing rejects custom modules: its switches cannot be
assumed to identify replacement equations. Custom diagnostics retain stocks,
flows and histories but omit the canonical equation dependency graph, which would
misdescribe the replacement. Inspect the contract, source and recorded annual
`module_base_hazards_per_year`. No automatic graph is inferred from Python code.

## Provenance and version rules

Custom-run metadata describes dietary responses as **supplied module inputs**,
not automatically applied effects. It does not claim canonical progression-path
or dietary/treatment independence assumptions for replacement equations. Annual
response fields retain their existing names for compatibility; their use in
hazards is module-defined. CLI results also record the exact `package:factory`
selection so a factory can be replayed even when its returned class has another
name. Python users preserve their explicit construction call with the run script.

Results record the complete `ModuleSpec`, implementation class, class-file
SHA-256, dependency records, API version and **experimental** classification.
The full registry hash and scenario metadata remain present. A name never promotes
a module to canonical/scientifically validated status. The source hash does not
cover transitive imports: preserve the source package and locked environment.

Scenario YAML retains the strict existing schema; module selection is an explicit
execution argument. Replay requires scenario **and** module/evidence, not the
scenario file alone. Supply a separately versioned registry to change parameters;
modules do not silently override canonical keys. New scenario assumptions require
a reviewed schema, not unknown YAML fields. Package catalogs/distribution are
#22 work; complete release bundles are #21 work.

| Change | Rule |
| --- | --- |
| Remove/rename public fields or methods; change temporal/axis meaning or order | New API major, with an explicit migration or retained old adapter |
| Add optional compatible fields or opt-in adapters | New API minor; same major and requested minor no newer than runtime |
| Implementation repair with unchanged contract | Package patch; preserve code hashes and rerun conformance tests |
| Change module equations or assumptions | New module version and scientific change record, even if API shape is unchanged |
| Change evidence values, grades, distributions or vintage | New registry hash and evidence review; API compatibility is not scientific equivalence |

Only API 1.0 is implemented. Unsupported versions fail before equations execute.
Module versions use `major.minor.patch`. Pin the implementation and registry hash;
an API version alone cannot reproduce results.

## Verification and design trace

`tests/test_module_api.py` checks labelled shapes, units, time bases, immutability,
version/domain/step rejection, invalid evidence/hazards, CLI loading, typed-output
conservation, exact canonical parity in all structures and response modes,
GLP-1/tagged-cohort parity, and the no-diet-effect alternative. Examples import
only public contracts. The full existing engine suite remains required.

Trace: health segment of P-02 and I-05/I-07/I-11/I-12; F-01/F-04/F-08;
T-01/T-02/T-05/T-08. Future adapters require their own equations, evidence,
temporal integration and tests. Scientific calibration remains a separate gate.
