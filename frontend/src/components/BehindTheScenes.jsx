import { useEffect, useState } from "react";
import { formatDuration, secondsSince } from "../lib/time";

const requestPath = ["CloudFront", "API Gateway", "Lambda", "DynamoDB"];

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

export default function BehindTheScenes({ session }) {
  const { status, visit, events, eventsSaved, lastRoundTripMs, arrivedAt, retry } =
    session;
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
