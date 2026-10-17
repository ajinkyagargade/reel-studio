"""ffmpeg / ffprobe helpers."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(path: Path) -> Dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {out.stderr.strip()[-300:]}")
    data = json.loads(out.stdout)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or (v or {}).get("duration") or (a or {}).get("duration") or 0)
    fps = 0.0
    if v and v.get("avg_frame_rate") and "/" in v["avg_frame_rate"]:
        n, d = v["avg_frame_rate"].split("/")
        fps = round(float(n) / float(d), 2) if float(d) else 0.0
    return {
        "duration": duration,
        "width": int(v["width"]) if v else 0,
        "height": int(v["height"]) if v else 0,
        "fps": fps,
        "videoCodec": v.get("codec_name") if v else None,
        "audioCodec": a.get("codec_name") if a else None,
        "hasAudio": a is not None,
        "hasVideo": v is not None,
        "sampleRate": int(a["sample_rate"]) if a and a.get("sample_rate") else None,
        "bitrate": int(fmt.get("bit_rate") or 0),
        "sizeBytes": int(fmt.get("size") or 0),
        "container": fmt.get("format_long_name"),
    }


def duration_of(path: Path) -> float:
    return probe(path)["duration"]


def run_ffmpeg(args: List[str], total_duration: Optional[float] = None,
               on_progress: Optional[Callable[[float], None]] = None, cwd: Optional[Path] = None) -> None:
    """Run ffmpeg; report progress 0..1 when total_duration is known."""
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-progress", "pipe:1", "-nostats", *args]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(cwd) if cwd else None)
    time_re = re.compile(r"out_time_us=(\d+)")
    assert proc.stdout is not None
    for line in proc.stdout:
        m = time_re.match(line.strip())
        if m and total_duration and on_progress:
            on_progress(min(1.0, int(m.group(1)) / 1e6 / total_duration))
    stderr = proc.stderr.read() if proc.stderr else ""
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.strip()[-1200:]}")


def extract_audio(src: Path, dst: Path) -> None:
    """16 kHz mono FLAC - what Whisper wants, and small."""
    run_ffmpeg(["-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", str(dst)])


def make_thumbnail(src: Path, dst: Path, at: float) -> None:
    run_ffmpeg(["-ss", f"{max(at, 0):.2f}", "-i", str(src), "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "3", str(dst)])
