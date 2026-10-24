export async function startVisit() {
  const started = performance.now();
  const response = await fetch("/api/visits", { method: "POST" });

  if (!response.ok) {
    throw new Error(`Visit request failed with status ${response.status}`);
  }

  const data = await response.json();
  return { ...data, roundTripMs: Math.round(performance.now() - started) };
}
