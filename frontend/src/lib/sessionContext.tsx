import { createContext, useCallback, useContext, useEffect, useState, type PropsWithChildren } from "react";
import { setApiSession } from "./api";

export type SessionName = "personal" | "demo";

interface SessionContextValue {
  session: SessionName;
  setSession: (s: SessionName) => void;
  isDemo: boolean;
}

const STORAGE_KEY = "finex_session";

function loadSession(): SessionName {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "demo" || stored === "personal") return stored;
  } catch {
    // ignore
  }
  return "personal";
}

const SessionContext = createContext<SessionContextValue>({
  session: "personal",
  setSession: () => {},
  isDemo: false,
});

export function SessionProvider({ children }: PropsWithChildren) {
  const [session, setSessionState] = useState<SessionName>(loadSession);

  const setSession = useCallback((s: SessionName) => {
    setSessionState(s);
    setApiSession(s);
    try {
      localStorage.setItem(STORAGE_KEY, s);
    } catch {
      // ignore
    }
  }, []);

  // Sync on mount in case localStorage had a non-default value
  useEffect(() => {
    setApiSession(session);
  }, [session]);

  return (
    <SessionContext.Provider value={{ session, setSession, isDemo: session === "demo" }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
