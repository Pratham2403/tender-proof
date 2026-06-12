"use client";

import { useEffect } from "react";

/**
 * Runs `fn` immediately (as a microtask, so state updates never happen
 * synchronously inside the effect) and then on an interval.
 */
export function usePolling(fn: () => void | Promise<void>, intervalMs: number) {
  useEffect(() => {
    let cancelled = false;
    const tick = () => {
      if (!cancelled) void fn();
    };
    queueMicrotask(tick);
    const t = setInterval(tick, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [fn, intervalMs]);
}
