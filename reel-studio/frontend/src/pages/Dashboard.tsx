import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, RefreshCw, FolderOpen } from "lucide-react";
import { getVideos } from "../services/api";
import { Video } from "../types";
import VideoCard from "../components/VideoCard";

const Dashboard: React.FC = () => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVideos = async () => {
    try {
      setError(null);
      const data = await getVideos();
      setVideos(data);
    } catch (err) {
      setError("Failed to load videos. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVideos();
    const interval = setInterval(() => {
      setVideos((prev) => {
        const hasProcessing = prev.some((v) => v.status === "processing" || v.status === "uploaded");
        if (hasProcessing) fetchVideos();
        return prev;
      });
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-slate-400 mt-1">All your class recordings and generated reels</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchVideos}
            className="btn-ghost flex items-center gap-2 px-4 py-2.5 text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <Link to="/upload" className="btn-primary flex items-center gap-2 px-5 py-2.5 text-sm">
            <Plus className="w-4 h-4" />
            New Project
          </Link>
        </div>
      </div>

      {loading && (
        <div className="text-center py-24 text-slate-500">Loading projects...</div>
      )}

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl mb-6">
          {error}
        </div>
      )}

      {!loading && !error && videos.length === 0 && (
        <div className="text-center py-24 glass-card rounded-3xl">
          <FolderOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 mb-6">No projects yet</p>
          <Link to="/upload" className="btn-primary inline-flex items-center gap-2 px-6 py-3">
            <Plus className="w-4 h-4" />
            Create your first project
          </Link>
        </div>
      )}

      {!loading && videos.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map((video, i) => (
            <div key={video.id} style={{ animationDelay: `${i * 0.08}s` }}>
              <VideoCard video={video} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;