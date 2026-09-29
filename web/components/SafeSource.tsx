import type { Parameter } from "../lib/types";

export function SafeSource({ source }: { source: Parameter }) {
  return (
    <article className="source">
      <strong>{source.key.replaceAll("_", " ")}</strong>
      <div className="meta">
        {source.unresolved ? "Unresolved" : source.status} · grade{" "}
        {source.evidence_grade} · {source.unit}
      </div>
      {source.status === "synthetic" && (
        <p>Software assumption; not an observed effect.</p>
      )}
      {source.status === "estimated" && (
        <p>
          Estimated relationship; the study design determines whether a causal
          interpretation is supported.
        </p>
      )}
      <p>{source.citation || source.source}</p>
      <dl className="evidence-fields">
        <dt>Saved value</dt>
        <dd>{source.value ?? "Unresolved"}</dd>
        <dt>Population</dt>
        <dd>{source.population || "Not recorded"}</dd>
        <dt>Geography</dt>
        <dd>{source.geography || "Not recorded"}</dd>
        <dt>Period</dt>
        <dd>{source.time_period || "Not recorded"}</dd>
        <dt>Uncertainty</dt>
        <dd>
          {source.uncertainty
            ? [
                source.uncertainty.kind,
                source.uncertainty.low,
                source.uncertainty.high,
                source.uncertainty.rationale,
              ]
                .filter((v) => v != null)
                .join(" · ")
            : "Not recorded"}
        </dd>
        <dt>Applicability</dt>
        <dd>
          {source.notes ||
            "Not recorded; a citation does not establish transport to this scenario."}
        </dd>
      </dl>
      {source.source_url && /^https?:\/\//.test(source.source_url) && (
        <a href={source.source_url} target="_blank" rel="noreferrer">
          Read source ↗
        </a>
      )}
      <details>
        <summary>Full saved record</summary>
        <pre>{JSON.stringify(source, null, 2)}</pre>
      </details>
    </article>
  );
}
