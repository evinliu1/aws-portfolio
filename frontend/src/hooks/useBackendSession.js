import { useCallback, useEffect, useRef, useState } from "react";
import { requestResume, sendEvent, startVisit } from "../api";
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

function describeResumeDownload(result) {
  const minutes = result.expiresInSeconds / 60;
  const link = `a Lambda function signed a private S3 link that works for ${minutes} minutes`;
  if (!result.firstDownload) {
    return `You downloaded my resume again, so ${link}. I only get notified once per visit, so my phone stayed quiet. ${describeTiming(result)}`;
  }
  if (!result.notified) {
    return `You downloaded my resume, so ${link}. SNS couldn't send my notification this time, so my phone stayed quiet. ${describeTiming(result)}`;
  }
  return `You downloaded my resume, so ${link} and recorded the download on your visit. SNS emailed me about it, so my phone just buzzed. ${describeTiming(result)}`;
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

  // Throws if the API can't be reached, so the button can show that the download failed.
  const downloadResume = useCallback(async () => {
    const result = await requestResume(sessionId);
    window.location.assign(result.url); // The link says "attachment", so the page stays put.
    setLastRoundTripMs(result.roundTripMs);
    if (sessionId) addEvent(describeResumeDownload(result));
  }, [sessionId, addEvent]);

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
    downloadResume,
  };
}
