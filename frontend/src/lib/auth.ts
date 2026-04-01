"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { api, ApiError, storeTokens as storeTokenPair, clearTokens } from "./api";
import type { TokenResponse, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    org_name: string;
    org_slug: string;
    full_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const res = await api.get<User>("/users/me");
      setUser(res.data);
    } catch (err) {
      // Only clear tokens on auth failures (401/403). Network errors,
      // timeouts, and server errors should not log the user out.
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        clearTokens();
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<TokenResponse>("/auth/login", {
      email,
      password,
    });
    storeTokenPair(res.data.access_token, res.data.refresh_token);
    await fetchUser();
  }, [fetchUser]);

  const register = useCallback(async (data: {
    org_name: string;
    org_slug: string;
    full_name: string;
    email: string;
    password: string;
  }) => {
    const res = await api.post<TokenResponse>("/auth/register", data);
    storeTokenPair(res.data.access_token, res.data.refresh_token);
    await fetchUser();
  }, [fetchUser]);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout]
  );

  return React.createElement(
    AuthContext.Provider,
    { value },
    children
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
