import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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

export const metadata: Metadata = {
  title: "Aletheia — evidence-grounded multi-agent verification",
  description:
    "A multi-agent verification framework, with a rigorous evaluation harness, that improves the reliability of LLM answers by grounding every claim in real evidence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/[0.06] bg-[var(--background)]/75 backdrop-blur-md">
          <nav className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-3.5">
            <Link
              href="/"
              className="group flex items-center gap-2.5 text-sm font-semibold tracking-tight"
            >
              <span
                aria-hidden
                className="text-lg leading-none text-emerald-400 transition-transform duration-500 group-hover:rotate-180"
              >
                ◐
              </span>
              Aletheia
            </Link>
            <div className="flex items-center gap-6 font-mono text-xs text-neutral-500">
              <Link href="/verify" className="transition-colors hover:text-neutral-200">
                Verify
              </Link>
              <a
                href="https://github.com/jaygautam-creator/Aletheia"
                target="_blank"
                rel="noreferrer"
                className="transition-colors hover:text-neutral-200"
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
