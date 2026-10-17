import React from "react";
import { cn } from "../utils/cn";

interface ProgressBarProps {
  progress: number;
  label?: string;
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, label, className }) => {
  const clamped = Math.min(100, Math.max(0, progress));

  return (
    <div className={cn("w-full", className)}>
      {label && (
        <div className="flex justify-between text-sm text-slate-400 mb-2">
          <span>{label}</span>
          <span className="text-indigo-400 font-medium">{clamped}%</span>
        </div>
      )}
      <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-indigo-500 to-purple-500"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;