"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Controls from "../components/Controls";
import { SafeSource } from "../components/SafeSource";
import { api, download } from "../lib/api";
import { experimentSignature, format } from "../lib/data.mjs";
import type {
  Entry,
  Experiment,
  Parameter,
  Receipt,
  Result,
} from "../lib/types";

const ChartView = dynamic(() => import("../components/ChartView"), {
  ssr: false,
  loading: () => <p>Preparing chart…</p>,
});
const sections = ["Learn", "Explore", "Experiment", "Saved runs", "Sources"];
const lessons = [
  {
    chart: "stocks",
    number: "01",
    title: "Follow the people",
    text: "Stocks, flows, and the changing population.",
  },
  {
    chart: "dependencies",
    number: "02",
    title: "Trace the mechanism",
    text: "Connect an assumption to its effects.",
  },
  {
    chart: "uncertainty_life_expectancy",
    number: "03",
    title: "Read the uncertainty",
    text: "Understand what a shaded band includes.",
  },
  {
    chart: "sensitivity",
    number: "04",
    title: "Challenge the result",
    text: "Find the assumptions that matter.",
  },
];
const future = [
  {
    title: "Agriculture & regenerative practices",
    text: "Trace a specified practice through yield, cost, soil, and adoption. Requires appraised local relationships.",
    path: "docs/design/02_CAUSAL_LOOPS.md",
  },
  {
    title: "Retail & value capture",
    text: "Follow prices, demand, margins, and contracts. A premium is not automatically producer income.",
    path: "docs/REAL_FOOD_VALUE_CHAIN.md",
  },
  {
    title: "Healthcare costs & externalities",
    text: "Connect physical outcomes to resource costs, affected parties, and payment rules. Health gains alone do not establish savings.",
    path: "docs/design/03_EXTERNALITIES.md",
  },
];
const initial = (entry: Entry): Experiment => ({
  catalog_id: entry.id,
  scenario: structuredClone(entry.scenario),
  overrides: {},
  profile: "preview",
  seed: 42,
  reference_id: null,
  prediction: "",
  notes: "",
});

export default function Page() {
  const [token, setToken] = useState("");
  const [tab, setTab] = useState("Learn");
  const [entries, setEntries] = useState<Entry[]>([]);
  const [request, setRequest] = useState<Experiment | null>(null);
  const [parameters, setParameters] = useState<Record<string, Parameter>>({});
  const [sources, setSources] = useState<Parameter[]>([]);
  const [bounds, setBounds] = useState([0.5, 1.5]);
  const [runs, setRuns] = useState<Receipt[]>([]);
  const [selected, setSelected] = useState("");
  const [selectionRevision, setSelectionRevision] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [chartId, setChartId] = useState("stocks");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notes, setNotes] = useState("");
  const [filter, setFilter] = useState("");
  const active = runs.find((r) => ["queued", "running"].includes(r.status));
  const dirty = !!(
    request &&
    result &&
    experimentSignature(request) !== experimentSignature(result.request)
  );

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const launchToken =
      fragment.get("token") || sessionStorage.getItem("demeter-token") || "";
    if (fragment.has("token")) {
      sessionStorage.setItem("demeter-token", launchToken);
      history.replaceState(null, "", window.location.pathname);
    }
    setToken(launchToken);
    if (!launchToken)
      setError(
        "Start the interface with uv run --extra studio demeter explore, then open the browser link printed in that terminal.",
      );
  }, []);
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    api<{ scenarios: Entry[] }>(token, "catalog")
      .then((data) => {
        if (cancelled) return;
        setEntries(data.scenarios);
        const first =
          data.scenarios.find(
            (e) => e.id === "demeter.core@1.0.0/reduce_upf_30",
          ) || data.scenarios[0];
        setRequest(initial(first));
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);
  const shape = request
    ? `${request.scenario.health_structure}:${request.scenario.diet_response.kind}:${request.scenario.diet_response.shape}:${!!request.scenario.glp1}`
    : "";
  useEffect(() => {
    if (!token || !request) return;
    let cancelled = false;
    api<{
      editable: Record<string, Parameter>;
      sources: Parameter[];
      exposure_bounds: number[];
    }>(token, "parameters", request.scenario)
      .then((data) => {
        if (!cancelled) {
          setParameters(data.editable);
          setSources(data.sources);
          setBounds(data.exposure_bounds);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
    // Shape selects active parameters; numeric edits do not require a metadata request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, shape]);
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    let inFlight = false;
    let fetchedStatus = "";
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const list = await api<Receipt[]>(token, "runs");
        if (cancelled) return;
        setRuns(list);
        const current = list.find((r) => r.id === selected);
        if (current && current.status !== fetchedStatus) {
          const data = await api<Result>(token, `runs/${selected}`);
          if (cancelled) return;
          setResult(data);
          fetchedStatus = data.receipt.status;
          setNotes(data.notes ?? data.request.notes);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        inFlight = false;
      }
    };
    refresh();
    const interval = setInterval(refresh, 1500);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [token, selected, selectionRevision]);

  async function act(action: () => Promise<void>) {
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function choose(id: string) {
    setResult(null);
    setSelected(id);
    setSelectionRevision((value) => value + 1);
    setTab("Explore");
    setChartId("stocks");
  }
  function preset(id: string) {
    const entry = entries.find((e) => e.id === id)!;
    setRequest(initial(entry));
    setNotice("");
    setError("");
  }
  async function run() {
    if (!request) return;
    setSubmitting(true);
    await act(async () => {
      const receipt = await api<Receipt>(token, "runs", request);
      setRuns((list) => [receipt, ...list]);
      choose(receipt.id);
    });
    setSubmitting(false);
  }
  const currentChart =
    result?.charts?.find((c) => c.id === chartId) ?? result?.charts?.[0];
  const referenceChart = result?.reference?.charts.find(
    (c) => c.id === currentChart?.id,
  );
  const evidence = result?.sources
    ? Object.values(result.sources).filter(
        (p) => p.source_url || p.status === "synthetic",
      )
    : sources;
  const exportFile = (artifact: string) =>
    act(() => download(token, selected, artifact));

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="header-inner">
          <button
            className="brand"
            onClick={() => setTab("Learn")}
            aria-label="Demeter home"
          >
            <span className="brand-mark">D</span>
            <span>
              DEMETER<small>Food. Health. Consequences.</small>
            </span>
          </button>
          <nav aria-label="Main navigation">
            {sections.map((section) => (
              <button
                key={section}
                aria-current={tab === section ? "page" : undefined}
                onClick={() => setTab(section)}
              >
                {section}
              </button>
            ))}
          </nav>
          <span className="local-status">
            <i />
            Local learning preview
          </span>
        </div>
      </header>
      <main id="main">
        <div className="science-strip">
          <span className="status-dot" />
          Validation-only model experiments <span className="divider">/</span>
          <span>
            Understand assumptions. Do not interpret these runs as scientific
            findings.
          </span>
        </div>
        {error && (
          <div role="alert" className="alert">
            <strong>Check before continuing</strong>
            <p>{error}</p>
            <button className="text-button" onClick={() => setError("")}>
              Dismiss
            </button>
          </div>
        )}
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
        {active && (
          <div className="running" role="status">
            <span className="spinner" />
            <div>
              <strong>{active.name}</strong>
              <span>{active.stage}</span>
            </div>
            <button
              className="secondary"
              onClick={() =>
                act(async () => {
                  await api(token, `runs/${active.id}/cancel`, {});
                  setNotice(
                    "Calculation cancelled. Your other saved results are unchanged.",
                  );
                })
              }
            >
              Cancel calculation
            </button>
          </div>
        )}

        {tab === "Learn" && (
          <>
            <section className="hero">
              <div>
                <p className="eyebrow">
                  A learning laboratory for connected systems
                </p>
                <h1>
                  Change an assumption.
                  <br />
                  <em>Follow the consequences.</em>
                </h1>
                <p className="lede">
                  Explore how food, metabolic health, and time connect. Predict
                  what will happen, run an experiment, and discover which
                  assumptions shape the answer.
                </p>
                <div className="actions">
                  <button
                    className="primary"
                    disabled={!request || !!active || submitting}
                    onClick={run}
                  >
                    Run this experiment →
                  </button>
                  <button
                    className="text-button"
                    onClick={() => setTab("Experiment")}
                  >
                    Choose your assumptions
                  </button>
                </div>
                <p className="meta">
                  Current: {request?.scenario.name ?? "Loading"} ·{" "}
                  {request?.profile ?? "Preview"} sampling · Runs are saved
                  locally
                </p>
              </div>
              <div className="system-card">
                <p className="eyebrow">The first part of a larger system</p>
                <div className="system-node">
                  Food exposure <span>Your scenario choice</span>
                </div>
                <div className="system-arrow">
                  ↓ <small>response & delay</small>
                </div>
                <div className="system-node">
                  Metabolic states <span>Stocks, progression & recovery</span>
                </div>
                <div className="system-arrow">
                  ↓ <small>age-specific mortality</small>
                </div>
                <div className="system-node">
                  Longevity measures <span>Calculated from the model</span>
                </div>
                <p>
                  Each link needs evidence.
                  <br />
                  Today’s intervention effects remain synthetic.
                </p>
              </div>
            </section>
            <section className="learning-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Learn to read the system</p>
                  <h2>Four questions to ask of every run</h2>
                </div>
                <span className="meta">Predict → Run → Compare → Explain</span>
              </div>
              <div className="lesson-grid">
                {lessons.map((lesson) => (
                  <button
                    className="lesson"
                    key={lesson.number}
                    onClick={() => {
                      setChartId(lesson.chart);
                      if (result?.charts) setTab("Explore");
                      else {
                        setTab("Experiment");
                        setNotice(
                          "Run an experiment to explore this lesson with your own results.",
                        );
                      }
                    }}
                  >
                    <span>{lesson.number}</span>
                    <h3>{lesson.title}</h3>
                    <p>{lesson.text}</p>
                    <b>Explore →</b>
                  </button>
                ))}
              </div>
            </section>
            <section className="future-section">
              <p className="eyebrow">Where the model is going</p>
              <h2>A shared view across the value chain</h2>
              <p>
                Future modules will connect these health experiments to who
                creates value, who captures it, and who bears the costs. Their
                mechanisms are design premises awaiting evidence and
                implementation.
              </p>
              <div className="future-grid">
                {future.map((item) => (
                  <article key={item.title}>
                    <span className="badge planned">Planned</span>
                    <h3>{item.title}</h3>
                    <p>{item.text}</p>
                    <a
                      href={`https://github.com/Crusonia/Demeter/blob/main/${item.path}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Read the design →
                    </a>
                  </article>
                ))}
              </div>
            </section>
          </>
        )}

        {tab === "Experiment" && request && (
          <Controls
            request={request}
            entries={entries}
            parameters={parameters}
            runs={runs}
            bounds={bounds}
            onChange={(r) => {
              setRequest(r);
              setNotice("");
            }}
            onPreset={preset}
            onRun={run}
            onValidate={() =>
              act(async () => {
                await api(token, "validate", request);
                setNotice(
                  "Assumptions are valid for a software experiment. This does not establish scientific validity.",
                );
              })
            }
            busy={submitting || !!active}
          />
        )}
        {tab === "Experiment" && !request && (
          <p role="status">Loading the reviewed model catalog…</p>
        )}

        {tab === "Explore" && (
          <>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Understand a completed experiment</p>
                <h1 className="page-title">Follow the result</h1>
              </div>
              <label className="run-picker">
                Saved experiment
                <select
                  value={selected}
                  onChange={(e) => choose(e.target.value)}
                >
                  <option value="">Select a run</option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} · {r.status} · {r.id.slice(0, 6)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {!selected && (
              <div className="empty">
                <h2>Your next insight starts with a question.</h2>
                <p>
                  Choose a saved run above, or create an experiment to see
                  charts and explanations here.
                </p>
                <button
                  className="primary"
                  onClick={() => setTab("Experiment")}
                >
                  Set up an experiment →
                </button>
              </div>
            )}
            {selected && !result && <p role="status">Loading saved results…</p>}
            {result && result.receipt.status !== "complete" && (
              <div className="empty">
                <h2>{result.receipt.stage}</h2>
                <p>
                  {result.receipt.error ??
                    "Only completed calculations are shown as results. You can explore other saved runs while a calculation is active."}
                </p>
                <button
                  className="secondary"
                  onClick={() => {
                    setRequest(result.request);
                    setTab("Experiment");
                  }}
                >
                  Review these assumptions
                </button>
              </div>
            )}
            {result?.charts && (
              <>
                {dirty && (
                  <div className="notice">
                    Your editor has different assumptions. These charts still
                    show <strong>{result.receipt.name}</strong>.{" "}
                    <button
                      className="text-button"
                      onClick={() => setTab("Experiment")}
                    >
                      Review and rerun →
                    </button>
                  </div>
                )}
                <div className="result-intro">
                  <p className="eyebrow">What this run shows</p>
                  {result.summary?.map((text) => (
                    <p key={text}>{text}</p>
                  ))}
                  <div className="actions">
                    <button
                      className="secondary"
                      onClick={() => {
                        setRequest(structuredClone(result.request));
                        setTab("Experiment");
                      }}
                    >
                      Use these assumptions
                    </button>
                    <button
                      className="text-button"
                      onClick={() => exportFile("report")}
                    >
                      ↓ Offline report
                    </button>
                    <button
                      className="text-button"
                      onClick={() => exportFile("scenario")}
                    >
                      ↓ Scenario YAML
                    </button>
                    <button
                      className="text-button"
                      onClick={() => exportFile("diagnostics")}
                    >
                      ↓ Full diagnostics
                    </button>
                  </div>
                </div>
                <label className="chart-picker">
                  Question / chart
                  <select
                    value={currentChart?.id}
                    onChange={(e) => setChartId(e.target.value)}
                  >
                    {result.charts.map((c) => (
                      <option value={c.id} key={c.id}>
                        {c.id.replaceAll("_", " ")} — {c.guide.question}
                      </option>
                    ))}
                  </select>
                </label>
                {currentChart && (
                  <ChartView
                    chart={currentChart}
                    reference={referenceChart}
                    sources={evidence}
                    scenarioName={result.receipt.name}
                    onExperiment={() => setTab("Experiment")}
                  />
                )}
                {result.comparison && (
                  <section className="comparison">
                    <p className="eyebrow">Compare with the frozen reference</p>
                    <h2>What changed—and what did you change?</h2>
                    <p>
                      Reference:{" "}
                      <strong>{result.comparison.reference_label}</strong>.
                      Outcomes at model year {result.comparison.year}.
                    </p>
                    <p>{result.comparison.interval_note}</p>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Outcome</th>
                            <th>Reference</th>
                            <th>Experiment</th>
                            <th>Absolute change</th>
                            <th>Relative change</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.comparison.outcomes.map((row) => (
                            <tr key={row.metric}>
                              <th>
                                {row.metric.replaceAll("_", " ")}{" "}
                                <span className="meta">({row.unit})</span>
                              </th>
                              <td>{format(row.reference)}</td>
                              <td>{format(row.experiment)}</td>
                              <td>{format(row.absolute_delta)}</td>
                              <td>
                                {row.relative_delta === null
                                  ? "Not defined"
                                  : `${format(row.relative_delta * 100)}%`}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <details>
                      <summary>
                        See the exact assumptions diff (
                        {result.comparison.assumptions.length})
                      </summary>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Assumption</th>
                              <th>Reference</th>
                              <th>Experiment</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.comparison.assumptions.map((row) => (
                              <tr key={row.field}>
                                <th>{row.field}</th>
                                <td>
                                  <code>{JSON.stringify(row.reference)}</code>
                                </td>
                                <td>
                                  <code>{JSON.stringify(row.experiment)}</code>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </details>
                  </section>
                )}
                <section className="reflection">
                  <p className="eyebrow">Close the learning loop</p>
                  <h2>Did the result match your prediction?</h2>
                  <blockquote>
                    {result.request.prediction ||
                      "No prediction was recorded for this run."}
                  </blockquote>
                  <label>
                    Your explanation & next question
                    <textarea
                      rows={4}
                      value={notes}
                      maxLength={4000}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="What surprised you? Which evidence would change your interpretation?"
                    />
                  </label>
                  <button
                    className="secondary"
                    onClick={() =>
                      act(async () => {
                        await api(token, `runs/${selected}/notes`, {
                          text: notes,
                        });
                        setNotice(
                          "Reflection saved alongside this experiment.",
                        );
                      })
                    }
                  >
                    Save reflection
                  </button>
                  <details>
                    <summary>Reproducibility record</summary>
                    <p>
                      Seed {result.request.seed} · {result.request.profile}{" "}
                      sampling · {result.receipt.created_at}
                    </p>
                    <p className="hash">
                      Evidence: {result.receipt.resolved_evidence_sha256}
                      <br />
                      Code: {result.receipt.code}
                      <br />
                      Commentary: {result.receipt.commentary_sha256}
                    </p>
                    <div className="actions">
                      <button
                        className="text-button"
                        onClick={() => exportFile("request")}
                      >
                        Download all assumptions
                      </button>
                      <button
                        className="text-button"
                        onClick={() => exportFile("evidence")}
                      >
                        Download resolved evidence
                      </button>
                      <button
                        className="text-button"
                        onClick={() => exportFile("comparison")}
                      >
                        Download comparison
                      </button>
                    </div>
                  </details>
                </section>
              </>
            )}
          </>
        )}

        {tab === "Saved runs" && (
          <>
            <p className="eyebrow">Your local notebook</p>
            <h1 className="page-title">Every experiment leaves a trail.</h1>
            <p>
              Reopen a completed run, use it as a reference, or return to its
              assumptions. Failed and cancelled attempts remain visible.
            </p>
            {runs.length === 0 && (
              <div className="empty">
                <h2>No experiments yet</h2>
                <button
                  className="primary"
                  onClick={() => setTab("Experiment")}
                >
                  Create your first experiment
                </button>
              </div>
            )}
            <div className="saved-grid">
              {runs.map((run) => (
                <button
                  key={run.id}
                  className="saved-card"
                  onClick={() => choose(run.id)}
                >
                  <span
                    className={`badge ${run.status === "complete" ? "observed" : ""}`}
                  >
                    {run.status}
                  </span>
                  <h2>{run.name}</h2>
                  <p>{run.stage}</p>
                  <small>
                    {new Date(run.created_at).toLocaleString()} · {run.profile}
                  </small>
                  <b>Open experiment →</b>
                </button>
              ))}
            </div>
          </>
        )}
        {tab === "Sources" && (
          <>
            <p className="eyebrow">Evidence belongs beside the chart</p>
            <h1 className="page-title">Know what supports the model.</h1>
            <p>
              Observed inputs, benchmark studies, and synthetic mechanisms have
              different roles. These are the current registry’s sourced records;
              each saved run retains its own evidence snapshot.
            </p>
            <label className="search">
              Find a source or parameter
              <input
                type="search"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Try mortality, UPF, or NHANES"
              />
            </label>
            <div className="sources-grid">
              {sources
                .filter((p) =>
                  `${p.key} ${p.citation} ${p.source}`
                    .toLowerCase()
                    .includes(filter.toLowerCase()),
                )
                .map((p) => (
                  <SafeSource source={p} key={p.key} />
                ))}
            </div>
          </>
        )}
      </main>
      <footer>
        <strong>Demeter</strong>
        <span>A community model, built one testable mechanism at a time.</span>
        <a
          href="https://github.com/Crusonia/Demeter"
          target="_blank"
          rel="noreferrer"
        >
          Code, evidence & contribution guide ↗
        </a>
      </footer>
    </>
  );
}
