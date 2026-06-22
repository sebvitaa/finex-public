import { useEffect, useRef, useState } from "react";

/**
 * Adds the `is-visible` class to the element the first time it scrolls into view.
 * Works with the `.fx-reveal` styles defined in styles.css.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: { threshold?: number; once?: boolean }) {
  const ref = useRef<T | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true);
            if (options?.once !== false) observer.unobserve(entry.target);
          } else if (options?.once === false) {
            setVisible(false);
          }
        });
      },
      { threshold: options?.threshold ?? 0.18 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [options?.threshold, options?.once]);

  return { ref, visible };
}

/**
 * Animated number that counts up from 0 to `target` once it becomes active.
 */
export function useCountUp(target: number, active: boolean, durationMs = 1400) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!active) return;
    if (typeof window === "undefined" || typeof requestAnimationFrame === "undefined") {
      setValue(target);
      return;
    }

    let raf = 0;
    let start: number | null = null;
    const step = (ts: number) => {
      if (start === null) start = ts;
      const progress = Math.min((ts - start) / durationMs, 1);
      // easeOutCubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, active, durationMs]);

  return value;
}
