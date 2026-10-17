import { CaptionSettings, CaptionStyleDef, WordTimestamp } from "../types";

export interface CaptionGroup {
  words: WordTimestamp[];
  start: number;
  end: number;
}

/** Same grouping rules as the backend renderer, so the live preview matches the final video. */
export const groupWords = (words: WordTimestamp[], maxWords: number, maxChars: number): CaptionGroup[] => {
  const groups: WordTimestamp[][] = [];
  let cur: WordTimestamp[] = [];
  for (const w of words) {
    const chars = cur.reduce((a, x) => a + x.word.length + 1, 0) + w.word.length;
    const gap = cur.length ? w.start - cur[cur.length - 1].end : 0;
    if (cur.length && (cur.length >= maxWords || chars > maxChars || gap > 0.7)) {
      groups.push(cur);
      cur = [];
    }
    cur.push(w);
    if (/[.?!]$/.test(w.word) && cur.length >= 2) {
      groups.push(cur);
      cur = [];
    }
  }
  if (cur.length) groups.push(cur);
  return groups.map((g, i) => {
    const next = groups[i + 1];
    const end = Math.min(g[g.length - 1].end + 0.25, next ? next[0].start : Infinity);
    return { words: g, start: g[0].start, end };
  });
};

/** Binary search for the group visible at time t (or null). */
export const findGroup = (groups: CaptionGroup[], t: number): CaptionGroup | null => {
  let lo = 0;
  let hi = groups.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (t < groups[mid].start) hi = mid - 1;
    else if (t >= groups[mid].end) lo = mid + 1;
    else return groups[mid];
  }
  return null;
};

export interface ResolvedCaptionStyle {
  font: string;
  bold: boolean;
  upper: boolean;
  box: boolean;
  color: string;
  highlight: string;
  outline: string;
  outlineWidth: number;
  mode: CaptionStyleDef["mode"];
  maxWords: number;
}

export const resolveStyle = (cfg: CaptionSettings, preset: CaptionStyleDef, fontIsBuiltin: boolean): ResolvedCaptionStyle => ({
  font: cfg.font || preset.font,
  bold: preset.bold && fontIsBuiltin,
  upper: cfg.uppercase ?? preset.upper,
  box: cfg.box ?? preset.box,
  color: cfg.color || preset.color,
  highlight: cfg.highlightColor || preset.highlight,
  outline: cfg.outlineColor || preset.outline,
  outlineWidth: Math.min(preset.outlineWidth, 6),
  mode: preset.mode,
  maxWords: preset.maxWords,
});
