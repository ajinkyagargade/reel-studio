import React, { useEffect, useRef, useState } from "react";
import { Upload } from "lucide-react";
import { CaptionSettings, EditOptions } from "../types";
import { errorMessage, uploadFont } from "../services/api";
import { resolveStyle } from "../utils/captionLayout";
import CaptionText from "./CaptionText";
import { Chips, Field, Select, Slider, Toggle } from "./ui";

interface Props {
  cfg: CaptionSettings;
  onChange: (patch: Partial<CaptionSettings>) => void;
  options: EditOptions;
  onAssetsChanged: () => void;
}

const SAMPLE = "Live captions look like this".split(" ");

/** Style editor for captions: preset, position, size, font (built-in or uploaded), colours. */
const CaptionControls: React.FC<Props> = ({ cfg, onChange, options, onAssetsChanged }) => {
  const [active, setActive] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const preset = options.captionStyles.find((s) => s.id === cfg.style) || options.captionStyles[0];
  const font = options.fonts.find((f) => f.family === (cfg.font || preset.font));
  const style = resolveStyle(cfg, preset, !!font?.builtin);

  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % SAMPLE.length), 550);
    return () => clearInterval(t);
  }, []);

  const handleFont = async (file?: File | null) => {
    if (!file) return;
    setUploading(true);
    setErr(null);
    try {
      const f = await uploadFont(file);
      onAssetsChanged();
      onChange({ font: f.family });
    } catch (e) {
      setErr(errorMessage(e, "Could not upload that font"));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const colorInput = (label: string, value: string, key: "color" | "highlightColor" | "outlineColor") => (
    <Field label={label}>
      <input
        type="color"
        value={value}
        onChange={(e) => onChange({ [key]: e.target.value } as Partial<CaptionSettings>)}
        className="w-full h-10 rounded-lg bg-transparent border border-white/10 cursor-pointer"
      />
    </Field>
  );

  return (
    <div className="space-y-4">
      {/* live sample so every change is visible immediately */}
      <div className="rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 h-28 flex items-center justify-center overflow-hidden">
        <CaptionText words={SAMPLE} activeIndex={active} style={style} size={cfg.size} height={260} />
      </div>

      <Toggle label="Show captions" value={cfg.enabled} onChange={(v) => onChange({ enabled: v })} />
      {cfg.enabled && (
        <>
          <Field label="Style">
            <Chips options={options.captionStyles} value={cfg.style} onChange={(v) => onChange({ style: v })} />
          </Field>
          <Field label="Position">
            <Chips options={options.captionPositions} value={cfg.position} onChange={(v) => onChange({ position: v as CaptionSettings["position"] })} />
          </Field>
          <Slider label="Size" value={cfg.size} min={0.6} max={1.6} step={0.1} onChange={(v) => onChange({ size: v })} format={(v) => `${Math.round(v * 100)}%`} />

          <Field label="Font" hint="Hindi text needs a font that supports Devanagari, e.g. FreeSans, or upload your own.">
            <div className="flex gap-2">
              <Select
                value={cfg.font || ""}
                options={[{ id: "", label: `Style default (${preset.font})` }, ...options.fonts.map((f) => ({ id: f.family, label: f.label }))]}
                onChange={(v) => onChange({ font: v || null })}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="btn-ghost px-3 text-xs flex items-center gap-1.5 whitespace-nowrap disabled:opacity-50"
              >
                <Upload className="w-3.5 h-3.5" /> {uploading ? "Uploading…" : "Upload font"}
              </button>
              <input ref={fileRef} type="file" accept=".ttf,.otf" className="hidden" onChange={(e) => handleFont(e.target.files?.[0])} />
            </div>
            {err && <p className="text-[11px] text-red-300 mt-1">{err}</p>}
          </Field>

          <div className="grid grid-cols-3 gap-3">
            {colorInput("Text", style.color, "color")}
            {colorInput("Highlight", style.highlight, "highlightColor")}
            {colorInput(style.box ? "Box" : "Outline", style.outline, "outlineColor")}
          </div>
          <Toggle label="UPPERCASE" value={style.upper} onChange={(v) => onChange({ uppercase: v })} />
          <Toggle label="Background box" value={style.box} onChange={(v) => onChange({ box: v })} />
          {(cfg.color || cfg.highlightColor || cfg.outlineColor || cfg.uppercase !== null || cfg.box !== null || cfg.font) && (
            <button
              onClick={() => onChange({ color: null, highlightColor: null, outlineColor: null, uppercase: null, box: null, font: null })}
              className="text-[11px] text-indigo-300 hover:text-white"
            >
              Reset font and colours to the style default
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default CaptionControls;
