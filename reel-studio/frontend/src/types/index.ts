export type VideoStatus = "uploaded" | "processing" | "ready" | "failed";

export interface VideoMetadata {
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  videoCodec?: string | null;
  audioCodec?: string | null;
  hasAudio?: boolean;
  sampleRate?: number | null;
  bitrate?: number;
  sizeBytes?: number;
  container?: string | null;
  fileName?: string;
  uploadedAt?: string;
}

export interface Video {
  id: string;
  filename: string;
  originalName: string;
  status: VideoStatus;
  progress: number;
  message?: string;
  duration?: number;
  createdAt: string;
  thumbnailUrl?: string;
  meta?: VideoMetadata;
  defaultReelId?: string;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  words: WordTimestamp[];
  segments: TranscriptSegment[];
  fullText: string;
  language?: string;
}

// ---------- video understanding ----------
export interface Chapter {
  title: string;
  start: number;
  end: number;
  summary: string;
}

export interface KeyPoint {
  title: string;
  summary: string;
  narration: string;
  start: number;
  end: number;
  importance: number;
}

export interface Analysis {
  source: "claude" | "local";
  note?: string;
  title: string;
  language: string;
  contentType: string;
  audience: string;
  difficulty: string;
  tldr: string;
  summary: string;
  keyTakeaways: string[];
  chapters: Chapter[];
  keyPoints: KeyPoint[];
  topics: string[];
  keywords: string[];
  glossary: { term: string; definition: string }[];
  quotes: { text: string; time: number }[];
  actionItems: string[];
  faq: { q: string; a: string }[];
  stats: {
    wordCount: number;
    sentenceCount: number;
    wordsPerMinute: number;
    speakingTimeSeconds: number;
    speakingPercent: number;
    estimatedReadMinutes: number;
  };
  metadata: VideoMetadata;
}

// ---------- reels ----------
export interface CaptionSettings {
  enabled: boolean;
  style: string;
  position: "top" | "middle" | "bottom";
  size: number;
  color: string | null;
  highlightColor: string | null;
  outlineColor: string | null;
  font: string | null;
  uppercase: boolean | null; // null = follow the style preset
  box: boolean | null;
}

export interface LogoSettings {
  id: string | null;
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";
  size: number; // fraction of video width
  opacity: number;
}

export interface CaptionStyleDef {
  id: string;
  label: string;
  font: string;
  bold: boolean;
  upper: boolean;
  mode: "word" | "karaoke" | "none";
  color: string;
  highlight: string;
  outline: string;
  outlineWidth: number;
  box: boolean;
  maxWords: number;
}

export interface FontInfo {
  family: string;
  label: string;
  builtin: boolean;
  file: string;
  url: string;
}

export interface LogoInfo {
  id: string;
  name: string;
  url: string;
}

export interface ReelSettings {
  targetSeconds: number;
  voice: "ai" | "original" | "none";
  ttsVoice: string;
  ttsRate: number;
  originalVolume: number;
  aspect: string;
  quality: string;
  framing: string;
  zoom: number;
  focusX: number;
  focusY: number;
  motion: string;
  filter: string;
  speed: number;
  transition: string;
  transitionDuration: number;
  captions: CaptionSettings;
  logo: LogoSettings;
  showTitles: boolean;
  progressBar: boolean;
  fitToTarget: boolean;
}

export interface ReelPoint {
  id: string;
  title: string;
  text: string;
  start: number;
  end: number;
  enabled: boolean;
  transition: string | null;
  customText: boolean;
  focusX?: number;
  focusY?: number;
  zoom?: number;
}

export type ReelStatus = "draft" | "rendering" | "ready" | "failed";

export interface Reel {
  id: string;
  videoId: string;
  status: ReelStatus;
  progress: number;
  message?: string;
  settings: ReelSettings;
  points: ReelPoint[];
  outputUrl: string | null;
  downloadUrl: string | null;
  duration: number | null;
  width?: number;
  height?: number;
  size?: number;
  stale: boolean;
  notes: string[];
  createdAt: string;
}

export interface Option {
  id: string;
  label: string;
  group?: string;
  hint?: string;
  lang?: string;
  highlight?: string;
  color?: string;
}

export interface EditOptions {
  transitions: Option[];
  filters: Option[];
  captionStyles: CaptionStyleDef[];
  captionPositions: string[];
  logoPositions: string[];
  fonts: FontInfo[];
  logos: LogoInfo[];
  aspects: string[];
  framings: Option[];
  motions: Option[];
  qualities: Option[];
  voiceModes: Option[];
  voices: Option[];
  defaults: ReelSettings;
}

export interface Health {
  ok: boolean;
  ffmpeg: boolean;
  whisper: boolean;
  whisperModel: string;
  claude: boolean;
  claudeModel: string | null;
  aiVoice: boolean;
}

// ---------- topic explainer ----------
export interface ExplainerSection {
  heading: string;
  body: string;
  code: string;
}

export interface Explanation {
  title: string;
  language: string;
  tldr: string;
  sections: ExplainerSection[];
  takeaways: string[];
}

export interface ExplainerReel {
  status: "processing" | "ready" | "failed";
  progress: number;
  message?: string;
  outputUrl?: string | null;
  downloadUrl?: string | null;
}

export interface ExplainerDoc {
  id: string;
  topic: string;
  status: "ready" | "failed";
  message?: string;
  explanation: Explanation;
  reel: ExplainerReel | null;
}

export interface CaptionedJob {
  status: "none" | "rendering" | "ready" | "failed";
  progress: number;
  message?: string;
  outputUrl?: string | null;
  downloadUrl?: string | null;
}
