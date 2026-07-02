"use client";

import { useEffect, useRef, useState } from "react";

/** True once the user has asked for reduced motion — animations should no-op. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Observe an element and report when it first scrolls into view. Fires once, then
 * disconnects — reveal animations should not replay on scroll-back.
 */
export function useInView<T extends Element>(rootMargin = "0px 0px -12% 0px"): {
  ref: React.RefObject<T | null>;
  inView: boolean;
} {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
      // Reduced motion (or no observer / a test environment): there is no reveal to wait
      // for, so show the final content immediately. Deferred so it is not a synchronous
      // setState in the effect body.
      const id = setTimeout(() => setInView(true), 0);
      return () => clearTimeout(id);
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2, rootMargin },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin]);

  return { ref, inView };
}

/**
 * Animate a number from 0 to `target` once `active` becomes true. Honours
 * prefers-reduced-motion by snapping straight to the target.
 */
export function useCountUp(target: number, active: boolean, durationMs = 1100): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!active) return;
    if (prefersReducedMotion() || typeof requestAnimationFrame !== "function") {
      // Snap straight to the target, deferred to a callback so it is not a synchronous
      // setState in the effect body.
      const id = setTimeout(() => setValue(target), 0);
      return () => clearTimeout(id);
    }
    let raf = 0;
    let start: number | null = null;
    const step = (t: number) => {
      if (start === null) start = t;
      const progress = Math.min((t - start) / durationMs, 1);
      // easeOutCubic for a confident settle.
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, active, durationMs]);

  return value;
}
