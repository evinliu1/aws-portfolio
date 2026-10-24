async function postJson(path, body) {
  const started = performance.now();
  const response = await fetch(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(`${path} failed with status ${response.status}`);
  }

  const data = await response.json();
  return { ...data, roundTripMs: Math.round(performance.now() - started) };
}

export function startVisit() {
  return postJson("/api/visits");
}

export function sendEvent(sessionId, event) {
  return postJson("/api/events", { sessionId, ...event });
}
