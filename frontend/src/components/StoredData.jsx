import { useState } from "react";
import { CLICK_LABELS } from "../lib/clickTargets";

const solidButton =
  "min-h-11 cursor-pointer rounded-full bg-navy-text px-4.5 text-[15px] font-semibold text-navy disabled:cursor-default disabled:opacity-70";
const outlineButton =
  "min-h-11 cursor-pointer rounded-full border border-white/30 px-4.5 text-[15px] font-semibold disabled:cursor-default disabled:opacity-70";

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function formatDate(epochSeconds) {
  return new Date(epochSeconds * 1000).toLocaleDateString([], {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

// The same heading text the section-view tracker reports.
function sectionLabel(id) {
  return document.getElementById(id)?.querySelector("h2")?.textContent ?? id;
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

// Turns the raw DynamoDB rows into [label, detail] pairs a visitor can read.
function summarize(items) {
  const visit = items.find((item) => item.sk === "META");
  if (!visit) return [];
  const ofType = (type) => items.filter((item) => item.type === type);
  const heartbeats = ofType("heartbeat").length;
  const sections = ofType("section_view").map((item) => sectionLabel(item.section));
  const clicks = ofType("click").map((item) => CLICK_LABELS[item.target] ?? item.target);
  const place = [visit.region, visit.country].filter(Boolean).join(", ") || "an unknown place";

  return [
    [
      "Your visit",
      `Started at ${formatTime(visit.created_at)} from ${place}, on a ${visit.is_mobile ? "phone" : "computer"}`,
    ],
    [
      "Time on page",
      heartbeats ? `${plural(heartbeats, "heartbeat")} from your open tab` : "No heartbeats yet",
    ],
    ["Sections read", sections.join(", ") || "None yet"],
    ["Clicks", clicks.join(", ") || "None yet"],
    [
      "Resume",
      visit.resume_downloaded_at
        ? `Downloaded at ${formatTime(visit.resume_downloaded_at)}`
        : "Not downloaded",
    ],
    ["Deleted automatically on", formatDate(visit.expires_at)],
  ];
}

export default function StoredData({ load, remove }) {
  const [loadState, setLoadState] = useState("idle"); // idle | loading | loaded | error
  const [items, setItems] = useState([]);
  const [confirming, setConfirming] = useState(false);
  const [deleteState, setDeleteState] = useState("idle"); // idle | deleting | error

  async function show() {
    setLoadState("loading");
    try {
      setItems(await load());
      setLoadState("loaded");
    } catch {
      setLoadState("error");
    }
  }

  async function confirmDelete() {
    setDeleteState("deleting");
    try {
      await remove(); // On success the panel switches to its deleted view and this unmounts.
    } catch {
      setDeleteState("error");
    }
  }

  const deleting = deleteState === "deleting";

  return (
    <div className="flex flex-col gap-4">
      <div>
        <p>What I store about you</p>
        <p className="text-[15px] leading-normal text-navy-muted">
          Everything my backend saved about this visit. DynamoDB deletes it
          after 30 days, or you can delete it now.
        </p>
      </div>

      <div aria-live="polite" className="flex flex-col gap-4 empty:hidden">
        {loadState === "loaded" && (
          <>
            <dl className="flex flex-col gap-2.5 text-[15px]">
              {summarize(items).map(([term, detail]) => (
                <div key={term}>
                  <dt className="text-navy-muted">{term}</dt>
                  <dd>{detail}</dd>
                </div>
              ))}
            </dl>
            <details className="text-[15px]">
              <summary className="cursor-pointer text-navy-muted">
                The raw rows in DynamoDB ({items.length})
              </summary>
              <pre className="mt-2 max-h-72 overflow-auto rounded-lg bg-black/25 p-3 text-[13px] leading-snug">
                {JSON.stringify(items, null, 2)}
              </pre>
            </details>
          </>
        )}
        {loadState === "error" && (
          <p className="text-[15px]">Your data didn't load. Try again.</p>
        )}
      </div>

      {confirming ? (
        <div className="flex flex-col gap-3 rounded-xl border border-white/20 p-4">
          <p className="text-[15px] leading-normal">
            Delete everything stored about this visit? Your browser will also
            stop sending events.
          </p>
          <div className="flex flex-wrap gap-2.5">
            <button
              type="button"
              onClick={confirmDelete}
              disabled={deleting}
              className={solidButton}
            >
              {deleting ? "Deleting…" : "Yes, delete it"}
            </button>
            <button
              type="button"
              onClick={() => {
                setConfirming(false);
                setDeleteState("idle");
              }}
              disabled={deleting}
              className={outlineButton}
            >
              Cancel
            </button>
          </div>
          {deleteState === "error" && (
            <p className="text-[15px]" role="alert">
              The delete didn't go through. Try again.
            </p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2.5">
          <button
            type="button"
            onClick={show}
            disabled={loadState === "loading"}
            className={solidButton}
          >
            {loadState === "loading"
              ? "Loading…"
              : loadState === "loaded"
                ? "Refresh"
                : "Show my data"}
          </button>
          <button type="button" onClick={() => setConfirming(true)} className={outlineButton}>
            Delete my data
          </button>
        </div>
      )}

      <p className="text-[15px] leading-normal text-navy-muted">
        My code doesn't store your IP address or set cookies, so this visit
        isn't linked to any other. The visitor count and click tallies are
        plain numbers with nothing tying them to you, so they stay. If you
        download my resume, I get an email saying which region it came from.
      </p>
    </div>
  );
}
