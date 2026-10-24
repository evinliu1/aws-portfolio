import { useCallback, useEffect, useRef, useState } from "react";
import { startVisit } from "../api";
import { secondsSince } from "../lib/time";

const PAGE_OPENED_AT = Date.now();

function describeArrival(visit) {
  const timing = `The round trip took ${visit.roundTripMs} ms, and my Python code ran for ${visit.handlerMs} ms of it.`;
  if (visit.coldStart) {
    return `You arrived. A Lambda function woke up from a cold start and saved your visit to DynamoDB. ${timing}`;
  }
  return `You arrived. A warm Lambda function saved your visit to DynamoDB. ${timing}`;
}

export default function useBackendSession() {
  const [status, setStatus] = useState("connecting");
  const [visit, setVisit] = useState(null);
  const [events, setEvents] = useState([]);
  const requested = useRef(false);

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
      addEvent(describeArrival(result));
      setStatus("live");
    } catch {
      setStatus("offline");
    }
  }, [addEvent]);

  useEffect(() => {
    if (requested.current) return;
    requested.current = true;
    connect();
  }, [connect]);

  return { status, visit, events, arrivedAt: PAGE_OPENED_AT, retry: connect };
}
