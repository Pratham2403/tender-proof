"use client";

import { useEffect, useRef, useState } from "react";
import type { JobProgressEvent } from "@/types";
import { API_BASE, api } from "@/lib/api";

interface JobEventState {
  jobId: string | null;
  event: JobProgressEvent | null;
}

/**
 * Streams job progress over WebSocket, falling back to REST polling if the
 * socket drops. Returns the latest progress event for the given job.
 */
export function useJobProgress(jobId: string | null) {
  // State is keyed by jobId so switching jobs implicitly resets the event
  // without a synchronous setState inside the effect.
  const [state, setState] = useState<JobEventState>({ jobId: null, event: null });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const wsUrl = API_BASE.replace(/^http/, "ws") + `/ws/jobs/${jobId}`;
    let ws: WebSocket | null = null;
    let closed = false;
    const emit = (event: JobProgressEvent) => setState({ jobId, event });

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const startPolling = () => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        try {
          const status = await api.getJobStatus(jobId);
          if (status.status === "SUCCESS") {
            emit({ type: "complete" });
            stopPolling();
          } else if (status.status === "FAILURE") {
            emit({ type: "error", reason: status.message });
            stopPolling();
          } else {
            emit({
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

    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (msg) => {
        const data = JSON.parse(msg.data) as JobProgressEvent;
        emit(data);
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

  return state.jobId === jobId ? state.event : null;
}
