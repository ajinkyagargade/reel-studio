import React, { useState } from "react";
import { Sparkles, Loader2, Download } from "lucide-react";
import { createExplainer, errorMessage, getExplainerStatus, mediaUrl } from "../services/api";
import SetupBanner from "../components/SetupBanner";
import { ExplainerJob } from "../types";
import ProgressBar from "../components/ProgressBar";

const TopicExplainer: React.FC = () => {
  const [topic, setTopic] = useState("");
  const [job, setJob] = useState<ExplainerJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setError(null);
    setJob(null);

    try {
      const { id } = await createExplainer(topic.trim());
      const interval = setInterval(async () => {
        try {
          const status = await getExplainerStatus(id);
          setJob(status);
          if (status.status === "ready" || status.status === "failed") {
            clearInterval(interval);
            setLoading(false);
          }
        } catch {
          clearInterval(interval);
          setLoading(false);
          setError("Failed to get status");
        }
      }, 2500);
    } catch (err: any) {
      setError(errorMessage(err, "Failed to start generation"));
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="text-center mb-12 animate-fade-in-up">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-500/15 rounded-2xl mb-5 animate-float">
          <Sparkles className="w-8 h-8 text-indigo-400" />
        </div>
        <h1 className="text-3xl font-bold text-white mb-3">AI Topic Explainer</h1>
        <p className="text-slate-400">
          Type any technical topic and get a ready-to-post 45-second explainer
          video with animated code, voiceover and captions.
        </p>
      </div>

      <div className="mb-6"><SetupBanner need={["claude", "voice"]} /></div>
      <div className="glass-card rounded-3xl p-8 animate-fade-in-up delay-100">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Enter a topic
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. JSON vs XML, useEffect in React, Kubernetes Pods..."
          className="input-dark w-full px-4 py-3.5 text-lg"
          disabled={loading}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
        />

        <button
          onClick={handleGenerate}
          disabled={loading || !topic.trim()}
          className="btn-primary mt-5 w-full py-3.5 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate 45s Explainer
            </>
          )}
        </button>

        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm">
            {error}
          </div>
        )}

        {job && (
          <div className="mt-8 border-t border-white/5 pt-6 animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white">{job.topic}</h3>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                  job.status === "ready"
                    ? "bg-emerald-500/20 text-emerald-300"
                    : job.status === "failed"
                    ? "bg-red-500/20 text-red-300"
                    : "bg-amber-500/20 text-amber-300"
                }`}
              >
                {job.status}
              </span>
            </div>

            {job.status === "processing" && (
              <ProgressBar progress={job.progress} label={job.message || "Creating your explainer..."} />
            )}

            {job.status === "ready" && job.outputUrl && (
              <div className="space-y-4">
                <div className="aspect-[9/16] max-w-xs mx-auto bg-black rounded-2xl overflow-hidden border border-white/10">
                  <video src={mediaUrl(job.outputUrl)} controls className="w-full h-full object-contain" />
                </div>
                <a
                  href={mediaUrl(job.downloadUrl || job.outputUrl)}
                  className="btn-primary flex items-center justify-center gap-2 w-full py-3"
                >
                  <Download className="w-5 h-5" />
                  Download Video
                </a>
              </div>
            )}

            {job.status === "failed" && (
              <p className="text-sm text-red-400">{job.message || "Generation failed. Please try again."}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TopicExplainer;