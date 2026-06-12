"use client";

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";
import { IconAlert, IconCheck, IconX } from "./icons";

type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

const ToastContext = createContext<(kind: ToastKind, message: string) => void>(
  () => {},
);

export function useToast() {
  return useContext(ToastContext);
}

const KIND_STYLES: Record<ToastKind, { wrap: string; icon: React.ReactNode }> = {
  success: {
    wrap: "border-emerald-200 bg-white text-emerald-800",
    icon: <IconCheck className="h-4 w-4 text-emerald-600" />,
  },
  error: {
    wrap: "border-rose-200 bg-white text-rose-800",
    icon: <IconAlert className="h-4 w-4 text-rose-600" />,
  },
  info: {
    wrap: "border-slate-200 bg-white text-slate-700",
    icon: <IconCheck className="h-4 w-4 text-indigo-600" />,
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const push = useCallback((kind: ToastKind, message: string) => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, kind, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismiss = (id: number) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-80 flex-col gap-2"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`animate-toast-in pointer-events-auto flex items-start gap-2.5 rounded-xl border p-3.5 text-sm shadow-lg shadow-slate-900/5 ${KIND_STYLES[t.kind].wrap}`}
          >
            <span className="mt-0.5 shrink-0">{KIND_STYLES[t.kind].icon}</span>
            <span className="flex-1 leading-snug">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="shrink-0 rounded p-0.5 text-slate-400 hover:text-slate-600"
              aria-label="Dismiss"
            >
              <IconX className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
