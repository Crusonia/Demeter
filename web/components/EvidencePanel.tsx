"use client";
import { useState } from "react";
import type { ChartEvidence, Json } from "../lib/types";
import { SafeSource } from "./SafeSource";

const text = (value: Json | undefined): string =>
  value == null
    ? "Not recorded"
    : typeof value === "string"
      ? value
      : JSON.stringify(value);

export default function EvidencePanel({
  evidence,
}: {
  evidence?: ChartEvidence;
}) {
  const [selected, setSelected] = useState("");
  if (!evidence)
    return (
      <p>
        Chart-specific evidence was not saved with this older run. Download its
        original diagnostics or create a new run to capture evidence navigation.
      </p>
    );
  const mechanism = evidence.mechanisms.find((m) => m.id === selected);
  const parameters = mechanism
    ? evidence.parameters.filter((p) => mechanism.parameters.includes(p.key))
    : evidence.parameters;
  return (
    <div className="source-list">
      <h3>{evidence.scope}</h3>
      <p>{evidence.note}</p>
      {evidence.mechanisms.length > 0 && (
        <label>
          Evidence for a mechanism
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">All active inputs for this chart</option>
            {evidence.mechanisms.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      )}
      {mechanism && <p className="notice">{mechanism.note}</p>}
      {!mechanism && evidence.sampled_parameters.length > 0 && (
        <details>
          <summary>Which inputs were sampled?</summary>
          <p>{evidence.sampled_parameters.join(", ")}</p>
          <p>
            Registered sampling ranges describe this experiment. They are not
            automatically empirical confidence intervals.
          </p>
        </details>
      )}
      {parameters.map((p) => (
        <SafeSource key={p.key} source={p} />
      ))}
      {!mechanism &&
        evidence.sources.map(({ key, record }) => {
          const receipt = record.receipt;
          const receiptUrl =
            receipt && typeof receipt === "object" && !Array.isArray(receipt)
              ? receipt.url
              : null;
          const url = record.source_url || record.url || receiptUrl;
          return (
            <article className="source" key={key}>
              <h4>{text(record.label || record.title || key)}</h4>
              <dl className="evidence-fields">
                {(
                  [
                    "status",
                    "unit",
                    "population",
                    "geography",
                    "time_period",
                    "uncertainty",
                    "limitations",
                  ] as const
                ).map((field) => (
                  <div key={field}>
                    <dt>{field.replaceAll("_", " ")}</dt>
                    <dd>{text(record[field])}</dd>
                  </div>
                ))}
              </dl>
              {typeof url === "string" && /^https?:\/\//.test(url) && (
                <a href={url} target="_blank" rel="noreferrer">
                  Read source ↗
                </a>
              )}
              <details>
                <summary>Full saved record and source receipt</summary>
                <pre>{JSON.stringify(record, null, 2)}</pre>
              </details>
            </article>
          );
        })}
      {mechanism && (
        <p>
          Choose “All active inputs for this chart” to see background source
          data and the other dependencies.
        </p>
      )}
      <details>
        <summary>Unresolved evidence and limits</summary>
        <ul>
          {[...evidence.unresolved, ...evidence.limitations].map((v, i) => (
            <li key={i}>{v}</li>
          ))}
        </ul>
      </details>
      <details>
        <summary>Saved evidence identity</summary>
        <code>{evidence.evidence_sha256}</code>
      </details>
    </div>
  );
}
