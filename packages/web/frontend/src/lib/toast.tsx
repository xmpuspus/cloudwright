import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import Icon from "../components/Icon";

export type ToastKind = "error" | "success";

interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ToastApi {
  notify: (text: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastApi>({ notify: () => undefined });

/** Surfaces the failures the old code swallowed. Polite live region, so a screen
 *  reader hears the message without losing the caret position. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (text: string, kind: ToastKind = "error") => {
      const id = Date.now() + Math.random();
      setToasts((current) => [...current.slice(-3), { id, kind, text }]);
      window.setTimeout(() => dismiss(id), kind === "success" ? 3000 : 8000);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast${toast.kind === "success" ? " toast--success" : ""}`}>
            <Icon name={toast.kind === "success" ? "check" : "alert"} size={15} />
            <span>{toast.text}</span>
            <button className="toast__close" onClick={() => dismiss(toast.id)} aria-label="Dismiss">
              <Icon name="close" size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
