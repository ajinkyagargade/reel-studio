import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Download,
  Film,
  Image as ImageIcon,
  Loader2,
  Mic,
  Palette,
  Play,
  Plus,
  RefreshCw,
  SlidersHorizontal,
  Sparkles,
  Subtitles,
  Trash2,
  Wand2,
} from "lucide-react";
import { Analysis, EditOptions, Reel, ReelPoint, ReelSettings, Video } from "../types";
import { getReel, mediaUrl, renderReel, replanReel, errorMessage } from "../services/api";
import { fmtTime } from "../utils/format";
import { cn } from "../utils/cn";
import ProgressBar from "./ProgressBar";
import { Chips, Field, Section, Select, Slider, Toggle } from "./ui";
import CaptionControls from "./CaptionControls";
import LogoControls from "./LogoControls";

interface Props {
  video: Video;
  analysis: Analysis;
  options: EditOptions;
  reel: Reel;
  onReel: (r: Reel) => void;
  onSeekSource: (seconds: number) => void;
  onAssetsChanged: () => void;
}

const newId = () => Math.random().toString(36).slice(2, 14);
const sig = (points: ReelPoint[], settings: ReelSettings) => JSON.stringify([points, settings]);

const ReelStudio: React.FC<Props> = ({ video, analysis, options, reel, onReel, onSeekSource, onAssetsChanged }) => {
  const [points, setPoints] = useState<ReelPoint[]>(reel.points);
  const [settings, setSettings] = useState<ReelSettings>(reel.settings);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [planTarget, setPlanTarget] = useState(reel.settings.targetSeconds);
  const [planCount, setPlanCount] = useState(Math.max(3, Math.min(8, Math.round(reel.settings.targetSeconds / 10))));

  // Re-sync drafts when a different reel is opened.
  useEffect(() => {
    setPoints(reel.points);
    setSettings(reel.settings);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reel.id]);

  // Poll while rendering.
  useEffect(() => {
    if (reel.status !== "rendering") return;
    const t = setInterval(async () => {
      try {
        onReel(await getReel(reel.id));
      } catch {
        /* transient network error: keep polling */
      }
    }, 1500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reel.status, reel.id]);

  const dirty = sig(points, settings) !== sig(reel.points, reel.settings);
  const rendering = reel.status === "rendering";
  const set = <K extends keyof ReelSettings>(key: K, value: ReelSettings[K]) => setSettings((s) => ({ ...s, [key]: value }));
  const setCap = (patch: Partial<ReelSettings["captions"]>) => setSettings((s) => ({ ...s, captions: { ...s.captions, ...patch } }));

  const updatePoint = (i: number, patch: Partial<ReelPoint>) =>
    setPoints((ps) => ps.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  const move = (i: number, dir: -1 | 1) =>
    setPoints((ps) => {
      const j = i + dir;
      if (j < 0 || j >= ps.length) return ps;
      const copy = [...ps];
      [copy[i], copy[j]] = [copy[j], copy[i]];
      return copy;
    });
  const remove = (i: number) => setPoints((ps) => ps.filter((_, idx) => idx !== i));

  const unused = useMemo(
    () => analysis.keyPoints.filter((k) => !points.some((p) => Math.abs(p.start - k.start) < 1)),
    [analysis.keyPoints, points]
  );
  const addKeyPoint = (idx: number) => {
    const k = unused[idx];
    if (!k) return;
    setPoints((ps) => [
      ...ps,
      { id: newId(), title: k.title, text: k.narration || k.summary, start: k.start, end: k.end, enabled: true, transition: null, customText: false },
    ]);
  };
  const addBlank = () =>
    setPoints((ps) => [
      ...ps,
      { id: newId(), title: "New point", text: "", start: 0, end: Math.min(10, video.duration || 10), enabled: true, transition: null, customText: true },
    ]);

  const estimate = useMemo(() => {
    const on = points.filter((p) => p.enabled);
    if (!on.length) return 0;
    const td = settings.transitionDuration;
    if (settings.voice === "ai") {
      const speech = on.reduce((a, p) => a + (p.text || p.title).split(/\s+/).length / (2.4 * (1 + settings.ttsRate / 100)), 0);
      return Math.max(0, speech + on.length * 0.55 - (on.length - 1) * td);
    }
    const cap = settings.fitToTarget ? settings.targetSeconds / on.length : 1e9;
    const len = on.reduce((a, p) => a + Math.min(p.end - p.start, cap * settings.speed) / settings.speed, 0);
    return Math.max(0, len - (on.length - 1) * td);
  }, [points, settings]);

  const handleRender = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await renderReel(reel.id, { points, settings });
      setPoints(r.points);
      setSettings(r.settings);
      onReel(r);
    } catch (e) {
      setError(errorMessage(e, "Could not start rendering"));
    } finally {
      setBusy(false);
    }
  };

  const handleReplan = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await replanReel(reel.id, { targetSeconds: planTarget, numPoints: planCount });
      setPoints(r.points);
      setSettings(r.settings);
      onReel(r);
    } catch (e) {
      setError(errorMessage(e, "Could not re-plan the reel"));
    } finally {
      setBusy(false);
    }
  };

  const ready = reel.status === "ready" && !!reel.outputUrl;
  const portrait = !reel.width || !reel.height || reel.height >= reel.width;
  const aspectStyle = reel.width && reel.height ? { aspectRatio: `${reel.width} / ${reel.height}` } : { aspectRatio: "9 / 16" };
  const cap = settings.captions;
  const groupedTransitions = useMemo(() => {
    const groups: Record<string, typeof options.transitions> = {};
    options.transitions.forEach((t) => {
      (groups[t.group || "Other"] = groups[t.group || "Other"] || []).push(t);
    });
    return groups;
  }, [options.transitions]);

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* ---------------- Left: preview + render ---------------- */}
      <div className="lg:col-span-2">
        <div className="lg:sticky lg:top-28 space-y-4">
          <div className="glass-card rounded-2xl p-4">
            <div className={cn("mx-auto bg-black rounded-xl overflow-hidden border border-white/10", portrait ? "max-w-[300px]" : "w-full")} style={aspectStyle}>
              {ready ? (
                <video key={reel.outputUrl} src={mediaUrl(reel.outputUrl)} controls playsInline className="w-full h-full object-contain" />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 text-sm gap-3 p-6 text-center">
                  {rendering ? <Loader2 className="w-8 h-8 animate-spin text-indigo-400" /> : <Film className="w-8 h-8" />}
                  {rendering ? "Rendering your reel…" : reel.status === "failed" ? "Render failed" : "No reel rendered yet"}
                </div>
              )}
            </div>
          </div>

          <div className="glass-card rounded-2xl p-5 space-y-3">
            {rendering && <ProgressBar progress={reel.progress} label={reel.message || "Rendering…"} />}
            {reel.status === "failed" && (
              <div className="flex gap-2 text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="break-words min-w-0">{reel.message}</span>
              </div>
            )}
            {reel.notes?.map((n) => (
              <div key={n} className="text-xs text-amber-200 bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">{n}</div>
            ))}
            {error && <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/20 rounded-xl p-3">{error}</div>}

            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Estimated length ≈ <span className="text-indigo-300 font-medium">{Math.round(estimate)}s</span></span>
              {ready && reel.duration ? <span>Last render: {Math.round(reel.duration)}s</span> : null}
            </div>
            {(dirty || reel.stale) && ready && (
              <p className="text-xs text-amber-300">You have changes that are not in the video yet.</p>
            )}

            <button
              onClick={handleRender}
              disabled={busy || rendering || points.every((p) => !p.enabled)}
              className="btn-primary w-full py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {rendering ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Rendering…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" /> {ready ? "Apply changes & re-render" : "Render reel"}
                </>
              )}
            </button>
            {ready && reel.downloadUrl && (
              <a
                href={mediaUrl(reel.downloadUrl)}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-colors"
              >
                <Download className="w-4 h-4" /> Download reel
              </a>
            )}
            <p className="text-[11px] text-slate-600">
              Tip: choose “Draft” quality under Look &amp; framing for fast test renders, then switch to HD for the final.
            </p>
          </div>
        </div>
      </div>

      {/* ---------------- Right: editing ---------------- */}
      <div className="lg:col-span-3 space-y-4">
        {/* Plan */}
        <Section title="Plan the reel" icon={<Sparkles />} defaultOpen={false}>
          <div className="grid grid-cols-2 gap-4">
            <Slider label="Target length" value={planTarget} min={15} max={90} step={5} onChange={setPlanTarget} format={(v) => `${v}s`} />
            <Slider label="Number of points" value={planCount} min={2} max={12} step={1} onChange={setPlanCount} />
          </div>
          <button onClick={handleReplan} disabled={busy || rendering} className="btn-ghost w-full py-2.5 text-sm flex items-center justify-center gap-2 disabled:opacity-50">
            <RefreshCw className="w-4 h-4" /> Re-pick the best points
          </button>
          <p className="text-[11px] text-slate-600">This replaces the point list below with the highest-importance moments of the video.</p>
        </Section>

        {/* Points */}
        <div className="glass-card rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white text-sm flex items-center gap-2">
              <Film className="w-4 h-4 text-indigo-400" /> Reel points ({points.filter((p) => p.enabled).length}/{points.length})
            </h3>
            <button onClick={addBlank} className="text-xs text-indigo-300 hover:text-white flex items-center gap-1">
              <Plus className="w-3.5 h-3.5" /> Custom point
            </button>
          </div>

          <div className="space-y-3">
            {points.map((p, i) => (
              <div key={p.id} className={cn("rounded-xl border p-4 space-y-3 transition-opacity", p.enabled ? "border-white/10 bg-white/[0.02]" : "border-white/5 opacity-50")}>
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-300 text-xs flex items-center justify-center shrink-0">{i + 1}</span>
                  <input value={p.title} onChange={(e) => updatePoint(i, { title: e.target.value })} className="input-dark flex-1 min-w-0 px-3 py-2 text-sm" aria-label="Point title" />
                  <button onClick={() => move(i, -1)} disabled={i === 0} className="p-1.5 text-slate-500 hover:text-white disabled:opacity-30" aria-label="Move up"><ArrowUp className="w-4 h-4" /></button>
                  <button onClick={() => move(i, 1)} disabled={i === points.length - 1} className="p-1.5 text-slate-500 hover:text-white disabled:opacity-30" aria-label="Move down"><ArrowDown className="w-4 h-4" /></button>
                  <button onClick={() => remove(i)} className="p-1.5 text-slate-500 hover:text-red-400" aria-label="Delete point"><Trash2 className="w-4 h-4" /></button>
                </div>

                <textarea
                  value={p.text}
                  rows={2}
                  onChange={(e) => updatePoint(i, { text: e.target.value, customText: true })}
                  placeholder={settings.voice === "ai" ? "What the voice-over says (also used for captions)" : "Caption text (leave empty to use the real transcript)"}
                  className="input-dark w-full px-3 py-2 text-sm resize-y"
                />
                {settings.voice !== "ai" && p.customText && p.text && (
                  <button onClick={() => updatePoint(i, { text: "", customText: false })} className="text-[11px] text-indigo-300 hover:text-white">
                    Use the real transcript for captions instead
                  </button>
                )}

                <div className="grid grid-cols-3 gap-3 items-end">
                  <Field label="Start (s)">
                    <input type="number" step="0.1" min={0} value={p.start} onChange={(e) => updatePoint(i, { start: parseFloat(e.target.value) || 0 })} className="input-dark w-full px-3 py-2 text-sm" />
                  </Field>
                  <Field label="End (s)">
                    <input type="number" step="0.1" min={0} value={p.end} onChange={(e) => updatePoint(i, { end: parseFloat(e.target.value) || 0 })} className="input-dark w-full px-3 py-2 text-sm" />
                  </Field>
                  <button onClick={() => onSeekSource(p.start)} className="btn-ghost py-2 text-xs" title="Jump the source video to this moment">
                    Source {fmtTime(p.start)}
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 items-end">
                  <Field label={i === points.length - 1 ? "Transition (last point: unused)" : "Transition into next point"}>
                    <Select
                      value={p.transition || ""}
                      onChange={(v) => updatePoint(i, { transition: v || null })}
                      options={[{ id: "", label: "Use default" }, ...options.transitions]}
                    />
                  </Field>
                  <Toggle label="Include" value={p.enabled} onChange={(v) => updatePoint(i, { enabled: v })} />
                </div>
              </div>
            ))}
          </div>

          {unused.length > 0 && (
            <div className="mt-4">
              <Field label="Add another key moment from the video">
                <Select
                  value=""
                  onChange={(v) => v !== "" && addKeyPoint(parseInt(v, 10))}
                  options={[{ id: "", label: "Choose a moment…" }, ...unused.map((k, i) => ({ id: String(i), label: `${fmtTime(k.start)} · ${k.title}` }))]}
                />
              </Field>
            </div>
          )}
        </div>

        {/* Voice */}
        <Section title="Voice" icon={<Mic />} defaultOpen>
          <Chips options={options.voiceModes} value={settings.voice} onChange={(v) => set("voice", v as ReelSettings["voice"])} />
          <p className="text-[11px] text-slate-600">{options.voiceModes.find((m) => m.id === settings.voice)?.hint}</p>
          {settings.voice === "ai" && (
            <>
              <Field label="AI voice">
                <Select value={settings.ttsVoice} options={options.voices} onChange={(v) => set("ttsVoice", v)} />
              </Field>
              <Slider label="Speaking speed" value={settings.ttsRate} min={-30} max={40} step={5} onChange={(v) => set("ttsRate", v)} format={(v) => `${v > 0 ? "+" : ""}${v}%`} />
              <Slider label="Original audio underneath" value={settings.originalVolume} min={0} max={0.5} step={0.05} onChange={(v) => set("originalVolume", v)} format={(v) => `${Math.round(v * 100)}%`} />
            </>
          )}
        </Section>

        {/* Captions */}
        <Section title="Captions (font, colour, style)" icon={<Subtitles />} defaultOpen>
          <CaptionControls cfg={cap} onChange={setCap} options={options} onAssetsChanged={onAssetsChanged} />
        </Section>

        {/* Logo */}
        <Section title="Logo" icon={<ImageIcon />}>
          <LogoControls logo={settings.logo} onChange={(patch) => set("logo", { ...settings.logo, ...patch })} options={options} onAssetsChanged={onAssetsChanged} />
        </Section>

        {/* Transitions */}
        <Section title="Transitions" icon={<Wand2 />} defaultOpen>
          <p className="text-[11px] text-slate-600">Default between every point. You can override a single transition inside each point above.</p>
          {Object.entries(groupedTransitions).map(([group, list]) => (
            <Field key={group} label={group}>
              <Chips options={list} value={settings.transition} onChange={(v) => set("transition", v)} />
            </Field>
          ))}
          <Slider label="Transition length" value={settings.transitionDuration} min={0.2} max={1.5} step={0.1} onChange={(v) => set("transitionDuration", v)} format={(v) => `${v.toFixed(1)}s`} />
        </Section>

        {/* Look */}
        <Section title="Look & framing" icon={<Palette />}>
          <Field label="Colour look">
            <Chips options={options.filters} value={settings.filter} onChange={(v) => set("filter", v)} />
          </Field>
          <Field label="Shape">
            <Chips options={options.aspects} value={settings.aspect} onChange={(v) => set("aspect", v)} />
          </Field>
          <Field label="Framing" hint={options.framings.find((f) => f.id === settings.framing)?.hint}>
            <Chips options={options.framings} value={settings.framing} onChange={(v) => set("framing", v)} />
          </Field>
          {settings.framing === "crop" && (
            <div className="space-y-3">
              <Slider label="Zoom" value={settings.zoom} min={1} max={3} step={0.1} onChange={(v) => set("zoom", v)} format={(v) => `${v.toFixed(1)}×`} />
              <Slider label="Focus left ↔ right" value={settings.focusX} min={0} max={1} step={0.05} onChange={(v) => set("focusX", v)} format={(v) => `${Math.round(v * 100)}%`} />
              <Slider label="Focus top ↔ bottom" value={settings.focusY} min={0} max={1} step={0.05} onChange={(v) => set("focusY", v)} format={(v) => `${Math.round(v * 100)}%`} />
            </div>
          )}
          <Field label="Camera motion">
            <Chips options={options.motions} value={settings.motion} onChange={(v) => set("motion", v)} />
          </Field>
          <Slider label="Video speed" value={settings.speed} min={0.5} max={2} step={0.25} onChange={(v) => set("speed", v)} format={(v) => `${v}×`} />
          <Field label="Render quality">
            <Chips options={options.qualities} value={settings.quality} onChange={(v) => set("quality", v)} />
          </Field>
        </Section>

        {/* Extras */}
        <Section title="Extras" icon={<SlidersHorizontal />}>
          <Toggle label="Point titles" hint="Shows “1. Title” at the start of each point" value={settings.showTitles} onChange={(v) => set("showTitles", v)} />
          <Toggle label="Progress bar" value={settings.progressBar} onChange={(v) => set("progressBar", v)} />
          <Toggle label="Fit to target length" hint="Speeds up narration / trims points so the reel stays near the target" value={settings.fitToTarget} onChange={(v) => set("fitToTarget", v)} />
          <Slider label="Target length" value={settings.targetSeconds} min={15} max={90} step={5} onChange={(v) => set("targetSeconds", v)} format={(v) => `${v}s`} />
        </Section>
      </div>
    </div>
  );
};

export default ReelStudio;
