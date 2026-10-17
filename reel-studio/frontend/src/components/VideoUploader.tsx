import React, { useState, useRef } from "react";
import { Film, X, UploadCloud } from "lucide-react";
import { errorMessage, uploadVideo } from "../services/api";
import ProgressBar from "./ProgressBar";
import { cn } from "../utils/cn";

interface VideoUploaderProps {
  onSuccess: (videoId: string) => void;
}

const VideoUploader: React.FC<VideoUploaderProps> = ({ onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [language, setLanguage] = useState("auto");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (selected: File | null) => {
    if (!selected) return;
    if (!selected.type.startsWith("video/")) {
      setError("Please select a valid video file");
      return;
    }
    setFile(selected);
    setError(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const result = await uploadVideo(file, setProgress, language);
      onSuccess(result.id);
    } catch (err: any) {
      setError(errorMessage(err, "Upload failed. Please try again."));
    } finally {
      setUploading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setProgress(0);
    setError(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="w-full max-w-2xl mx-auto animate-fade-in-up">
      <div
        className={cn(
          "glass-card rounded-3xl p-12 text-center transition-all duration-500",
          dragActive && "border-indigo-500/50 shadow-glow scale-[1.02]",
          file && "border-indigo-500/30"
        )}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        {!file ? (
          <>
            <div className="mx-auto w-20 h-20 bg-indigo-500/15 rounded-2xl flex items-center justify-center mb-6 animate-float">
              <UploadCloud className="w-10 h-10 text-indigo-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Drop your class recording here
            </h3>
            <p className="text-slate-400 mb-8">
              or click to browse • MP4, MOV, WebM supported
            </p>
            <button
              onClick={() => inputRef.current?.click()}
              className="btn-primary px-8 py-3"
            >
              Select Video
            </button>
            <input
              ref={inputRef}
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0] || null)}
            />
          </>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-center gap-4">
              <div className="w-14 h-14 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                <Film className="w-7 h-7 text-indigo-400" />
              </div>
              <div className="text-left">
                <p className="font-medium text-white truncate max-w-xs">{file.name}</p>
                <p className="text-sm text-slate-400">
                  {(file.size / (1024 * 1024)).toFixed(1)} MB
                </p>
              </div>
              {!uploading && (
                <button
                  onClick={clearFile}
                  className="ml-2 p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {!uploading && (
              <div className="max-w-xs mx-auto text-left">
                <label className="block text-xs text-slate-500 mb-1.5">Spoken language</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)} className="input-dark w-full px-3 py-2.5 text-sm">
                  <option value="auto" className="bg-slate-900">Auto-detect</option>
                  <option value="en" className="bg-slate-900">English</option>
                  <option value="hi" className="bg-slate-900">Hindi (Devanagari)</option>
                  <option value="hinglish" className="bg-slate-900">Hinglish (Hindi + English, Latin script)</option>
                </select>
              </div>
            )}

            {uploading && <ProgressBar progress={progress} label="Uploading..." />}

            {!uploading && (
              <button onClick={handleUpload} className="btn-primary px-10 py-3">
                Start Processing
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm animate-scale-in">
          {error}
        </div>
      )}
    </div>
  );
};

export default VideoUploader;