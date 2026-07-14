"use client";

import Link from "next/link";

import { useAuth } from "@/lib/useAuth";

/** Shows profile/history when signed in, or sign-in/sign-up when not. */
export function AuthNav() {
  const { user, loading } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <>
        <Link href="/login" className="transition-colors hover:text-slate-900">
          Sign in
        </Link>
        <Link href="/signup" className="transition-colors hover:text-slate-900">
          Sign up
        </Link>
      </>
    );
  }

  return (
    <>
      <Link href="/history" className="transition-colors hover:text-slate-900">
        History
      </Link>
      <Link href="/profile" className="transition-colors hover:text-slate-900">
        {user.display_name || "Profile"}
      </Link>
    </>
  );
}
