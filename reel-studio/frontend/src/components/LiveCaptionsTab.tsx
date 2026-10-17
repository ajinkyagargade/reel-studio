import React, { useEffect, useState } from "react";
import { Download, FileText, Flame, Loader2, Save } from "lucide-react";
import { CaptionedJob, CaptionSettings, EditOptions, LogoSettings, Reel } from "../types";
import { captionFileUrl, errorMessage, getCaptioned, mediaUrl, saveReel, startCaptioned } from "../services/api";
import CaptionControls from "./CaptionControls";
import LogoControls from "./LogoControls";
import ProgressBar from "./ProgressBar";
import { Chips, Field } from "./ui";

interface Props {
  videoId: string;
  options: EditOptions;
  cfg: CaptionSettings;
  logo: LogoSettings;
  onCfg: (patch: Partial<CaptionSettings>) => void;
  onLogo: (patch: Partial<LogoSettings>) => void;
  onAssetsChanged: () => void;
  reel: Reel | null;
  onReelSaved: (r: Reel) => void;
  live: boolean;
  onLive: (v: boolean) => void;
}

/** Controls beside the source player: live caption style, downloads, burned-in full video, save to reel. */
const LiveCaptionsTab: React.FC<Props> = ({ videoId, options, cfg, logo, onCfg, onLogo, onAssetsChanged, reel, onReelSaved, live, onLive }) => {
  const [job, setJob] = useState<CaptionedJob>({ status: "none", progress: 0 });
  const [quality, setQuality] = useState("720p");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getCaptioned(videoId).then(setJob).catch(() => undefined);
  }, [videoId]);

  useEffect(() => {
    if (job.status !== "rendering") return;
    const t = setInterval(async () => {
      try {
        setJob(await getCaptioned(videoId));
      } catch {
        /* keep polling */
      }
    }, 1500);
    return () => clearInterval(t);
  }, [job.status, videoId]);

  const burn = async () => {
    setErr(null);
    try {
      setJob(await startCaptioned(videoId, { captions: cfg, logo, quality }));
    } catch (e) {
      setErr(errorMessage(e, "Could not start rendering"));
    }
  };

  const applyToReel = async () => {
    if (!reel) return;
    setErr(null);
    try {
      const r = await saveReel(reel.id, { settings: { ...reel.settings, captions: cfg, logo } });
      onReelSaved(r);
      setMsg("Saved. Open the Reel studio tab and re-render to see it in your reel.");
      setTimeout(() => setMsg(null), 5000);
    } catch (e) {
      setErr(errorMessage(e, "Could not save to the reel"));
    }
  };

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-2xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-white text-sm">Live captions</h3>
          <button
            onClick={() => onLive(!live)}
            className={`text-xs px-3 py-1.5 rounded-full border ${live ? "border-emerald-400 bg-emerald-500/20 text-emerald-200" : "border-white/10 text-slate-400"}`}
          >
            {live ? "● On – press play" : "Off"}
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Captions appear word by word over the video as it plays, using the transcript timing. Change the style below and watch the player update instantly.
        </p>
      </div>

      <div className="glass-card rounded-2xl p-5">
        <CaptionControls cfg={cfg} onChange={onCfg} options={options} onAssetsChanged={onAssetsChanged} />
      </div>

      <div className="glass-card rounded-2xl p-5 space-y-3">
        <h3 className="font-semibold text-white text-sm">Logo</h3>
        <LogoControls logo={logo} onChange={onLogo} options={options} onAssetsChanged={onAssetsChanged} />
        <p className="text-[11px] text-slate-600">The logo is added to reels and to the captioned full video, not to the live preview.</p>
      </div>

      <div className="glass-card rounded-2xl p-5 space-y-4">
        <h3 className="font-semibold text-white text-sm">Use these captions</h3>
        {reel && (
          <button onClick={applyToReel} className="btn-ghost w-full py-2.5 text-sm flex items-center justify-center gap-2">
            <Save className="w-4 h-4" /> Save style + logo to my reel
          </button>
        )}
        {msg && <p className="text-xs text-emerald-300">{msg}</p>}

        <div className="grid grid-cols-2 gap-3">
          <a href={captionFileUrl(videoId, "srt")} className="btn-ghost py-2.5 text-sm flex items-center justify-center gap-2">
            <FileText className="w-4 h-4" /> Download .srt
          </a>
          <a href={captionFileUrl(videoId, "vtt")} className="btn-ghost py-2.5 text-sm flex items-center justify-center gap-2">
            <FileText className="w-4 h-4" /> Download .vtt
          </a>
        </div>

        <div className="border-t border-white/5 pt-4 space-y-3">
          <p className="text-xs text-slate-400">Burn the styled captions (and logo) into the entire original video:</p>
          <Field label="Quality">
            <Chips options={options.qualities} value={quality} onChange={setQuality} />
          </Field>
          {job.status === "rendering" && <ProgressBar progress={job.progress} label={job.message || "Rendering…"} />}
          {job.status === "failed" && <p className="text-xs text-red-300 break-words">{job.message}</p>}
          {err && <p className="text-xs text-red-300">{err}</p>}
          <button onClick={burn} disabled={job.status === "rendering"} className="btn-primary w-full py-3 text-sm flex items-center justify-center gap-2 disabled:opacity-50">
            {job.status === "rendering" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Flame className="w-4 h-4" />}
            {job.status === "rendering" ? "Rendering…" : "Burn captions into full video"}
          </button>
          {job.status === "ready" && job.downloadUrl && (
            <a href={mediaUrl(job.downloadUrl)} className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-colors">
              <Download className="w-4 h-4" /> Download captioned video
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveCaptionsTab;
