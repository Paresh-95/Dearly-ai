"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, post, refreshSession, tokenStore } from "@/lib/api";
import type { User } from "@/lib/types";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthValue {
  status: Status;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<User | null>(null);

  const loadUser = useCallback(async () => {
    setUser(await api<User>("/auth/me"));
    setStatus("authenticated");
  }, []);

  useEffect(() => {
    (async () => {
      try {
        if (await refreshSession()) return await loadUser();
      } catch {
        /* fall through to anonymous */
      }
      setStatus("anonymous");
    })();
  }, [loadUser]);

  const startSession = useCallback(
    async (path: string, body: unknown) => {
      const { access_token } = await post<{ access_token: string }>(path, body);
      tokenStore.set(access_token);
      await loadUser();
    },
    [loadUser],
  );

  const value: AuthValue = {
    status,
    user,
    login: (email, password) => startSession("/auth/login", { email, password }),
    register: (email, password, displayName) =>
      startSession("/auth/register", { email, password, display_name: displayName || null }),
    logout: async () => {
      await post("/auth/logout");
      tokenStore.set(null);
      setUser(null);
      setStatus("anonymous");
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
