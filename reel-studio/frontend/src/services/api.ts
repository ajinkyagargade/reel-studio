import axios from "axios";
import {
  Video,
  Transcript,
  Analysis,
  Reel,
  ReelPoint,
  ReelSettings,
  EditOptions,
  Health,
  ExplainerDoc,
  FontInfo,
  LogoInfo,
  CaptionedJob,
  CaptionSettings,
  LogoSettings,
} from "../types";

export const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api";
// Origin of the backend, used to turn "/api/..." media paths into absolute URLs.
const API_ORIGIN = API_BASE.replace(/\/api\/?$/, "");

/** Absolute URL for a media path returned by the backend (e.g. "/api/reels/x/video"). */
export const mediaUrl = (path?: string | null): string => {
  if (!path) return "";
  return /^https?:\/\//.test(path) ? path : `${API_ORIGIN}${path}`;
};

const api = axios.create({ baseURL: API_BASE });

// Pull the FastAPI/Starlette-style {detail} message out of an error.
export const errorMessage = (err: any, fallback: string): string =>
  err?.response?.data?.detail || (err?.message === "Network Error" ? "Cannot reach the backend. Is it running on port 8000?" : fallback);

// ========== System ==========
export const getHealth = async (): Promise<Health> => (await api.get<Health>("/health")).data;
export const getOptions = async (): Promise<EditOptions> => (await api.get<EditOptions>("/options")).data;

// ========== Video APIs ==========
export const uploadVideo = async (file: File, onProgress?: (percent: number) => void, language = "auto") => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);

  const response = await api.post<{ id: string; message: string }>("/upload", formData, {
    onUploadProgress: (e) => {
      if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total));
    },
    timeout: 0,
  });
  return response.data;
};

export const getVideos = async (): Promise<Video[]> => (await api.get<Video[]>("/videos")).data;
export const getVideo = async (id: string): Promise<Video> => (await api.get<Video>(`/videos/${id}`)).data;
export const getVideoStatus = async (id: string): Promise<Video> => (await api.get<Video>(`/videos/${id}/status`)).data;
export const deleteVideo = async (id: string) => (await api.delete(`/videos/${id}`)).data;
export const getTranscript = async (videoId: string): Promise<Transcript> =>
  (await api.get<Transcript>(`/videos/${videoId}/transcript`)).data;
export const getAnalysis = async (videoId: string): Promise<Analysis> =>
  (await api.get<Analysis>(`/videos/${videoId}/analysis`)).data;
export const videoStreamUrl = (videoId: string) => mediaUrl(`/api/videos/${videoId}/stream`);

// ========== Reel APIs ==========
export const getReels = async (videoId: string): Promise<Reel[]> => (await api.get<Reel[]>(`/videos/${videoId}/reels`)).data;
export const createReel = async (
  videoId: string,
  body: { targetSeconds?: number; numPoints?: number; settings?: Partial<ReelSettings>; render?: boolean }
): Promise<Reel> => (await api.post<Reel>(`/videos/${videoId}/reels`, body)).data;
export const getReel = async (reelId: string): Promise<Reel> => (await api.get<Reel>(`/reels/${reelId}`)).data;
export const saveReel = async (reelId: string, body: { points?: ReelPoint[]; settings?: ReelSettings }): Promise<Reel> =>
  (await api.put<Reel>(`/reels/${reelId}`, body)).data;
export const replanReel = async (reelId: string, body: { targetSeconds?: number; numPoints?: number }): Promise<Reel> =>
  (await api.post<Reel>(`/reels/${reelId}/replan`, body)).data;
export const renderReel = async (reelId: string, body?: { points?: ReelPoint[]; settings?: ReelSettings }): Promise<Reel> =>
  (await api.post<Reel>(`/reels/${reelId}/render`, body || {})).data;
export const deleteReel = async (reelId: string) => (await api.delete(`/reels/${reelId}`)).data;

// ========== Fonts, logos, live captions ==========
const uploadForm = (file: File) => {
  const f = new FormData();
  f.append("file", file);
  return f;
};
export const getFonts = async (): Promise<FontInfo[]> => (await api.get<FontInfo[]>("/fonts")).data;
export const uploadFont = async (file: File): Promise<FontInfo> => (await api.post<FontInfo>("/fonts", uploadForm(file))).data;
export const getLogos = async (): Promise<LogoInfo[]> => (await api.get<LogoInfo[]>("/logos")).data;
export const uploadLogo = async (file: File): Promise<LogoInfo> => (await api.post<LogoInfo>("/logos", uploadForm(file))).data;
export const deleteLogo = async (id: string) => (await api.delete(`/logos/${id}`)).data;
export const captionFileUrl = (videoId: string, fmt: "srt" | "vtt") => mediaUrl(`/api/videos/${videoId}/captions/${fmt}?download=1`);
export const startCaptioned = async (
  videoId: string,
  settings: { captions: CaptionSettings; logo: LogoSettings; quality: string }
): Promise<CaptionedJob> => (await api.post<CaptionedJob>(`/videos/${videoId}/captioned`, { settings })).data;
export const getCaptioned = async (videoId: string): Promise<CaptionedJob> =>
  (await api.get<CaptionedJob>(`/videos/${videoId}/captioned`)).data;

// ========== Topic Explainer APIs ==========
/** Step 1: full explanation of the user's text (takes a few seconds). */
export const createExplainer = async (text: string): Promise<ExplainerDoc> =>
  (await api.post<ExplainerDoc>("/explainer", { text })).data;
/** Step 2 (optional): start making a reel from that explanation. */
export const startExplainerReel = async (id: string): Promise<ExplainerDoc> =>
  (await api.post<ExplainerDoc>(`/explainer/${id}/reel`)).data;
export const getExplainer = async (id: string): Promise<ExplainerDoc> =>
  (await api.get<ExplainerDoc>(`/explainer/${id}`)).data;

export default api;
