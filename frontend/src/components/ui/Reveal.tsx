import type { ReactNode } from "react";

import { useReveal } from "../../lib/motion";

type RevealProps = {
  children: ReactNode;
  className?: string;
  delay?: number;
};

/** Fades + lifts its children into view the first time they scroll into the viewport. */
export function Reveal({ children, className = "", delay = 0 }: RevealProps) {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`fx-reveal ${visible ? "is-visible" : ""} ${className}`}
      style={{ transitionDelay: visible ? `${delay}ms` : "0ms" }}
    >
      {children}
    </div>
  );
}
