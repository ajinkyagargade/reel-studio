import React, { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "../utils/cn";
import { Option } from "../types";

/** Collapsible settings card. */
export const Section: React.FC<{
  title: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}> = ({ title, icon, defaultOpen = false, children }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left"
      >
        <span className="flex items-center gap-2.5 font-semibold text-white text-sm">
          <span className="text-indigo-400 [&>svg]:w-4 [&>svg]:h-4">{icon}</span>
          {title}
        </span>
        <ChevronDown className={cn("w-4 h-4 text-slate-500 transition-transform", open && "rotate-180")} />
      </button>
      {open && <div className="px-5 pb-5 space-y-4 animate-fade-in">{children}</div>}
    </div>
  );
};

export const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
  <div>
    <label className="block text-xs text-slate-500 mb-1.5">{label}</label>
    {children}
    {hint && <p className="text-[11px] text-slate-600 mt-1">{hint}</p>}
  </div>
);

/** Pill buttons for choosing one option. */
export const Chips: React.FC<{
  options: Option[] | string[];
  value: string | null | undefined;
  onChange: (v: string) => void;
}> = ({ options, value, onChange }) => (
  <div className="flex flex-wrap gap-2">
    {(options as any[]).map((o) => {
      const id = typeof o === "string" ? o : o.id;
      const label = typeof o === "string" ? o : o.label;
      const active = id === value;
      return (
        <button
          key={id}
          type="button"
          title={typeof o === "string" ? undefined : o.hint}
          onClick={() => onChange(id)}
          className={cn(
            "px-3 py-1.5 rounded-full text-xs border transition-all",
            active
              ? "border-indigo-400 bg-indigo-500/20 text-white shadow-[0_0_12px_rgba(99,102,241,.35)]"
              : "border-white/10 text-slate-400 hover:text-white hover:border-white/25"
          )}
        >
          {label}
        </button>
      );
    })}
  </div>
);

export const Slider: React.FC<{
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
  format?: (v: number) => string;
}> = ({ label, value, min, max, step, onChange, format }) => (
  <div>
    <div className="flex justify-between text-xs mb-1.5">
      <span className="text-slate-500">{label}</span>
      <span className="text-indigo-300 font-medium">{format ? format(value) : value}</span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value))}
      className="w-full accent-indigo-500"
    />
  </div>
);

export const Toggle: React.FC<{ label: string; value: boolean; onChange: (v: boolean) => void; hint?: string }> = ({
  label,
  value,
  onChange,
  hint,
}) => (
  <button type="button" onClick={() => onChange(!value)} className="w-full flex items-center justify-between gap-4 text-left">
    <span>
      <span className="block text-sm text-slate-300">{label}</span>
      {hint && <span className="block text-[11px] text-slate-600">{hint}</span>}
    </span>
    <span className={cn("w-10 h-6 rounded-full p-0.5 transition-colors shrink-0", value ? "bg-indigo-500" : "bg-white/10")}>
      <span className={cn("block w-5 h-5 rounded-full bg-white transition-transform", value && "translate-x-4")} />
    </span>
  </button>
);

export const Select: React.FC<{
  value: string;
  options: Option[] | string[];
  onChange: (v: string) => void;
  className?: string;
}> = ({ value, options, onChange, className }) => (
  <select value={value} onChange={(e) => onChange(e.target.value)} className={cn("input-dark w-full px-3 py-2.5 text-sm", className)}>
    {(options as any[]).map((o) => {
      const id = typeof o === "string" ? o : o.id;
      return (
        <option key={id} value={id} className="bg-slate-900">
          {typeof o === "string" ? o : o.label}
        </option>
      );
    })}
  </select>
);

/** Shows setup problems (missing ffmpeg / whisper / voice) so nothing fails silently. */
export const Banner: React.FC<{ tone?: "warn" | "info"; children: React.ReactNode }> = ({ tone = "warn", children }) => (
  <div
    className={cn(
      "p-4 rounded-xl border text-sm",
      tone === "warn" ? "bg-amber-500/10 border-amber-500/20 text-amber-200" : "bg-indigo-500/10 border-indigo-500/20 text-indigo-200"
    )}
  >
    {children}
  </div>
);
