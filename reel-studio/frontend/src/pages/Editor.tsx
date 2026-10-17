import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import ReactPlayer from "react-player";
import { ArrowLeft, FileText, Loader2, Plus, Scissors, Sparkles, Subtitles } from "lucide-react";
import {
  createReel,
  errorMessage,
  getAnalysis,
  getFonts,
  getLogos,
  getOptions,
  getReels,
  getTranscript,
  getVideo,
  videoStreamUrl,
} from "../services/api";
import { Analysis, CaptionSettings, EditOptions, LogoSettings, Reel, Transcript, Video } from "../types";
import LiveCaptionOverlay from "../components/LiveCaptionOverlay";
import LiveCaptionsTab from "../components/LiveCaptionsTab";
import { useFontFaces } from "../hooks/useFontFaces";
import OverviewTab from "../components/OverviewTab";
import ReelStudio from "../components/ReelStudio";
import { cn } from "../utils/cn";
import { fmtTime } from "../utils/format";

type Tab = "overview" | "studio" | "live" | "transcript";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "overview", label: "Video explained", icon: <FileText className="w-4 h-4" /> },
  { id: "studio", label: "Reel studio", icon: <Scissors className="w-4 h-4" /> },
  { id: "live", label: "Live captions", icon: <Subtitles className="w-4 h-4" /> },
  { id: "transcript", label: "Transcript", icon: <Sparkles className="w-4 h-4" /> },
];

const Editor: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [reels, setReels] = useState<Reel[]>([]);
  const [activeReelId, setActiveReelId] = useState<string | null>(null);
  const [options, setOptions] = useState<EditOptions | null>(null);
  const [tab, setTab] = useState<Tab>("studio");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const player = useRef<ReactPlayer>(null);
  const [live, setLive] = useState(true);
  const [capCfg, setCapCfg] = useState<CaptionSettings | null>(null);
  const [logoCfg, setLogoCfg] = useState<LogoSettings | null>(null);
  useFontFaces(options?.fonts || []);
  const getTime = useCallback(() => player.current?.getCurrentTime() ?? 0, []);
  const refreshAssets = useCallback(async () => {
    const [fonts, logos] = await Promise.all([getFonts(), getLogos()]);
    setOptions((o) => (o ? { ...o, fonts, logos } : o));
  }, []);

  const load = useCallback(async () => {
    if (!videoId) return;
    try {
      setError(null);
      const [v, a, opts, rs, t] = await Promise.all([
        getVideo(videoId),
        getAnalysis(videoId),
        getOptions(),
        getReels(videoId),
        getTranscript(videoId).catch(() => null),
      ]);
      setVideo(v);
      setAnalysis(a);
      setOptions(opts);
      setReels(rs);
      setTranscript(t);
      setActiveReelId((cur) => cur || v.defaultReelId || rs[rs.length - 1]?.id || null);
    } catch (err) {
      setError(errorMessage(err, "Failed to load this video. Is it still processing?"));
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    load();
  }, [load]);

  const seek = (seconds: number) => {
    player.current?.seekTo(seconds, "seconds");
    if (tab === "studio") return;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // The live caption style starts from the active reel's settings.
  useEffect(() => {
    const r = reels.find((x) => x.id === activeReelId);
    const base = r?.settings || options?.defaults;
    if (base) {
      setCapCfg(base.captions);
      setLogoCfg(base.logo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeReelId, !!options]);

  const updateReel = (r: Reel) => setReels((prev) => prev.map((x) => (x.id === r.id ? r : x)));

  const makeReel = async () => {
    if (!videoId) return;
    setCreating(true);
    try {
      const r = await createReel(videoId, { targetSeconds: 60 });
      setReels((prev) => [...prev, r]);
      setActiveReelId(r.id);
      setTab("studio");
    } catch (err) {
      setError(errorMessage(err, "Could not create a reel"));
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32 text-slate-500">
        <Loader2 className="w-6 h-6 animate-spin mr-2 text-indigo-400" />
        Loading workspace...
      </div>
    );
  }

  if (error || !video || !analysis || !options) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 mb-4">{error || "Video not found"}</p>
        <Link to="/dashboard" className="text-indigo-400 hover:underline">
          Back to Projects
        </Link>
      </div>
    );
  }

  const activeReel = reels.find((r) => r.id === activeReelId) || null;

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link to="/dashboard" className="p-2.5 rounded-xl glass hover:bg-white/10 text-slate-400 hover:text-white transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-white truncate">{analysis.title || video.originalName}</h1>
          <p className="text-sm text-slate-500 truncate">
            {video.originalName} · {fmtTime(video.duration || 0)}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all",
              tab === t.id ? "bg-indigo-500/20 text-white border border-indigo-400/40" : "glass text-slate-400 hover:text-white"
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* The source player stays mounted so seeking works from every tab */}
      <div className={cn(tab === "studio" ? "hidden" : "grid lg:grid-cols-5 gap-6")}>
        <div className="lg:col-span-2">
          <div className="lg:sticky lg:top-28 glass-card rounded-2xl overflow-hidden">
            <div className="aspect-video bg-black">
              <div className="relative w-full h-full">
                <ReactPlayer ref={player} url={videoStreamUrl(video.id)} width="100%" height="100%" controls />
                {tab === "live" && capCfg && (
                  <LiveCaptionOverlay
                    words={transcript?.words || []}
                    getTime={getTime}
                    cfg={capCfg}
                    presets={options.captionStyles}
                    fonts={options.fonts}
                    enabled={live}
                  />
                )}
              </div>
            </div>
            <p className="text-[11px] text-slate-500 px-4 py-2.5">Source video · click any timestamp to jump here</p>
          </div>
        </div>
        <div className="lg:col-span-3">
          {tab === "overview" && <OverviewTab analysis={analysis} onSeek={seek} />}
          {tab === "live" && capCfg && logoCfg && (
            <LiveCaptionsTab
              videoId={video.id}
              options={options}
              cfg={capCfg}
              logo={logoCfg}
              onCfg={(p) => setCapCfg((c) => (c ? { ...c, ...p } : c))}
              onLogo={(p) => setLogoCfg((l) => (l ? { ...l, ...p } : l))}
              onAssetsChanged={refreshAssets}
              reel={activeReel}
              onReelSaved={updateReel}
              live={live}
              onLive={setLive}
            />
          )}
          {tab === "transcript" && (
            <div className="glass-card rounded-2xl p-5">
              <h3 className="font-semibold text-white mb-4 text-sm">Transcript ({transcript?.language || analysis.language})</h3>
              {transcript && transcript.segments.length > 0 ? (
                <div className="space-y-1 max-h-[70vh] overflow-y-auto pr-2">
                  {transcript.segments.map((s, i) => (
                    <button key={i} onClick={() => seek(s.start)} className="w-full text-left flex gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
                      <span className="text-xs text-indigo-300 w-12 shrink-0 pt-0.5">{fmtTime(s.start)}</span>
                      <span className="text-sm text-slate-300">{s.text}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">{transcript?.fullText || "Transcript is not available."}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {tab === "studio" && (
        <>
          {/* Reel versions */}
          <div className="flex items-center gap-2 mb-5 overflow-x-auto">
            {reels.map((r, i) => (
              <button
                key={r.id}
                onClick={() => setActiveReelId(r.id)}
                className={cn(
                  "px-3.5 py-1.5 rounded-full text-xs border whitespace-nowrap",
                  r.id === activeReelId ? "border-indigo-400 bg-indigo-500/20 text-white" : "border-white/10 text-slate-400 hover:text-white"
                )}
              >
                Reel {i + 1}
                {r.status === "rendering" ? " · rendering" : r.status === "ready" ? " · ready" : ""}
              </button>
            ))}
            <button onClick={makeReel} disabled={creating} className="px-3.5 py-1.5 rounded-full text-xs border border-dashed border-white/20 text-slate-400 hover:text-white flex items-center gap-1 disabled:opacity-50">
              {creating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />} New version
            </button>
          </div>

          {activeReel ? (
            <ReelStudio
              key={activeReel.id}
              video={video}
              analysis={analysis}
              options={options}
              reel={activeReel}
              onReel={updateReel}
              onAssetsChanged={refreshAssets}
              onSeekSource={(t) => {
                setTab("overview");
                setTimeout(() => seek(t), 50);
              }}
            />
          ) : (
            <div className="glass-card rounded-2xl p-12 text-center">
              <p className="text-slate-400 mb-5">No reel yet for this video.</p>
              <button onClick={makeReel} disabled={creating} className="btn-primary px-8 py-3 inline-flex items-center gap-2">
                {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Create 60-second reel
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Editor;
