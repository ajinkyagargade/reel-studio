import React, { useRef } from "react";
import { cn } from "../utils/cn";

interface Props {
  children: React.ReactNode;
  className?: string;
  tilt?: number; // max degrees
}

/** Card with a cursor-following spotlight and 3D tilt. */
const SpotlightCard: React.FC<Props> = ({ children, className, tilt = 6 }) => {
  const ref = useRef<HTMLDivElement>(null);

  const move = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    el.style.setProperty("--mx", `${x * 100}%`);
    el.style.setProperty("--my", `${y * 100}%`);
    el.style.transform = `perspective(900px) rotateX(${(0.5 - y) * tilt}deg) rotateY(${(x - 0.5) * tilt}deg) translateZ(0)`;
  };
  const leave = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  return (
    <div ref={ref} onMouseMove={move} onMouseLeave={leave} className={cn("spot-card", className)}>
      <div className="relative z-10 h-full">{children}</div>
    </div>
  );
};

export default SpotlightCard;
