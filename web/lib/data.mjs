/** Plotted rows, not recomputed model outcomes. Includes heatmap cells. */
export function chartRows(figure) {
  const rows = [];
  for (const [index, trace] of figure.data.entries()) {
    const series = trace.name || `Series ${index + 1}`;
    if (Array.isArray(trace.z)) {
      trace.z.forEach((line, yi) =>
        line.forEach((value, xi) =>
          rows.push({
            series,
            x: trace.x?.[xi] ?? xi,
            y: trace.y?.[yi] ?? yi,
            value,
          }),
        ),
      );
    } else {
      const count = Math.max(trace.x?.length || 0, trace.y?.length || 0);
      for (let i = 0; i < count; i++)
        rows.push({
          series,
          x: trace.x?.[i] ?? i,
          y: trace.y?.[i] ?? null,
          value: trace.text?.[i] ?? null,
        });
    }
  }
  return rows;
}
export function csv(rows) {
  const cell = (value) => {
    let text =
      value == null
        ? ""
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);
    if (typeof value === "string" && /^[=+@\-\t\r]/.test(text))
      text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  };
  return [
    "series,x,y,value",
    ...rows.map((row) =>
      [row.series, row.x, row.y, row.value].map(cell).join(","),
    ),
  ].join("\r\n");
}
export function format(value) {
  if (value == null) return "Not defined";
  if (typeof value !== "number") return String(value);
  return value.toLocaleString("en-US", {
    maximumFractionDigits: Math.abs(value) < 1 ? 5 : 3,
  });
}
export function experimentSignature(request) {
  return JSON.stringify([
    request.catalog_id,
    request.scenario,
    request.overrides,
    request.profile,
    request.seed,
    request.reference_id,
  ]);
}
