import type { Parameter } from "../lib/types";

export function SafeSource({ source }: { source: Parameter }) {
  return (
    <article className="source">
      <strong>{source.key.replaceAll("_", " ")}</strong>
      <div className="meta">
        {source.status} · grade {source.evidence_grade} · {source.unit}
      </div>
      <p>{source.citation || source.source}</p>
      {source.source_url && /^https?:\/\//.test(source.source_url) && (
        <a href={source.source_url} target="_blank" rel="noreferrer">
          Read source ↗
        </a>
      )}
    </article>
  );
}
