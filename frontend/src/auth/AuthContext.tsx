import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "../lib/api";
import type { Role, User } from "../types";

export interface RegisterInput {
  full_name: string;
  email: string;
  phone?: string;
  password: string;
  role: "customer" | "vendor";
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore the session from the HTTP-only cookie on page load.
  useEffect(() => {
    let cancelled = false;
    api
      .get<User>("/auth/me")
      .then((res) => !cancelled && setUser(res.data))
      .catch(() => !cancelled && setUser(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<User>("/auth/login", { email, password });
    setUser(res.data);
    return res.data;
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const res = await api.post<User>("/auth/register", { ...input, phone: input.phone || null });
    setUser(res.data);
    return res.data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, setUser }),
    [user, loading, login, register, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

/** Where each role lands after logging in. */
export function homePathFor(role: Role): string {
  if (role === "admin") return "/admin/overview";
  if (role === "vendor") return "/vendor";
  return "/dashboard";
}
