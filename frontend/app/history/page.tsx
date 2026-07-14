"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { type HistoryEntry, myHistory } from "@/lib/auth";
import { useAuth } from "@/lib/useAuth";

export default function HistoryPage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    myHistory()
      .then(setEntries)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load history."));
  }, [user]);

  if (loading || !user) {
    return <main className="mx-auto max-w-4xl px-6 py-16 text-sm text-slate-500">Loading…</main>;
  }

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-16">
      <h1 className="font-serif text-2xl font-medium text-slate-900">Your history</h1>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {entries.length === 0 && !error ? (
        <p className="text-sm text-slate-500">No requests yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white/60">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="px-4 py-2 font-medium">When</th>
                <th className="px-4 py-2 font-medium">Route</th>
                <th className="px-4 py-2 font-medium">Query</th>
                <th className="px-4 py-2 font-medium">Key</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Latency</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2 whitespace-nowrap text-slate-600">
                    {new Date(entry.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-slate-600">{entry.route}</td>
                  <td className="max-w-xs truncate px-4 py-2 text-slate-600">
                    {entry.query_preview ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {entry.key_source === "user_key" ? "your key" : "server default"} ·{" "}
                    {entry.provider}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={
                        entry.status === "ok"
                          ? "text-teal-700"
                          : entry.status === "refused"
                            ? "text-amber-600"
                            : "text-rose-600"
                      }
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {entry.latency_ms != null ? `${entry.latency_ms} ms` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
