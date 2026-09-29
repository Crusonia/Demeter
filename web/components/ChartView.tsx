"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Script from "next/script";
import type { Chart, Figure } from "../lib/types";
import { chartRows, csv, format } from "../lib/data.mjs";
import { downloadBlob } from "../lib/api";
import EvidencePanel from "./EvidencePanel";

declare global {
  interface Window {
    Plotly: {
      react: (
        node: HTMLElement,
        data: Figure["data"],
        layout: object,
        config: object,
      ) => Promise<void>;
      purge: (node: HTMLElement) => void;
      downloadImage: (node: HTMLElement, options: object) => void;
    };
  }
}
export default function ChartView({
  chart,
  reference,
  scenarioName,
  onExperiment,
}: {
  chart: Chart;
  reference?: Chart;
  scenarioName: string;
  onExperiment: () => void;
}) {
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState("Chart");
  const [showReference, setShowReference] = useState(false);
  const [plotError, setPlotError] = useState("");
  const node = useRef<HTMLDivElement>(null);
  const rows = useMemo(() => chartRows(chart.figure), [chart]);
  const canOverlay = ["stocks", "flows"].includes(chart.id);
  const isBenchmark =
    chart.id.startsWith("history_") ||
    ["glp1_trial_benchmarks", "diet_lag_challenge"].includes(chart.id);
  useEffect(() => {
    if (window.Plotly) setReady(true);
  }, []);
  useEffect(() => {
    setShowReference(false);
    setTab("Chart");
  }, [chart.id]);
  useEffect(() => {
    const target = node.current;
    if (!ready || !target || tab !== "Chart") return;
    const figure = structuredClone(chart.figure);
    // Stacked stocks cannot be overlaid safely. Compare totals as individual
    // lines when reference mode is selected, leaving the canonical export intact.
    if (showReference && reference && canOverlay) {
      figure.data = figure.data.map((t) => ({
        ...t,
        stackgroup: undefined,
        fill: "none",
      }));
      figure.data.push(
        ...structuredClone(reference.figure.data).map((t) => ({
          ...t,
          stackgroup: undefined,
          fill: "none",
          name: `Reference · ${t.name}`,
          line: {
            ...(typeof t.line === "object" && !Array.isArray(t.line)
              ? t.line
              : {}),
            dash: "dot",
            width: 2,
          },
          opacity: 0.65,
        })),
      );
    }
    const layout = {
      ...figure.layout,
      title: figure.layout.title,
      autosize: true,
      width: undefined,
      height: 450,
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: { family: "Arial, sans-serif", size: 13, color: "#263d40" },
      margin: { l: 60, r: 25, t: 70, b: 95 },
    };
    // Plotly does not wrap titles automatically on narrow screens. Keep the
    // complete measure and validation label visible, including in PNG exports.
    const title = figure.layout.title;
    const titleText =
      typeof title === "string"
        ? title
        : title && typeof title === "object" && !Array.isArray(title)
          ? String(title.text ?? "")
          : "";
    const titleLines: string[] = [];
    for (const word of titleText.split(/\s+/)) {
      const last = titleLines.length - 1;
      if (last < 0 || titleLines[last].length + word.length + 1 > 36)
        titleLines.push(word);
      else titleLines[last] += ` ${word}`;
    }
    layout.title = {
      text: titleLines.join("<br>"),
      font: { size: 14 },
      x: 0.03,
      xanchor: "left",
    };
    layout.margin.t = 24 + titleLines.length * 20;
    window.Plotly.react(target, figure.data, layout, {
      responsive: true,
      displaylogo: false,
      toImageButtonOptions: { filename: `demeter-${chart.id}` },
    }).catch((error) => setPlotError(String(error)));
    const resize = new ResizeObserver(() => {
      window.dispatchEvent(new Event("resize"));
    });
    resize.observe(target);
    return () => {
      resize.disconnect();
      window.Plotly.purge(target);
    };
  }, [chart, reference, ready, tab, showReference, canOverlay]);
  return (
    <section className="chart-story" aria-label={chart.guide.question}>
      <Script
        src="/plotly.min.js"
        strategy="afterInteractive"
        onReady={() => setReady(true)}
        onError={() =>
          setPlotError(
            "Chart library did not load. Restart the local interface.",
          )
        }
      />
      <div className="chart-heading">
        <div>
          <p className="eyebrow">Explore the mechanism</p>
          <h2>{chart.guide.question}</h2>
          <p className="meta">
            {scenarioName} · Complete run · Full plotted time range
          </p>
        </div>
        <span className={isBenchmark ? "badge observed" : "badge"}>
          {isBenchmark ? "Historical benchmark" : "Model experiment"}
        </span>
      </div>
      <div className="story-grid">
        <div className="chart-pane">
          <div className="chart-toolbar">
            <div className="tabs" role="group" aria-label="Chart views">
              {["Chart", "Data", "Sources"].map((value) => (
                <button
                  aria-pressed={tab === value}
                  key={value}
                  onClick={() => setTab(value)}
                >
                  {value}
                </button>
              ))}
            </div>
            <button
              className="text-button"
              onClick={() =>
                downloadBlob(
                  new Blob([csv(rows)], { type: "text/csv;charset=utf-8" }),
                  `${chart.id}.csv`,
                )
              }
            >
              ↓ CSV
            </button>
            <button
              className="text-button"
              onClick={() =>
                downloadBlob(
                  new Blob([JSON.stringify(chart.figure, null, 2)], {
                    type: "application/json",
                  }),
                  `${chart.id}.plotly.json`,
                )
              }
            >
              ↓ JSON
            </button>
          </div>
          {tab === "Chart" && (
            <>
              <div
                className="plot"
                ref={node}
                aria-label={`Interactive chart: ${chart.id}`}
              />
              {!ready && <p role="status">Loading local chart library…</p>}
              {plotError && <p role="alert">{plotError}</p>}
              {canOverlay && reference && (
                <label className="check">
                  <input
                    type="checkbox"
                    checked={showReference}
                    onChange={(e) => setShowReference(e.target.checked)}
                  />
                  Compare reference as dotted lines{" "}
                  {chart.id === "stocks" && "(unstacked)"}
                </label>
              )}
              <p className="chart-footnote">
                Hover for values. Use the chart toolbar to zoom or download a
                PNG. Commentary describes the full run; zooming does not rerun
                the model.
              </p>
            </>
          )}
          {tab === "Data" && (
            <div className="data-table">
              <p className="meta">
                {rows.length.toLocaleString()} plotted rows. Showing the first
                150; CSV contains all rows. Units are shown on the chart axes.
              </p>
              <table>
                <thead>
                  <tr>
                    <th>Series</th>
                    <th>X</th>
                    <th>Y</th>
                    <th>Cell / label</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 150).map((r, i) => (
                    <tr key={i}>
                      <td>{String(r.series)}</td>
                      <td>{format(r.x)}</td>
                      <td>{format(r.y)}</td>
                      <td>{format(r.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {tab === "Sources" && (
            <>
              <p>Evidence below is frozen with the experiment.</p>
              <EvidencePanel
                key={`${chart.id}-experiment`}
                evidence={chart.evidence}
              />
              {canOverlay && reference && (
                <details>
                  <summary>Evidence for the frozen reference</summary>
                  <EvidencePanel
                    key={`${reference.id}-reference`}
                    evidence={reference.evidence}
                  />
                </details>
              )}
            </>
          )}
        </div>
        <aside className="commentary">
          <h3>How to read this</h3>
          <p>
            {showReference && chart.id === "stocks"
              ? "Each line counts people in one health state. Dotted lines show the reference. This comparison is unstacked: add the state values to obtain total living population."
              : chart.guide.read}
          </p>
          <h3>Why it happens</h3>
          <p>{chart.guide.mechanism}</p>
          <div className="try-box">
            <span className="eyebrow">Try it yourself</span>
            <p>{chart.guide.try}</p>
            <button className="text-button" onClick={onExperiment}>
              Change an assumption →
            </button>
          </div>
          {chart.guide.predict && (
            <details className="learning-exercise">
              <summary>Test your explanation</summary>
              <h3>Predict before running</h3>
              <p>{chart.guide.predict}</p>
              <h3>Challenge an assumption</h3>
              <p>{chart.guide.challenge}</p>
              <h3>What evidence would change your interpretation?</h3>
              <p>{chart.guide.evidence}</p>
              <p>
                Record your prediction in Experiment and your explanation below
                the results.
              </p>
            </details>
          )}
          <details>
            <summary>What this cannot establish</summary>
            <p>{chart.guide.limit}</p>
          </details>
        </aside>
      </div>
    </section>
  );
}
