"use client";

import { CheckCircle2, CircleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";

type Toast = { id: number; message: string; kind: "success" | "error" };
type ToastContextValue = { notify: (message: string, kind?: Toast["kind"]) => void };
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notify = useCallback((message: string, kind: Toast["kind"] = "success") => {
    const id = Date.now();
    setToasts((current) => [...current, { id, message, kind }]);
    if (kind === "success") {
      window.setTimeout(() => setToasts((current) => current.filter((item) => item.id !== id)), 4500);
    }
  }, []);
  const value = useMemo(() => ({ notify }), [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region">
        {toasts.map((toast) => (
          <div className={`toast toast-${toast.kind}`} key={toast.id} role={toast.kind === "error" ? "alert" : "status"}>
            {toast.kind === "success" ? <CheckCircle2 aria-hidden /> : <CircleAlert aria-hidden />}
            <span>{toast.message}</span>
            <Button variant="ghost" size="icon" aria-label="Dismiss notification" onClick={() => setToasts((items) => items.filter((item) => item.id !== toast.id))}><X /></Button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
