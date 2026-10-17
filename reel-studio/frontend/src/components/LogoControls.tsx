import React, { useRef, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import { EditOptions, LogoSettings } from "../types";
import { deleteLogo, errorMessage, mediaUrl, uploadLogo } from "../services/api";
import { cn } from "../utils/cn";
import { Chips, Field, Slider } from "./ui";

interface Props {
  logo: LogoSettings;
  onChange: (patch: Partial<LogoSettings>) => void;
  options: EditOptions;
  onAssetsChanged: () => void;
}

const POS: Record<string, React.CSSProperties> = {
  "top-left": { top: "4%", left: "6%" },
  "top-right": { top: "4%", right: "6%" },
  "bottom-left": { bottom: "6%", left: "6%" },
  "bottom-right": { bottom: "6%", right: "6%" },
  center: { top: "50%", left: "50%", transform: "translate(-50%,-50%)" },
};

/** Pick or upload a logo, choose the corner, size and opacity. */
const LogoControls: React.FC<Props> = ({ logo, onChange, options, onAssetsChanged }) => {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const current = options.logos.find((l) => l.id === logo.id);

  const handleUpload = async (file?: File | null) => {
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const l = await uploadLogo(file);
      onAssetsChanged();
      onChange({ id: l.id });
    } catch (e) {
      setErr(errorMessage(e, "Could not upload that image"));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const remove = async (id: string) => {
    try {
      await deleteLogo(id);
      if (logo.id === id) onChange({ id: null });
      onAssetsChanged();
    } catch (e) {
      setErr(errorMessage(e, "Could not delete the logo"));
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onChange({ id: null })}
          className={cn("h-14 px-3 rounded-xl border text-xs", !logo.id ? "border-indigo-400 bg-indigo-500/20 text-white" : "border-white/10 text-slate-400 hover:text-white")}
        >
          No logo
        </button>
        {options.logos.map((l) => (
          <div key={l.id} className="relative group">
            <button
              type="button"
              onClick={() => onChange({ id: l.id })}
              title={l.name}
              className={cn("h-14 w-20 rounded-xl border p-1.5 bg-white/5 flex items-center justify-center", logo.id === l.id ? "border-indigo-400 shadow-[0_0_12px_rgba(99,102,241,.35)]" : "border-white/10 hover:border-white/25")}
            >
              <img src={mediaUrl(l.url)} alt={l.name} className="max-h-full max-w-full object-contain" />
            </button>
            <button
              type="button"
              onClick={() => remove(l.id)}
              className="absolute -top-1.5 -right-1.5 hidden group-hover:flex w-5 h-5 rounded-full bg-red-500 text-white items-center justify-center"
              aria-label={`Delete ${l.name}`}
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="h-14 px-3 rounded-xl border border-dashed border-white/20 text-xs text-slate-400 hover:text-white flex items-center gap-1.5 disabled:opacity-50"
        >
          <Upload className="w-3.5 h-3.5" /> {busy ? "Uploading…" : "Upload logo"}
        </button>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={(e) => handleUpload(e.target.files?.[0])} />
      </div>
      {err && <p className="text-[11px] text-red-300">{err}</p>}

      {logo.id && current && (
        <div className="grid grid-cols-[90px_1fr] gap-4">
          <div className="relative rounded-lg bg-slate-800 border border-white/10" style={{ aspectRatio: "9/16" }}>
            <img
              src={mediaUrl(current.url)}
              alt=""
              className="absolute object-contain"
              style={{ width: `${logo.size * 100}%`, opacity: logo.opacity, ...POS[logo.position] }}
            />
          </div>
          <div className="space-y-3 min-w-0">
            <Field label="Position">
              <Chips options={options.logoPositions} value={logo.position} onChange={(v) => onChange({ position: v as LogoSettings["position"] })} />
            </Field>
            <Slider label="Size" value={logo.size} min={0.05} max={0.6} step={0.01} onChange={(v) => onChange({ size: v })} format={(v) => `${Math.round(v * 100)}% of width`} />
            <Slider label="Opacity" value={logo.opacity} min={0.1} max={1} step={0.05} onChange={(v) => onChange({ opacity: v })} format={(v) => `${Math.round(v * 100)}%`} />
          </div>
        </div>
      )}
    </div>
  );
};

export default LogoControls;
