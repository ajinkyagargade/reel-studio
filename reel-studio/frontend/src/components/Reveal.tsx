import React from "react";
import { useReveal } from "../hooks/useReveal";
import { cn } from "../utils/cn";

interface Props {
  children: React.ReactNode;
  delay?: number; // ms
  variant?: "up" | "left" | "right" | "zoom" | "blur";
  className?: string;
}

/** Scroll-triggered entrance animation wrapper. */
const Reveal: React.FC<Props> = ({ children, delay = 0, variant = "up", className }) => {
  const ref = useReveal<HTMLDivElement>();
  return (
    <div ref={ref} className={cn("reveal", `reveal-${variant}`, className)} style={{ transitionDelay: `${delay}ms` }}>
      {children}
    </div>
  );
};

export default Reveal;
