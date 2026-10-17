import React, { useEffect, useMemo, useRef, useState } from "react";
import { CaptionSettings, CaptionStyleDef, FontInfo, WordTimestamp } from "../types";
import { findGroup, groupWords, resolveStyle } from "../utils/captionLayout";
import CaptionText from "./CaptionText";

interface Props {
  words: WordTimestamp[];
  getTime: () => number; // current playback time of the player
  cfg: CaptionSettings;
  presets: CaptionStyleDef[];
  fonts: FontInfo[];
  enabled: boolean;
}

/** Real-time captions drawn over the player. Updates ~30x/second from the playback clock. */
const LiveCaptionOverlay: React.FC<Props> = ({ words, getTime, cfg, presets, fonts, enabled }) => {
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 640, h: 360 });
  const [t, setT] = useState(0);

  const preset = presets.find((p) => p.id === cfg.style) || presets[0];
  const font = fonts.find((f) => f.family === (cfg.font || preset.font));
  const style = resolveStyle(cfg, preset, !!font?.builtin);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let raf = 0;
    let last = -1;
    const tick = () => {
      const now = getTime();
      if (Math.abs(now - last) > 0.03) {
        last = now;
        setT(now);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [enabled, getTime]);

  const fs = size.h * 0.075 * cfg.size;
  const maxChars = Math.max(12, Math.floor((2 * size.w * 0.86) / (fs * 0.62)));
  const groups = useMemo(() => groupWords(words, style.maxWords, maxChars), [words, style.maxWords, maxChars]);
  const group = enabled && cfg.enabled ? findGroup(groups, t) : null;
  const active = group ? group.words.findIndex((w, i) => t >= w.start && (i + 1 >= group.words.length || t < group.words[i + 1].start)) : -1;

  const place =
    cfg.position === "top"
      ? { top: "12%" }
      : cfg.position === "middle"
      ? { top: "50%", transform: "translateY(-50%)" }
      : { bottom: size.h > size.w ? "20%" : "8%" };

  return (
    <div ref={box} className="absolute inset-0 pointer-events-none overflow-hidden" aria-live="polite">
      {group && (
        <div className="absolute inset-x-0 flex justify-center px-[7%]" style={place as React.CSSProperties}>
          <CaptionText words={group.words.map((w) => w.word)} activeIndex={active} style={style} size={cfg.size} height={size.h} />
        </div>
      )}
    </div>
  );
};

export default LiveCaptionOverlay;
