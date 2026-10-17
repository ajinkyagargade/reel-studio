import React from "react";
import { useNavigate } from "react-router-dom";
import VideoUploader from "../components/VideoUploader";
import SetupBanner from "../components/SetupBanner";

const Upload: React.FC = () => {
  const navigate = useNavigate();

  const handleSuccess = (videoId: string) => {
    navigate("/dashboard");
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-12 animate-fade-in-up">
        <h1 className="text-3xl font-bold text-white mb-3">Upload Class Recording</h1>
        <p className="text-slate-400">
          Upload a long video. AI explains it, then turns its key points into a
          captioned, voiced 60-second reel you can edit.
        </p>
      </div>

      <div className="mb-6"><SetupBanner need={["whisper", "voice"]} /></div>
      <VideoUploader onSuccess={handleSuccess} />

      <div className="mt-12 glass-card rounded-2xl p-6 animate-fade-in-up delay-200">
        <h3 className="font-semibold text-white mb-4">What happens next?</h3>
        <ol className="space-y-3 text-sm text-slate-400">
          <li className="flex gap-3">
            <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold flex-shrink-0">1</span>
            We transcribe the audio with word-level timing (English, Hindi, Hinglish)
          </li>
          <li className="flex gap-3">
            <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold flex-shrink-0">2</span>
            AI writes a full explanation: summary, chapters, key points, glossary and more
          </li>
          <li className="flex gap-3">
            <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold flex-shrink-0">3</span>
            The key points become a ~60-second reel with AI voice-over and animated captions
          </li>
          <li className="flex gap-3">
            <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold flex-shrink-0">4</span>
            Edit points, transitions, captions, filters and framing, then download
          </li>
        </ol>
      </div>
    </div>
  );
};

export default Upload;