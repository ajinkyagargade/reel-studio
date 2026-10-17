import { useEffect } from "react";
import { FontInfo } from "../types";
import { mediaUrl } from "../services/api";

/** Registers every backend font with the browser so the live preview uses the exact caption font. */
export const useFontFaces = (fonts: FontInfo[]) => {
  useEffect(() => {
    let el = document.getElementById("rs-caption-fonts") as HTMLStyleElement | null;
    if (!el) {
      el = document.createElement("style");
      el.id = "rs-caption-fonts";
      document.head.appendChild(el);
    }
    el.textContent = fonts
      .map((f) => `@font-face{font-family:"${f.family}";src:url("${mediaUrl(f.url)}");font-weight:100 900;font-display:swap;}`)
      .join("\n");
  }, [fonts]);
};
