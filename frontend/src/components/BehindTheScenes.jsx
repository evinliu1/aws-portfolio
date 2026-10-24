import { useEffect, useState } from "react";
import { CLICK_LABELS } from "../lib/clickTargets";
import { formatDuration, secondsSince } from "../lib/time";

const requestPath = ["CloudFront", "API Gateway", "Lambda", "DynamoDB"];
const CHART_ROWS = 5;

const subtitles = {
  connecting: "Connecting to the API",
  live: "Updating as you scroll and click",
  offline: "Offline right now",
};

function useElapsedSeconds(since) {
  const [seconds, setSeconds] = useState(() => secondsSince(since));
  useEffect(() => {
    const id = setInterval(() => setSeconds(secondsSince(since)), 1000);
    return () => clearInterval(id);
  }, [since]);
  return seconds;
}

function Stat({ value, label }) {
  return (
    <div className="rounded-xl bg-white/7 p-5">
      <div className="font-display text-[40px] font-medium leading-tight">
        {value}
      </div>
      <div className="text-[15px] text-navy-muted">{label}</div>
    </div>
  );
}

function ClickChart({ counts, lastClicked }) {
  const ranked = Object.entries(counts)
    .filter(([target]) => target in CLICK_LABELS)
    .sort(([a, x], [b, y]) => y - x || a.localeCompare(b));
  let rows = ranked.slice(0, CHART_ROWS);
  // Always show the visitor's own latest click, even if it isn't in the top rows yet.
  if (lastClicked && !rows.some(([target]) => target === lastClicked)) {
    rows = [...rows.slice(0, CHART_ROWS - 1), ranked.find(([t]) => t === lastClicked)];
  }
  if (rows.length === 0) return null;
  const most = Math.max(...rows.map(([, count]) => count));

  return (
    <div className="flex flex-col gap-3">
      <div>
        <p>What visitors click</p>
        <p className="text-[15px] text-navy-muted">
          Visitors who clicked each one, all time
        </p>
      </div>
      <ol className="flex flex-col gap-3">
        {rows.map(([target, count]) => (
          <li key={target} className="flex flex-col gap-1.5">
            <div className="flex justify-between gap-4 text-[15px]">
              <span>{CLICK_LABELS[target]}</span>
              <span className="text-navy-muted">{count.toLocaleString()}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/7" aria-hidden="true">
              <div
                className={`h-full rounded-full ${
                  target === lastClicked ? "bg-live" : "bg-navy-text"
                }`}
                style={{ width: `${(count / most) * 100}%` }}
              ></div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function BehindTheScenes({ session }) {
  const {
    status,
    visit,
    events,
    eventsSaved,
    lastRoundTripMs,
    clickCounts,
    lastClicked,
    arrivedAt,
    retry,
  } = session;
  const seconds = useElapsedSeconds(arrivedAt);
  const place =
    visit?.location?.region || visit?.location?.country || "Unknown";

  return (
    <aside
      aria-label="What my backend sees"
      className="sticky top-0 flex h-screen flex-col gap-10 self-start overflow-y-auto bg-navy px-12 pb-12 pt-18 text-navy-text"
    >
      <div>
        <h2 className="font-display text-[28px] font-bold">
          What my backend sees
        </h2>
        <p className="text-navy-muted">{subtitles[status]}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {visit ? (
          <>
            <Stat value={formatDuration(seconds)} label="time on page" />
            <Stat value={place} label="from CloudFront headers" />
            <Stat value={eventsSaved} label="events saved in DynamoDB" />
            <Stat value={`${lastRoundTripMs} ms`} label="last round trip" />
          </>
        ) : (
          [1, 2, 3, 4].map((n) => (
            <div key={n} className="h-[104px] rounded-xl bg-white/7"></div>
          ))
        )}
      </div>

      {status === "live" && (
        <ClickChart counts={clickCounts} lastClicked={lastClicked} />
      )}

      {status === "connecting" && (
        <p className="leading-normal">
          Your browser just sent its first request. If this takes a moment, the
          Lambda function is waking up from a cold start.
        </p>
      )}

      {status === "offline" && (
        <div className="flex flex-col gap-3.5 rounded-xl border border-white/20 p-5">
          <p className="leading-normal">
            The API did not respond, so this panel is paused. The rest of the
            site still works, because it is served straight from CloudFront.
          </p>
          <p className="text-[15px] leading-normal text-navy-muted">
            That separation is on purpose: static content and the backend fail
            independently.
          </p>
          <button
            type="button"
            onClick={retry}
            className="min-h-11 cursor-pointer self-start rounded-full bg-navy-text px-4.5 text-[15px] font-semibold text-navy"
          >
            Try again
          </button>
        </div>
      )}

      {events.length > 0 && (
        <ol>
          {events.map((event, index) => (
            <li
              key={event.id}
              className="flex gap-4 border-b border-white/12 py-4 leading-normal"
            >
              <span
                className={`w-14 shrink-0 text-[15px] ${
                  index === 0 ? "text-live" : "text-navy-muted"
                }`}
              >
                {formatDuration(event.at)}
              </span>
              <p>{event.text}</p>
            </li>
          ))}
        </ol>
      )}

      <div className="mt-auto flex flex-col gap-3">
        <p className="text-navy-muted">The path every request takes</p>
        <ul className="flex flex-wrap gap-2">
          {requestPath.map((service) => (
            <li
              key={service}
              className="rounded-full border border-white/30 px-3 py-1.5 text-[15px]"
            >
              {service}
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
