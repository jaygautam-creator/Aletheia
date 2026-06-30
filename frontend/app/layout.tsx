import type { Metadata } from "next";
import { Fraunces, Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// An elegant variable serif for display headlines — the editorial-luxury pairing.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Aletheia — evidence-grounded medical verification",
  description:
    "A multi-agent verification framework, with a rigorous evaluation harness, that improves the reliability of medical answers by grounding every claim in real evidence.",
};

/** The brand mark: a concentric aperture — something concealed, then revealed. */
function Aperture() {
  return (
    <span className="relative inline-flex h-7 w-7 items-center justify-center">
      <svg viewBox="0 0 28 28" className="h-7 w-7" aria-hidden>
        <circle cx="14" cy="14" r="12.5" className="fill-none stroke-teal-500/30" strokeWidth="1.5" />
        <circle
          cx="14"
          cy="14"
          r="7.5"
          className="fill-none stroke-teal-600"
          strokeWidth="2"
          strokeDasharray="35 12"
          strokeLinecap="round"
        />
        <circle cx="14" cy="14" r="2.5" className="fill-cyan-500" />
      </svg>
    </span>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-slate-900/[0.06] bg-[var(--background)]/70 backdrop-blur-xl">
          <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-3.5">
            <Link href="/" className="group flex items-center gap-2.5">
              <Aperture />
              <span className="font-serif text-xl font-medium tracking-tight text-slate-900">
                Aletheia
              </span>
            </Link>
            <div className="flex items-center gap-7 text-sm text-slate-500">
              <Link href="/verify" className="transition-colors hover:text-slate-900">
                Verify
              </Link>
              <a
                href="https://github.com/jaygautam-creator/Aletheia"
                target="_blank"
                rel="noreferrer"
                className="transition-colors hover:text-slate-900"
              >
                GitHub ↗
              </a>
            </div>
          </nav>
        </header>
        <div className="flex-1">{children}</div>
      </body>
    </html>
  );
}
