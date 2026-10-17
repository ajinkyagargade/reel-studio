import React from "react";
import { Clock, Film, Gauge, HelpCircle, ListChecks, Quote, BookOpen, Hash, FileText, Info, Play } from "lucide-react";
import { Analysis } from "../types";
import { fmtBytes, fmtTime } from "../utils/format";

interface Props {
  analysis: Analysis;
  onSeek: (seconds: number) => void;
}

const Card: React.FC<{ title: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, icon, children }) => (
  <div className="glass-card rounded-2xl p-5">
    <h3 className="flex items-center gap-2 font-semibold text-white text-sm mb-3">
      <span className="text-indigo-400 [&>svg]:w-4 [&>svg]:h-4">{icon}</span>
      {title}
    </h3>
    {children}
  </div>
);

const Stat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-xl bg-white/5 px-3 py-2.5">
    <div className="text-[11px] text-slate-500">{label}</div>
    <div className="text-sm font-medium text-white mt-0.5 truncate">{value}</div>
  </div>
);

const TimeLink: React.FC<{ t: number; onSeek: (s: number) => void }> = ({ t, onSeek }) => (
  <button
    onClick={() => onSeek(t)}
    className="inline-flex items-center gap-1 text-xs text-indigo-300 hover:text-white bg-indigo-500/10 hover:bg-indigo-500/25 rounded-md px-1.5 py-0.5 transition-colors"
  >
    <Play className="w-3 h-3" />
    {fmtTime(t)}
  </button>
);

const OverviewTab: React.FC<Props> = ({ analysis: a, onSeek }) => {
  const m = a.metadata || {};
  const res = m.width && m.height ? `${m.width}×${m.height}` : "–";
  return (
    <div className="space-y-5">
      {a.note && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs">{a.note}</div>
      )}

      {/* Headline */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {a.contentType && <span className="text-[11px] px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300">{a.contentType}</span>}
          {a.difficulty && <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-300">{a.difficulty}</span>}
          {a.language && <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/10 text-slate-300">{a.language}</span>}
          <span className="text-[11px] px-2.5 py-1 rounded-full bg-white/5 text-slate-500">
            {a.source === "claude" ? "Written by Claude" : "Local analysis"}
          </span>
        </div>
        <h2 className="text-xl font-bold text-white mb-2">{a.title}</h2>
        {a.tldr && <p className="text-indigo-200 text-sm leading-relaxed mb-4">{a.tldr}</p>}
        {a.audience && <p className="text-xs text-slate-500">Best for: {a.audience}</p>}
      </div>

      {/* Brief explanation */}
      <Card title="Explanation of the video" icon={<FileText />}>
        <div className="space-y-3 text-sm text-slate-300 leading-relaxed">
          {a.summary.split(/\n\n+/).map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </Card>

      {a.keyTakeaways.length > 0 && (
        <Card title="Key takeaways" icon={<ListChecks />}>
          <ul className="space-y-2">
            {a.keyTakeaways.map((t, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 text-[11px] flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                {t}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Chapters */}
      {a.chapters.length > 0 && (
        <Card title="Chapters" icon={<Clock />}>
          <div className="space-y-2">
            {a.chapters.map((c, i) => (
              <div key={i} className="rounded-xl border border-white/5 hover:border-white/15 p-3 transition-colors">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-white">{c.title}</span>
                  <TimeLink t={c.start} onSeek={onSeek} />
                </div>
                {c.summary && <p className="text-xs text-slate-500 mt-1.5">{c.summary}</p>}
                <p className="text-[11px] text-slate-600 mt-1">
                  {fmtTime(c.start)} – {fmtTime(c.end)}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Key points */}
      <Card title="Key moments" icon={<Gauge />}>
        <div className="space-y-2">
          {a.keyPoints.map((k, i) => (
            <div key={i} className="rounded-xl border border-white/5 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-white">{k.title}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-slate-500">importance {k.importance.toFixed(0)}/10</span>
                  <TimeLink t={k.start} onSeek={onSeek} />
                </div>
              </div>
              <p className="text-xs text-slate-400 mt-1.5">{k.summary}</p>
            </div>
          ))}
        </div>
      </Card>

      {(a.topics.length > 0 || a.keywords.length > 0) && (
        <Card title="Topics & keywords" icon={<Hash />}>
          <div className="flex flex-wrap gap-2">
            {a.topics.map((t) => (
              <span key={t} className="px-3 py-1 rounded-full text-xs bg-indigo-500/20 text-indigo-200">{t}</span>
            ))}
            {a.keywords.filter((k) => !a.topics.includes(k)).map((k) => (
              <span key={k} className="px-3 py-1 rounded-full text-xs bg-white/5 text-slate-400">{k}</span>
            ))}
          </div>
        </Card>
      )}

      {a.glossary.length > 0 && (
        <Card title="Glossary" icon={<BookOpen />}>
          <dl className="space-y-2.5">
            {a.glossary.map((g) => (
              <div key={g.term}>
                <dt className="text-sm font-medium text-white">{g.term}</dt>
                <dd className="text-xs text-slate-400 mt-0.5">{g.definition}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}

      {a.actionItems.length > 0 && (
        <Card title="Things to practise" icon={<ListChecks />}>
          <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-300">
            {a.actionItems.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </Card>
      )}

      {a.faq.length > 0 && (
        <Card title="Questions this video answers" icon={<HelpCircle />}>
          <div className="space-y-3">
            {a.faq.map((f, i) => (
              <div key={i}>
                <p className="text-sm font-medium text-white">{f.q}</p>
                <p className="text-xs text-slate-400 mt-1">{f.a}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {a.quotes.length > 0 && (
        <Card title="Notable lines" icon={<Quote />}>
          <div className="space-y-3">
            {a.quotes.map((q, i) => (
              <blockquote key={i} className="border-l-2 border-indigo-500/60 pl-3 text-sm text-slate-300 italic">
                “{q.text}” <TimeLink t={q.time} onSeek={onSeek} />
              </blockquote>
            ))}
          </div>
        </Card>
      )}

      {/* File info + stats */}
      <Card title="Video information" icon={<Info />}>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
          <Stat label="File" value={m.fileName || "–"} />
          <Stat label="Duration" value={fmtTime(m.duration || 0)} />
          <Stat label="Resolution" value={res} />
          <Stat label="Frame rate" value={m.fps ? `${m.fps} fps` : "–"} />
          <Stat label="File size" value={fmtBytes(m.sizeBytes)} />
          <Stat label="Codecs" value={`${m.videoCodec || "–"} / ${m.audioCodec || "–"}`} />
          <Stat label="Words spoken" value={a.stats.wordCount.toLocaleString()} />
          <Stat label="Speaking pace" value={`${a.stats.wordsPerMinute} wpm`} />
          <Stat label="Speech vs. silence" value={`${a.stats.speakingPercent}% speech`} />
          <Stat label="Sentences" value={a.stats.sentenceCount.toLocaleString()} />
          <Stat label="Read-time of transcript" value={`${a.stats.estimatedReadMinutes} min`} />
          <Stat label="Uploaded" value={m.uploadedAt ? new Date(m.uploadedAt).toLocaleString() : "–"} />
        </div>
        <p className="text-[11px] text-slate-600 mt-3 flex items-center gap-1.5">
          <Film className="w-3 h-3" /> Times above are clickable and jump the player to that moment.
        </p>
      </Card>
    </div>
  );
};

export default OverviewTab;
