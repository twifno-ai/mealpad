import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const HEALTH_TIMEOUT_MS = 3000;

type Status = "checking" | "ok" | "failed";

type ConnectionContextValue = {
  status: Status;
  online: boolean;
  retry: () => void;
};

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

async function pingHealth(): Promise<boolean> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
  try {
    const res = await fetch("/api/health", { signal: controller.signal });
    if (!res.ok) return false;
    const body = await res.json();
    return body?.ok === true;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("checking");
  const [online, setOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );

  const check = useCallback(async () => {
    setStatus("checking");
    const ok = await pingHealth();
    setStatus(ok ? "ok" : "failed");
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  useEffect(() => {
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  const value = useMemo(
    () => ({ status, online, retry: check }),
    [status, online, check],
  );

  return (
    <ConnectionContext.Provider value={value}>{children}</ConnectionContext.Provider>
  );
}

export function useConnection() {
  const ctx = useContext(ConnectionContext);
  if (!ctx) throw new Error("useConnection outside ConnectionProvider");
  return ctx;
}
