"use client";

import { useEffect, useRef, useState } from "react";
import type { JobProgressEvent } from "@/types";
import { API_BASE, api } from "@/lib/api";

/**
 * Streams job progress over WebSocket, falling back to REST polling if the
 * socket drops. Returns the latest progress event.
 */
export function useJobProgress(jobId: string | null) {
  const [event, setEvent] = useState<JobProgressEvent | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setEvent(null);

    const wsUrl = API_BASE.replace(/^http/, "ws") + `/ws/jobs/${jobId}`;
    let ws: WebSocket | null = null;
    let closed = false;

    const startPolling = () => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const status = await api.getJobStatus(jobId);
          if (status.status === "SUCCESS") {
            setEvent({ type: "complete" });
            stopPolling();
          } else if (status.status === "FAILURE") {
            setEvent({ type: "error", reason: status.message });
            stopPolling();
          } else {
            setEvent({
              type: "progress",
              pct: status.progress_pct,
              message: status.message,
            });
          }
        } catch {
          // API unreachable — keep polling
        }
      }, 2000);
    };

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data) as JobProgressEvent;
        setEvent(data);
        if (data.type === "complete" || data.type === "error") {
          closed = true;
          ws?.close();
        }
      };
      ws.onerror = () => {
        if (!closed) startPolling();
      };
      ws.onclose = () => {
        if (!closed) startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      closed = true;
      ws?.close();
      stopPolling();
    };
  }, [jobId]);

  return event;
}
