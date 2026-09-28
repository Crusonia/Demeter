"use client";
import type {
  Entry,
  Experiment,
  Parameter,
  Receipt,
  Scenario,
  AccessStep,
} from "../lib/types";

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = "any",
  help,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number | string;
  help?: string;
}) {
  return (
    <label>
      {label}
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {help && <small>{help}</small>}
    </label>
  );
}
export default function Controls({
  request,
  entries,
  parameters,
  runs,
  bounds,
  onChange,
  onPreset,
  onRun,
  onValidate,
  busy,
}: {
  request: Experiment;
  entries: Entry[];
  parameters: Record<string, Parameter>;
  runs: Receipt[];
  bounds: number[];
  onChange: (r: Experiment) => void;
  onPreset: (id: string) => void;
  onRun: () => void;
  onValidate: () => void;
  busy: boolean;
}) {
  const scenario = request.scenario;
  const update = (patch: Partial<Scenario>) =>
    onChange({ ...request, scenario: { ...scenario, ...patch } });
  const glpFields: {
    key: keyof AccessStep;
    label: string;
    percent?: boolean;
  }[] = [
    { key: "start_year", label: "Start year" },
    { key: "access_fraction", label: "Access (%)", percent: true },
    { key: "coverage_fraction", label: "Coverage (%)", percent: true },
    { key: "supply_fraction", label: "Supply share (%)", percent: true },
    { key: "monthly_price_usd", label: "Monthly price ($)" },
    { key: "monthly_copay_usd", label: "Monthly copay ($)" },
  ];
  return (
    <div className="experiment-layout">
      <div className="form-main">
        <section className="form-section">
          <p className="eyebrow">01 · Choose your starting point</p>
          <h2>Set up an experiment</h2>
          <div className="form-grid">
            <label>
              Model / scenario
              <select
                value={request.catalog_id}
                onChange={(e) => onPreset(e.target.value)}
              >
                {entries.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.classification === "canonical" ? "Core" : "Experimental"}{" "}
                    · {e.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Experiment name
              <input
                value={scenario.name}
                maxLength={120}
                onChange={(e) => update({ name: e.target.value })}
              />
            </label>
          </div>
          <p className="meta">{scenario.description}</p>
          <div className="form-grid three">
            <NumberField
              label="Model years"
              value={scenario.years}
              min={1}
              max={100}
              step={1}
              onChange={(years) => update({ years })}
            />
            <label>
              Reference population
              <select
                value={scenario.sex}
                onChange={(e) => update({ sex: e.target.value })}
              >
                <option value="all">All sexes</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </label>
            <label>
              Mortality / population vintage
              <select
                value={scenario.baseline_year}
                onChange={(e) =>
                  update({ baseline_year: Number(e.target.value) })
                }
              >
                {[2022, 2023, 2024].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Health structure
            <select
              value={scenario.health_structure}
              onChange={(e) =>
                onChange({
                  ...request,
                  overrides: {},
                  scenario: { ...scenario, health_structure: e.target.value },
                })
              }
            >
              <option value="legacy">
                Three states · health / IR-prediabetes / T2D
              </option>
              <option value="risk_1">
                PreChronic · candidate definition 1
              </option>
              <option value="risk_2">
                PreChronic · candidate definition 2
              </option>
            </select>
            <small>
              Changing structure resets advanced overrides. PreChronic
              definitions are research proxies, not diagnoses.
            </small>
          </label>
        </section>
        <section className="form-section">
          <p className="eyebrow">02 · Change a lever</p>
          <h2>Food exposure & timing</h2>
          {!scenario.upf_schedule.length && !scenario.diet.upf && (
            <NumberField
              label="UPF reduction from reference (%)"
              value={
                Math.round((1 - (scenario.exposures.upf ?? 1)) * 100000) / 1000
              }
              min={(1 - bounds[1]) * 100}
              max={(1 - bounds[0]) * 100}
              onChange={(value) =>
                update({
                  exposures: { ...scenario.exposures, upf: 1 - value / 100 },
                })
              }
              help="A relative change in the modeled UPF exposure. This does not define a complete real-food basket."
            />
          )}
          {Object.entries(scenario.diet).map(([key, diet]) => (
            <NumberField
              key={key}
              label={`${key.replaceAll("_", " ")} target (${diet.unit})`}
              value={diet.target}
              min={0}
              onChange={(target) =>
                update({
                  diet: { ...scenario.diet, [key]: { ...diet, target } },
                })
              }
              help={`${diet.reference_period} · ${diet.role === "context_only" ? "Context only: has no independent modeled health effect" : "Uses the model's synthetic UPF response"}`}
            />
          ))}
          {scenario.upf_schedule.length > 0 && (
            <>
              <p>
                Each step sets exposure from its start year until the next step.
                Years must be unique, increasing, and within the horizon.
              </p>
              {scenario.upf_schedule.map((step, index) => (
                <div className="schedule-row" key={index}>
                  <NumberField
                    label={`Food step ${index + 1}: year`}
                    value={step.start_year}
                    min={1}
                    max={scenario.years}
                    step={1}
                    onChange={(start_year) =>
                      update({
                        upf_schedule: scenario.upf_schedule.map((s, i) =>
                          i === index ? { ...s, start_year } : s,
                        ),
                      })
                    }
                  />
                  <NumberField
                    label={
                      step.unit === "percent_energy"
                        ? "UPF (% of energy)"
                        : "UPF relative exposure"
                    }
                    value={step.value}
                    min={0}
                    onChange={(value) =>
                      update({
                        upf_schedule: scenario.upf_schedule.map((s, i) =>
                          i === index ? { ...s, value } : s,
                        ),
                      })
                    }
                    help={step.reference_period ?? "Reference = 1"}
                  />
                  <button
                    className="text-button"
                    disabled={scenario.upf_schedule.length === 1}
                    onClick={() =>
                      update({
                        upf_schedule: scenario.upf_schedule.filter(
                          (_, i) => i !== index,
                        ),
                      })
                    }
                  >
                    Remove step {index + 1}
                  </button>
                </div>
              ))}
              <button
                className="secondary"
                onClick={() => {
                  const last = scenario.upf_schedule.at(-1)!;
                  update({
                    upf_schedule: [
                      ...scenario.upf_schedule,
                      { ...last, start_year: last.start_year + 1 },
                    ],
                  });
                }}
              >
                Add food step
              </button>
            </>
          )}
          <div className="form-grid">
            <label>
              Response timing
              <select
                value={scenario.diet_response.kind}
                onChange={(e) =>
                  onChange({
                    ...request,
                    overrides: {},
                    scenario: {
                      ...scenario,
                      diet_response: { kind: e.target.value, shape: "linear" },
                    },
                  })
                }
              >
                <option value="legacy">Simple exposure lag</option>
                <option value="dynamic">Dynamic response & memory</option>
              </select>
            </label>
            {scenario.diet_response.kind === "dynamic" && (
              <label>
                Response shape
                <select
                  value={scenario.diet_response.shape}
                  onChange={(e) =>
                    onChange({
                      ...request,
                      overrides: {},
                      scenario: {
                        ...scenario,
                        diet_response: {
                          ...scenario.diet_response,
                          shape: e.target.value,
                        },
                      },
                    })
                  }
                >
                  <option value="linear">Linear</option>
                  <option value="saturating">Saturating</option>
                </select>
              </label>
            )}
          </div>
        </section>
        {scenario.glp1 && (
          <section className="form-section">
            <p className="eyebrow">Treatment experiment</p>
            <h2>GLP-1 access & capacity</h2>
            <p>
              These inputs describe a synthetic access scenario. They do not
              estimate insurance savings.
            </p>
            {scenario.glp1.access_schedule.map((step, index) => (
              <fieldset key={index}>
                <legend>Access step {index + 1}</legend>
                <div className="form-grid three">
                  {glpFields.map(({ key, label, percent }) => (
                    <NumberField
                      key={key}
                      label={`${label} · step ${index + 1}`}
                      value={step[key] * (percent ? 100 : 1)}
                      min={key === "start_year" ? 1 : 0}
                      max={
                        percent
                          ? 100
                          : key === "start_year"
                            ? scenario.years
                            : undefined
                      }
                      step={key === "start_year" ? 1 : "any"}
                      onChange={(value) =>
                        update({
                          glp1: {
                            access_schedule: scenario.glp1!.access_schedule.map(
                              (s, i) =>
                                i === index
                                  ? { ...s, [key]: value / (percent ? 100 : 1) }
                                  : s,
                            ),
                          },
                        })
                      }
                    />
                  ))}
                </div>
                <button
                  className="text-button"
                  disabled={scenario.glp1!.access_schedule.length === 1}
                  onClick={() =>
                    update({
                      glp1: {
                        access_schedule: scenario.glp1!.access_schedule.filter(
                          (_, i) => i !== index,
                        ),
                      },
                    })
                  }
                >
                  Remove access step {index + 1}
                </button>
              </fieldset>
            ))}
            <button
              className="secondary"
              onClick={() => {
                const last = scenario.glp1!.access_schedule.at(-1)!;
                update({
                  glp1: {
                    access_schedule: [
                      ...scenario.glp1!.access_schedule,
                      { ...last, start_year: last.start_year + 1 },
                    ],
                  },
                });
              }}
            >
              Add access step
            </button>
          </section>
        )}
        <details className="form-section advanced">
          <summary>
            Advanced assumptions{" "}
            <span className="badge">Synthetic parameters</span>
          </summary>
          <p>
            Change a nominal value, and optionally its existing uniform range.
            Values must remain within that range. The original evidence remains
            unchanged; a saved experiment records your overrides. Fixed
            parameters stay fixed in sampling.
          </p>
          {Object.entries(parameters).map(([key, p]) => {
            const edit = request.overrides[key];
            const set = (patch: Record<string, number>) =>
              onChange({
                ...request,
                overrides: {
                  ...request.overrides,
                  [key]: { ...(edit ?? { value: p.value }), ...patch },
                },
              });
            return (
              <fieldset key={key}>
                <legend>{key.replaceAll("_", " ")}</legend>
                <p className="meta">
                  {p.unit} · {p.status} · grade {p.evidence_grade}
                </p>
                <div className="form-grid three">
                  <NumberField
                    label={`${key}: nominal`}
                    value={edit?.value ?? p.value}
                    onChange={(value) => set({ value })}
                  />
                  {p.uncertainty.kind === "uniform" && (
                    <>
                      <NumberField
                        label={`${key}: low`}
                        value={edit?.low ?? p.uncertainty.low!}
                        onChange={(low) =>
                          set({ low, high: edit?.high ?? p.uncertainty.high! })
                        }
                      />
                      <NumberField
                        label={`${key}: high`}
                        value={edit?.high ?? p.uncertainty.high!}
                        onChange={(high) =>
                          set({ high, low: edit?.low ?? p.uncertainty.low! })
                        }
                      />
                    </>
                  )}
                </div>
                <small>{p.uncertainty.rationale}</small>
                {edit && (
                  <button
                    className="text-button"
                    onClick={() => {
                      const next = { ...request.overrides };
                      delete next[key];
                      onChange({ ...request, overrides: next });
                    }}
                  >
                    Reset {key.replaceAll("_", " ")}
                  </button>
                )}
              </fieldset>
            );
          })}
        </details>
      </div>
      <aside className="run-panel">
        <p className="eyebrow">03 · Predict, then run</p>
        <h2>What do you expect?</h2>
        <label>
          Your prediction
          <textarea
            rows={4}
            maxLength={4000}
            placeholder="I expect… because…"
            value={request.prediction}
            onChange={(e) =>
              onChange({ ...request, prediction: e.target.value })
            }
          />
        </label>
        <label>
          Compare with
          <select
            value={request.reference_id ?? ""}
            onChange={(e) =>
              onChange({ ...request, reference_id: e.target.value || null })
            }
          >
            <option value="">Matched no-intervention reference</option>
            {runs
              .filter((r) => r.status === "complete")
              .map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} · {r.id.slice(0, 6)}
                </option>
              ))}
          </select>
          <small>
            The default reference uses original assumptions, the same population
            and structure, and no dietary or GLP-1 intervention.
          </small>
        </label>
        <label>
          Sampling
          <select
            value={request.profile}
            onChange={(e) => onChange({ ...request, profile: e.target.value })}
          >
            <option value="preview">Preview · 4 draws / 8 Sobol samples</option>
            <option value="standard">
              Standard · 64 draws / 32 Sobol samples
            </option>
          </select>
          <small>
            Preview checks the software. Larger samples do not resolve missing
            scientific evidence.
          </small>
        </label>
        <NumberField
          label="Random seed"
          value={request.seed}
          min={0}
          max={4294967295}
          step={1}
          onChange={(seed) => onChange({ ...request, seed })}
        />
        <button className="primary" onClick={onRun} disabled={busy}>
          {busy ? "Calculation in progress…" : "Run experiment →"}
        </button>
        <button className="secondary" onClick={onValidate} disabled={busy}>
          Check assumptions
        </button>
        <p className="meta">
          Results and assumptions are saved on this computer. You can cancel a
          running calculation.
        </p>
      </aside>
    </div>
  );
}
