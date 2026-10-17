import React, { useCallback, useEffect, useRef, useState } from "react";
import { Sparkles, Loader2, Download, Film, RotateCcw } from "lucide-react";
import { createExplainer, errorMessage, getExplainer, mediaUrl, startExplainerReel } from "../services/api";
import SetupBanner from "../components/SetupBanner";
import ProgressBar from "../components/ProgressBar";
import { ExplainerDoc } from "../types";

const MAX_CHARS = 6000;
const POLL_MS = 2500;

const TopicExplainer: React.FC = () => {
  const [text, setText] = useState("");
  const [doc, setDoc] = useState<ExplainerDoc | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reelError, setReelError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]); // no leaked interval when leaving the page

  const pollReel = useCallback(
    (id: string) => {
      stopPolling();
      timer.current = setInterval(async () => {
        try {
          const latest = await getExplainer(id);
          setDoc(latest);
          if (latest.reel?.status !== "processing") stopPolling();
        } catch (err: any) {
          stopPolling();
          setReelError(errorMessage(err, "Lost track of the reel. Please try again."));
        }
      }, POLL_MS);
    },
    [stopPolling]
  );

  const handleExplain = async () => {
    const value = text.trim();
    if (!value || explaining) return;
    stopPolling();
    setExplaining(true);
    setError(null);
    setReelError(null);
    setDoc(null);
    try {
      setDoc(await createExplainer(value));
    } catch (err: any) {
      setError(errorMessage(err, "Could not generate the explanation. Please try again."));
    } finally {
      setExplaining(false);
    }
  };

  const handleMakeReel = async () => {
    if (!doc) return;
    setReelError(null);
    try {
      const started = await startExplainerReel(doc.id);
      setDoc(started);
      pollReel(doc.id);
    } catch (err: any) {
      setReelError(errorMessage(err, "Could not start the reel. Please try again."));
    }
  };

  const reset = () => {
    stopPolling();
    setDoc(null);
    setError(null);
    setReelError(null);
  };

  const explanation = doc?.explanation;
  const reel = doc?.reel;
  const reelBusy = reel?.status === "processing";

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-10 animate-fade-in-up">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-500/15 rounded-2xl mb-5 animate-float">
          <Sparkles className="w-8 h-8 text-indigo-400" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-3">AI Explainer</h1>
        <p className="text-slate-400">
          Paste a topic, a question or any text. Get a complete explanation, then turn it into a reel if you want one.
        </p>
      </div>

      <div className="mb-6">
        <SetupBanner need={["claude"]} />
      </div>

      <div className="glass-card rounded-3xl p-8 animate-fade-in-up delay-100">
        <label htmlFor="explain-text" className="block text-sm font-medium text-slate-300 mb-2">
          What should I explain?
        </label>
        <textarea
          id="explain-text"
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
          placeholder="e.g. How does useEffect work in React? or paste a paragraph you want explained..."
          rows={5}
          className="input-dark w-full px-4 py-3.5 text-base resize-y"
          disabled={explaining}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleExplain();
          }}
        />
        <div className="flex justify-between text-xs text-slate-500 mt-1.5">
          <span>Ctrl/Cmd + Enter to explain</span>
          <span>
            {text.length}/{MAX_CHARS}
          </span>
        </div>

        <button
          onClick={handleExplain}
          disabled={explaining || !text.trim()}
          className="btn-primary mt-5 w-full py-3.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {explaining ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Writing your explanation...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Explain
            </>
          )}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm">{error}</div>
        )}
      </div>

      {explanation && doc && (
        <div className="glass-card rounded-3xl p-8 mt-6 animate-scale-in">
          <div className="flex items-start justify-between gap-4 mb-2">
            <h2 className="text-2xl font-bold text-white">{explanation.title}</h2>
            <button
              onClick={reset}
              className="btn-ghost inline-flex items-center gap-1.5 px-3 py-1.5 text-sm shrink-0"
              title="Clear and start over"
            >
              <RotateCcw className="w-4 h-4" /> Clear
            </button>
          </div>
          {explanation.tldr && <p className="text-indigo-200 mb-6">{explanation.tldr}</p>}

          <div className="space-y-6">
            {explanation.sections.map((s, i) => (
              <section key={i}>
                {s.heading && <h3 className="font-semibold text-white mb-2">{s.heading}</h3>}
                {s.body.split(/\n{2,}/).map((para, j) => (
                  <p key={j} className="text-slate-300 leading-relaxed mb-3 whitespace-pre-line">
                    {para}
                  </p>
                ))}
                {s.code && (
                  <pre className="bg-black/40 border border-white/10 rounded-xl p-4 text-sm text-slate-200 overflow-x-auto">
                    <code>{s.code}</code>
                  </pre>
                )}
              </section>
            ))}
          </div>

          {explanation.takeaways.length > 0 && (
            <div className="mt-8 border-t border-white/5 pt-6">
              <h3 className="font-semibold text-white mb-3">Key takeaways</h3>
              <ul className="list-disc pl-5 space-y-1.5 text-slate-300">
                {explanation.takeaways.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-8 border-t border-white/5 pt-6">
            {!reel && (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <p className="text-slate-400 text-sm">Want this as a short vertical video with voice-over and captions?</p>
                <button onClick={handleMakeReel} className="btn-primary px-6 py-3 flex items-center justify-center gap-2 shrink-0">
                  <Film className="w-5 h-5" />
                  Make a reel
                </button>
              </div>
            )}

            {reelBusy && <ProgressBar progress={reel?.progress ?? 0} label={reel?.message || "Making your reel..."} />}

            {reel?.status === "failed" && (
              <div className="space-y-3">
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm">
                  {reel.message || "The reel could not be made."}
                </div>
                <button onClick={handleMakeReel} className="btn-primary px-6 py-3 flex items-center justify-center gap-2">
                  <Film className="w-5 h-5" />
                  Try again
                </button>
              </div>
            )}

            {reel?.status === "ready" && reel.outputUrl && (
              <div className="space-y-4">
                <div className="aspect-[9/16] max-w-xs mx-auto bg-black rounded-2xl overflow-hidden border border-white/10">
                  <video src={mediaUrl(reel.outputUrl)} controls className="w-full h-full object-contain" />
                </div>
                <a
                  href={mediaUrl(reel.downloadUrl || reel.outputUrl)}
                  className="btn-primary flex items-center justify-center gap-2 w-full py-3"
                >
                  <Download className="w-5 h-5" />
                  Download reel
                </a>
              </div>
            )}

            {reelError && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm">{reelError}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TopicExplainer;
