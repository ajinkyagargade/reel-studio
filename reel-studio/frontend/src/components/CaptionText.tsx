import React from "react";
import { ResolvedCaptionStyle } from "../utils/captionLayout";

interface Props {
  words: string[];
  activeIndex: number; // word currently spoken (-1 = none)
  style: ResolvedCaptionStyle;
  size: number; // user size multiplier
  height: number; // px height of the video area, drives the font size like the renderer does
}

/** One caption line in the exact look of the rendered video (font, colours, outline, box, highlight). */
const CaptionText: React.FC<Props> = ({ words, activeIndex, style, size, height }) => {
  const fs = Math.max(10, height * 0.075 * size);
  const stroke = Math.max(1, (style.outlineWidth * height) / 1080) * 2;
  const shown = (w: string) => (style.upper ? w.toUpperCase() : w);
  return (
    <div
      style={{
        fontFamily: `"${style.font}", sans-serif`,
        fontWeight: style.bold ? 700 : 400,
        fontSize: fs,
        lineHeight: 1.2,
        textAlign: "center",
        color: style.color,
        WebkitTextStroke: style.box ? undefined : `${stroke}px ${style.outline}`,
        paintOrder: "stroke fill",
        background: style.box ? `${style.outline}b3` : undefined,
        padding: style.box ? `${fs * 0.15}px ${fs * 0.35}px` : undefined,
        borderRadius: style.box ? fs * 0.2 : undefined,
        display: "inline-block",
        maxWidth: "100%",
      }}
    >
      {words.map((w, i) => {
        const active = i === activeIndex && style.mode !== "none";
        const sung = style.mode === "karaoke" && i <= activeIndex;
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              marginRight: i < words.length - 1 ? "0.28em" : 0,
              color: active || sung ? style.highlight : style.color,
              transform: active && style.mode === "word" ? "scale(1.14)" : "none",
              transition: "transform .08s, color .08s",
            }}
          >
            {shown(w)}
          </span>
        );
      })}
    </div>
  );
};

export default CaptionText;
