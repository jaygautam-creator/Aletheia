"use client";

import { useCallback, useEffect, useState } from "react";

import { type AccountUser, logout as apiLogout, me } from "@/lib/auth";

/** Tracks the signed-in account, if any, by calling GET /auth/me once on mount. */
export function useAuth(): {
  user: AccountUser | null;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
} {
  const [user, setUser] = useState<AccountUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(await me());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mount-time session check
    void refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return { user, loading, refresh, logout };
}
