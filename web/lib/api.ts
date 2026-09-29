export async function api<T>(
  token: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "X-Demeter-Token": token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const value = await response.json();
  if (!response.ok) {
    const detail = value.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail
            .map(
              (e) =>
                `${e.field ?? e.loc?.join(".") ?? "Input"}: ${e.message ?? e.msg}`,
            )
            .join("\n")
        : String(detail ?? "Request failed"),
    );
  }
  return value;
}
export function downloadBlob(blob: Blob, name: string) {
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function download(token: string, id: string, artifact: string) {
  const response = await fetch(`/api/runs/${id}/download/${artifact}`, {
    headers: { "X-Demeter-Token": token },
  });
  if (!response.ok)
    throw new Error("Export is unavailable until the run completes");
  const name =
    response.headers
      .get("content-disposition")
      ?.match(/filename="?([^";]+)/)?.[1] ?? artifact;
  downloadBlob(await response.blob(), name);
}
