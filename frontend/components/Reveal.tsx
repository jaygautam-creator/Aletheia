"use client";

import type { ReactNode } from "react";

import { useInView } from "@/lib/motion";

/**
 * Fade-and-rise a block into view as it scrolls in. The actual motion lives in CSS
 * (`[data-reveal]`), so it is disabled cleanly under prefers-reduced-motion; this only
 * toggles the state. `delay` staggers siblings.
 */
export function Reveal({
  children,
  delay = 0,
  className,
  id,
  as: Tag = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  id?: string;
  as?: "div" | "section" | "li" | "figure";
}) {
  const { ref, inView } = useInView<HTMLElement>();
  return (
    <Tag
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ref={ref as any}
      id={id}
      data-reveal={inView ? "in" : "out"}
      style={{ ["--reveal-delay" as string]: `${delay}ms` }}
      className={className}
    >
      {children}
    </Tag>
  );
}
