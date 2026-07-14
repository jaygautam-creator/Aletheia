"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  type ApiKeyInfo,
  deleteApiKey,
  listApiKeys,
  putApiKey,
  updateProfile,
} from "@/lib/auth";
import { useAuth } from "@/lib/useAuth";

const FIELD =
  "w-full rounded-xl border border-slate-300/70 bg-white/70 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20 focus:outline-none";

const PROVIDERS = ["gemini", "groq", "openrouter"] as const;

function ApiKeyRow({
  provider,
  info,
  onChanged,
}: {
  provider: string;
  info: ApiKeyInfo | undefined;
  onChanged: () => void;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!value.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await putApiKey(provider, value.trim());
      setValue("");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the key.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await deleteApiKey(provider);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove the key.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/60 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium capitalize text-slate-900">{provider}</span>
        {info ? (
          <span className="text-xs text-teal-700">key configured · {info.masked_key}</span>
        ) : (
          <span className="text-xs text-slate-400">using the server&apos;s default key</span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="password"
          placeholder={info ? "Replace key…" : "Paste your API key…"}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className={FIELD}
        />
        <button
          type="button"
          onClick={save}
          disabled={busy || !value.trim()}
          className="shrink-0 rounded-full bg-teal-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Save
        </button>
        {info && (
          <button
            type="button"
            onClick={remove}
            disabled={busy}
            className="shrink-0 rounded-full border border-slate-300 px-4 py-2 text-sm text-slate-600 transition hover:border-rose-300 hover:text-rose-600"
          >
            Remove
          </button>
        )}
      </div>
      {error && <p className="text-sm text-rose-600">{error}</p>}
    </div>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const { user, loading, refresh, logout } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- seed the edit form once the account loads
    if (user) setDisplayName(user.display_name ?? "");
  }, [user]);

  async function loadKeys() {
    try {
      setKeys(await listApiKeys());
    } catch {
      // A key-list failure isn't fatal to viewing the rest of the page.
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch stored keys once the account loads
    if (user) void loadKeys();
  }, [user]);

  async function saveProfile(event: React.FormEvent) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileMessage(null);
    try {
      await updateProfile({ display_name: displayName });
      await refresh();
      setProfileMessage("Saved.");
    } catch (err) {
      setProfileMessage(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setSavingProfile(false);
    }
  }

  if (loading || !user) {
    return <main className="mx-auto max-w-2xl px-6 py-16 text-sm text-slate-500">Loading…</main>;
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-10 px-6 py-16">
      <div className="flex items-center justify-between">
        <h1 className="font-serif text-2xl font-medium text-slate-900">Profile</h1>
        <button
          type="button"
          onClick={() => void logout().then(() => router.push("/"))}
          className="text-sm text-slate-500 hover:text-slate-900"
        >
          Sign out
        </button>
      </div>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-medium text-slate-700">Account</h2>
        <form onSubmit={saveProfile} className="flex flex-col gap-3">
          <input value={user.email} disabled className={`${FIELD} opacity-60`} />
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Display name"
            className={FIELD}
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={savingProfile}
              className="w-fit rounded-full bg-teal-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-teal-700 disabled:opacity-50"
            >
              Save
            </button>
            {profileMessage && <span className="text-sm text-slate-500">{profileMessage}</span>}
          </div>
        </form>
      </section>

      <section className="flex flex-col gap-4">
        <div>
          <h2 className="text-sm font-medium text-slate-700">Your API keys</h2>
          <p className="text-sm text-slate-500">
            Optional. When set, your own key is used instead of the shared server key for your
            requests.
          </p>
        </div>
        <div className="flex flex-col gap-3">
          {PROVIDERS.map((provider) => (
            <ApiKeyRow
              key={provider}
              provider={provider}
              info={keys.find((k) => k.provider === provider)}
              onChanged={loadKeys}
            />
          ))}
        </div>
      </section>

      <a href="/history" className="text-sm text-teal-700 hover:underline">
        View your request history →
      </a>
    </main>
  );
}
