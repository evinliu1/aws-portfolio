import { useCallback, useEffect, useRef, useState } from "react";
import { sendEvent, startVisit } from "../api";
import { secondsSince } from "../lib/time";

const PAGE_OPENED_AT = Date.now();
const HEARTBEAT_MS = 15_000;
// Stop after 30 minutes so a forgotten tab doesn't keep writing to DynamoDB.
const MAX_HEARTBEATS = 120;

function describeTiming(result) {
  return `The round trip took ${result.roundTripMs} ms, and my Python code ran for ${result.handlerMs} ms of it.`;
}

function describeArrival(visit) {
  if (visit.coldStart) {
    return `You arrived. A Lambda function woke up from a cold start and saved your visit to DynamoDB. ${describeTiming(visit)}`;
  }
  return `You arrived. A warm Lambda function saved your visit to DynamoDB. ${describeTiming(visit)}`;
}

function describeEventSave(result) {
  if (result.coldStart) {
    return `Events go to a separate Lambda function, so it woke up from its own cold start to save this one. ${describeTiming(result)}`;
  }
  return `A warm Lambda function saved it to DynamoDB. ${describeTiming(result)}`;
}

function describeFirstHeartbeat(result) {
  const seconds = HEARTBEAT_MS / 1000;
  return `You've been reading for ${seconds} seconds. Your browser now checks in every ${seconds} seconds, and each check-in is saved as an event under your visit. ${describeEventSave(result)}`;
}

function describeSectionView(label, result) {
  return `You reached the ${label} section. ${describeEventSave(result)}`;
}

export default function useBackendSession() {
  const [status, setStatus] = useState("connecting");
  const [visit, setVisit] = useState(null);
  const [events, setEvents] = useState([]);
  const [eventsSaved, setEventsSaved] = useState(0);
  const [lastRoundTripMs, setLastRoundTripMs] = useState(null);
  const requested = useRef(false);
  const seenSections = useRef(new Set());
  const sessionId = visit?.sessionId;

  const addEvent = useCallback((text) => {
    const event = {
      id: crypto.randomUUID(),
      at: secondsSince(PAGE_OPENED_AT),
      text,
    };
    setEvents((previous) => [event, ...previous]);
  }, []);

  const connect = useCallback(async () => {
    setStatus("connecting");
    try {
      const result = await startVisit();
      setVisit(result);
      setLastRoundTripMs(result.roundTripMs);
      addEvent(describeArrival(result));
      setStatus("live");
    } catch {
      setStatus("offline");
    }
  }, [addEvent]);

  // Saves one event. `describe` turns the API's reply into a feed entry; pass null to skip the feed.
  const record = useCallback(
    async (payload, describe) => {
      if (!sessionId) return;
      try {
        const result = await sendEvent(sessionId, payload);
        setEventsSaved((count) => count + 1);
        setLastRoundTripMs(result.roundTripMs);
        if (describe) addEvent(describe(result));
      } catch {
        // A lost event isn't worth interrupting the visitor for; the next one may get through.
      }
    },
    [sessionId, addEvent]
  );

  const viewSection = useCallback(
    (id, label) => {
      if (seenSections.current.has(id)) return;
      seenSections.current.add(id);
      record({ type: "section_view", section: id }, (result) =>
        describeSectionView(label, result)
      );
    },
    [record]
  );

  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    connect();
  }, [connect]);

  useEffect(() => {
    if (!sessionId) return;
    let sent = 0;
    const id = setInterval(() => {
      if (document.hidden) return; // Only count time the tab is actually being looked at.
      sent += 1;
      if (sent >= MAX_HEARTBEATS) clearInterval(id);
      record({ type: "heartbeat" }, sent === 1 ? describeFirstHeartbeat : null);
    }, HEARTBEAT_MS);
    return () => clearInterval(id);
  }, [sessionId, record]);

  return {
    status,
    visit,
    events,
    eventsSaved,
    lastRoundTripMs,
    arrivedAt: PAGE_OPENED_AT,
    retry: connect,
    viewSection,
  };
}
