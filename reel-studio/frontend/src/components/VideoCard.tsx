import React from "react";
import { Link } from "react-router-dom";
import { Film, Clock, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Video } from "../types";
import ProgressBar from "./ProgressBar";
import { cn } from "../utils/cn";

interface VideoCardProps {
  video: Video;
}

const statusConfig = {
  uploaded: { label: "Uploaded", color: "bg-slate-500/20 text-slate-300", icon: Film },
  processing: { label: "Processing", color: "bg-amber-500/20 text-amber-300", icon: Loader2 },
  ready: { label: "Ready", color: "bg-emerald-500/20 text-emerald-300", icon: CheckCircle },
  failed: { label: "Failed", color: "bg-red-500/20 text-red-300", icon: AlertCircle },
};

const VideoCard: React.FC<VideoCardProps> = ({ video }) => {
  const config = statusConfig[video.status];
  const Icon = config.icon;

  return (
    <div className="glass-card rounded-2xl overflow-hidden hover:border-indigo-500/30 transition-all duration-500 hover:-translate-y-1 hover:shadow-glow group animate-fade-in-up">
      <div className="aspect-video bg-dark-200 flex items-center justify-center relative overflow-hidden">
        {video.thumbnailUrl ? (
          <img src={video.thumbnailUrl} alt={video.originalName} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
        ) : (
          <Film className="w-12 h-12 text-slate-600" />
        )}
        <div className={cn("absolute top-3 right-3 px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 backdrop-blur-md", config.color)}>
          <Icon className={cn("w-3.5 h-3.5", video.status === "processing" && "animate-spin")} />
          {config.label}
        </div>
      </div>

      <div className="p-5">
        <h3 className="font-semibold text-white truncate mb-1">{video.originalName}</h3>
        <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
          <Clock className="w-4 h-4" />
          <span>{new Date(video.createdAt).toLocaleString()}</span>
        </div>

        {video.status === "processing" && (
          <ProgressBar progress={video.progress} label={video.message || "Processing..."} className="mb-4" />
        )}

        {video.status === "ready" && (
          <Link
            to={`/editor/${video.id}`}
            className="btn-primary block w-full text-center py-2.5 text-sm"
          >
            Open workspace
          </Link>
        )}

        {video.status === "failed" && (
          <p className="text-sm text-red-400">{video.message || "Something went wrong"}</p>
        )}
      </div>
    </div>
  );
};

export default VideoCard;