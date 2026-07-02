"use client";

import { useEffect } from "react";

import { prefersReducedMotion } from "@/lib/motion";

/**
 * The fixed background aurora. Renders two layered radial fields (styled in globals.css)
 * and, unless reduced motion is requested, drives a `--sy` scroll variable that parallaxes
 * them. The scroll handler is passive and rAF-throttled so it never blocks scrolling.
 */
export function AuroraField() {
  useEffect(() => {
    if (prefersReducedMotion()) return;
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        document.documentElement.style.setProperty("--sy", String(window.scrollY));
        raf = 0;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div aria-hidden className="aurora" />
      <div aria-hidden className="aurora aurora--low" />
    </>
  );
}
