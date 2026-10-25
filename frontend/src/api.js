async function request(path, options) {
  const started = performance.now();
  const response = await fetch(path, options);

  if (!response.ok) {
    throw new Error(`${path} failed with status ${response.status}`);
  }

  const data = await response.json();
  return { ...data, roundTripMs: Math.round(performance.now() - started) };
}

function postJson(path, body) {
  return request(path, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

export function startVisit() {
  return postJson("/api/visits");
}

export function sendEvent(sessionId, event) {
  return postJson("/api/events", { sessionId, ...event });
}

// sessionId is optional: the resume still downloads if the visit never registered.
export function requestResume(sessionId) {
  return postJson("/api/resume", sessionId ? { sessionId } : undefined);
}

export function getStats() {
  return request("/api/stats");
}

// Every row the backend stored about this visit, exactly as DynamoDB holds them.
export function getStoredData(sessionId) {
  return request(`/api/sessions/${sessionId}`);
}

export function deleteStoredData(sessionId) {
  return request(`/api/sessions/${sessionId}`, { method: "DELETE" });
}
