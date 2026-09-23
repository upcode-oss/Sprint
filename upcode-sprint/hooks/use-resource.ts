"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/services/api";

export function useResource<T>(path: string | null) {
  const [data, setData] = useState<T>(); const [error, setError] = useState<string>(); const [loading, setLoading] = useState(Boolean(path));
  const reload = useCallback(async () => {
    if (!path) return;
    setLoading(true); setError(undefined);
    try { setData(await api<T>(path)); } catch (reason) { setError((reason as Error).message); } finally { setLoading(false); }
  }, [path]);
  useEffect(() => { void reload(); }, [reload]);
  return { data, setData, error, loading, reload };
}

