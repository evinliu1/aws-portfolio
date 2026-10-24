export function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export function secondsSince(timestampMs) {
  return Math.floor((Date.now() - timestampMs) / 1000);
}
