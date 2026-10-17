import React, { useEffect, useState } from "react";
import { getHealth } from "../services/api";
import { Health } from "../types";
import { Banner } from "./ui";

/** Tells the user what is missing on the backend (ffmpeg, Whisper, Claude key, AI voice). */
const SetupBanner: React.FC<{ need?: ("whisper" | "claude" | "voice")[] }> = ({ need = ["whisper"] }) => {
  const [health, setHealth] = useState<Health | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setOffline(true));
  }, []);

  if (offline) {
    return (
      <Banner>
        The backend is not reachable. Start it with <code>uvicorn app.main:app --port 8000</code> inside the <code>backend</code> folder.
      </Banner>
    );
  }
  if (!health) return null;
  const problems: string[] = [];
  if (!health.ffmpeg) problems.push("ffmpeg is not installed (needed to read and render video).");
  if (need.includes("whisper") && !health.whisper) problems.push("faster-whisper is not installed: run pip install -r requirements.txt.");
  if (need.includes("voice") && !health.aiVoice) problems.push("edge-tts is not installed, so AI voice-over will fall back to the original audio.");
  if (need.includes("claude") && !health.claude) problems.push("Set ANTHROPIC_API_KEY in backend/.env to enable this feature.");
  if (!problems.length) return null;
  return (
    <Banner>
      <ul className="list-disc pl-5 space-y-1">
        {problems.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </Banner>
  );
};

export default SetupBanner;
