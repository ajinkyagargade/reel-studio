import React, { useRef } from "react";
import { Link } from "react-router-dom";
import { Upload, Sparkles, Video, Zap, Subtitles, Crop, Play, Layers, Wand2, ArrowRight, Check } from "lucide-react";
import Reveal from "../components/Reveal";
import SpotlightCard from "../components/SpotlightCard";
import Counter from "../components/Counter";
import { useReveal } from "../hooks/useReveal";

const Words: React.FC<{ text: string; start?: number; className?: string }> = ({ text, start = 0, className }) => (
  <>
    {text.split(" ").map((w, i) => (
      <span key={i} className="word mr-[0.25em]">
        <span className={className} style={{ animationDelay: `${start + i * 90}ms` }}>{w}</span>
      </span>
    ))}
  </>
);

const terms = ["Kubernetes", "useEffect", "Docker", "REST APIs", "TypeScript", "Redux", "GraphQL", "Big-O", "Git rebase", "Async/Await", "SQL Joins", "WebSockets"];

const steps = [
  ["Transcribe", "Whisper speech-to-text with word-level timing for English, Hindi and Hinglish."],
  ["Understand", "A clear summary, chapters and the key points of the whole video."],
  ["Create", "A point-wise reel of about 60 seconds with AI voice-over and animated captions."],
  ["Edit", "Change transitions, captions, filters and framing, then re-render in one click."],
];

const Home: React.FC = () => {
  const hero = useRef<HTMLElement>(null);
  const pipe = useReveal<HTMLDivElement>(0.3);

  const onMove = (e: React.MouseEvent) => {
    const r = hero.current?.getBoundingClientRect();
    if (!r || !hero.current) return;
    hero.current.style.setProperty("--px", String(((e.clientX - r.left) / r.width - 0.5) * 2));
    hero.current.style.setProperty("--py", String(((e.clientY - r.top) / r.height - 0.5) * 2));
  };

  return (
    <div className="space-y-32 pb-16">
      {/* HERO – split layout */}
      <section ref={hero} onMouseMove={onMove} className="grid lg:grid-cols-[1.15fr_1fr] gap-12 items-center min-h-[78vh]">
        <div>
          <Reveal variant="blur">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 glass rounded-full text-sm text-indigo-300 mb-8">
              <span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" /></span>
              <Zap className="w-4 h-4" /> AI Video Studio for Educators
            </div>
          </Reveal>

          <h1 className="text-5xl md:text-7xl font-bold leading-[1.05] mb-6">
            <Words text="Turn lectures into" /><br />
            <Words text="scroll-stopping" start={300} /><br />
            <Words text="reels." start={600} className="gradient-text" />
          </h1>

          <Reveal delay={700} variant="up">
            <p className="text-lg text-slate-400 max-w-xl mb-10">
              Upload a class recording. AI explains the whole video, then turns its key points into a captioned, voiced 60-second reel you can edit.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link to="/upload" className="btn-primary group inline-flex items-center justify-center gap-2 px-8 py-4">
                <Upload className="w-5 h-5" /> Upload Recording
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link to="/explainer" className="btn-ghost inline-flex items-center justify-center gap-2 px-8 py-4">
                <Sparkles className="w-5 h-5" /> Topic Explainer
              </Link>
            </div>
          </Reveal>
        </div>

        {/* Animated phone */}
        <Reveal variant="zoom" delay={300} className="flex justify-center relative">
          <div className="parallax" style={{ "--d": 14 } as React.CSSProperties}>
            <div className="phone float-slow">
              <div className="phone-screen">
                <div className="scan" />
                <div className="p-5 pt-10 space-y-3">
                  {[85, 60, 92, 45, 70, 55].map((w, i) => (
                    <div key={i} className="code-line" style={{ width: `${w}%`, animationDelay: `${i * 0.25}s`, background: i % 3 === 0 ? "rgba(129,140,248,.5)" : undefined }} />
                  ))}
                </div>
                <div className="absolute bottom-16 inset-x-0 text-center">
                  <span className="caption-pop inline-block px-3 py-1.5 rounded-lg bg-yellow-300 text-black font-bold text-lg">useEffect</span>
                </div>
                <div className="absolute bottom-6 inset-x-6 h-1 rounded-full bg-white/10 overflow-hidden"><div className="h-full w-full bg-gradient-to-r from-indigo-400 to-pink-400 code-line" style={{ animationDuration: "6s" }} /></div>
              </div>
            </div>
          </div>
          <div className="parallax absolute -left-2 top-16 hidden md:block" style={{ "--d": -26 } as React.CSSProperties}>
            <div className="glass-strong rounded-2xl px-4 py-3 flex items-center gap-3 float-slow"><Subtitles className="w-5 h-5 text-pink-400" /><span className="text-sm">Captions synced</span></div>
          </div>
          <div className="parallax absolute -right-2 bottom-24 hidden md:block" style={{ "--d": 30 } as React.CSSProperties}>
            <div className="glass-strong rounded-2xl px-4 py-3 flex items-center gap-3 float-slow" style={{ animationDelay: "1.5s" }}><Check className="w-5 h-5 text-emerald-400" /><span className="text-sm">6 points found</span></div>
          </div>
        </Reveal>
      </section>

      {/* MARQUEE */}
      <section className="-mx-4 overflow-hidden" style={{ maskImage: "linear-gradient(90deg,transparent,#000 15%,#000 85%,transparent)", WebkitMaskImage: "linear-gradient(90deg,transparent,#000 15%,#000 85%,transparent)" }}>
        <p className="text-center text-xs uppercase tracking-[.3em] text-slate-500 mb-6">Works for any topic</p>
        <div className="marquee">
          {[...terms, ...terms].map((t, i) => (
            <span key={i} className="mx-3 px-5 py-2 glass rounded-full text-slate-300 whitespace-nowrap font-display">{t}</span>
          ))}
        </div>
      </section>

      {/* STATS */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {[[20, "+", "Transitions to choose from"], [60, "s", "Reel from a long video"], [6, "", "Caption styles"], [9, ":16", "Vertical, square or wide"]].map(([n, s, l], i) => (
          <Reveal key={i} delay={i * 120} variant="up" className="text-center">
            <div className="text-5xl md:text-6xl font-display font-bold gradient-text"><Counter to={n as number} suffix={s as string} /></div>
            <p className="text-sm text-slate-500 mt-2">{l}</p>
          </Reveal>
        ))}
      </section>

      {/* BENTO FEATURES */}
      <section>
        <Reveal variant="blur" className="max-w-2xl mb-12">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">Everything between <span className="gradient-text">raw footage</span> and published.</h2>
        </Reveal>
        <div className="grid md:grid-cols-6 gap-5 auto-rows-[minmax(220px,auto)]">
          <Bento span="md:col-span-4" icon={<Video />} title="Point-wise Reel from Any Video" text="Finds the key teaching points in the transcript and stitches them into a 60-second reel with voice-over." delay={0}>
            <div className="flex items-end gap-1 h-16 mt-6">
              {Array.from({ length: 40 }).map((_, i) => (
                <div key={i} className="flex-1 rounded-sm bg-gradient-to-t from-indigo-500 to-fuchsia-400 code-line" style={{ height: `${20 + Math.abs(Math.sin(i * 0.7)) * 80}%`, animationDelay: `${i * 0.05}s`, transformOrigin: "bottom", animationName: "bar" }} />
              ))}
            </div>
          </Bento>
          <Bento span="md:col-span-2" icon={<Crop />} title="Smart 9:16 Framing" text="Blurred-background fit, or zoom into the part of the screen you choose." delay={100} />
          <Bento span="md:col-span-2" icon={<Subtitles />} title="Animated Captions" text="Word-by-word highlight, 6 styles, any position." delay={200} />
          <Bento span="md:col-span-2" icon={<Layers />} title="Transitions & Filters" text="Per-point transitions, colour looks, speed and zoom." delay={300} />
          <Bento span="md:col-span-2" icon={<Wand2 />} title="AI Voice-over" text="Natural neural voices in English and Hindi narrate each point." delay={400} />
        </div>
      </section>

      {/* PIPELINE */}
      <section className="grid lg:grid-cols-2 gap-16 items-center">
        <Reveal variant="left">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">From recording to reel in <span className="gradient-text">four steps.</span></h2>
          <p className="text-slate-400">No timelines to scrub, no manual captions. Just review and publish.</p>
        </Reveal>
        <div ref={pipe} className="reveal relative pl-0 space-y-8 reveal-up">
          <div className="pipe-line" />
          {steps.map(([t, d], i) => (
            <div key={t} className="relative flex gap-6 items-start" style={{ transitionDelay: `${i * 200}ms` }}>
              <div className="relative z-10 w-14 h-14 shrink-0 rounded-2xl glass-strong flex items-center justify-center font-display font-bold text-indigo-300 text-xl">{i + 1}</div>
              <div><h3 className="text-xl font-semibold">{t}</h3><p className="text-slate-400 text-sm mt-1">{d}</p></div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <Reveal variant="zoom">
        <div className="border-spin max-w-4xl mx-auto">
          <div className="p-12 md:p-16 text-center">
            <h2 className="text-4xl md:text-5xl font-bold mb-4">Ready to make your first reel?</h2>
            <p className="text-slate-400 mb-8">Drop a recording. We'll handle the rest.</p>
            <Link to="/upload" className="btn-primary inline-flex items-center gap-2 px-10 py-4 animate-pulse-glow"><Play className="w-5 h-5" /> Get Started</Link>
          </div>
        </div>
      </Reveal>
    </div>
  );
};

const Bento: React.FC<{ span: string; icon: React.ReactNode; title: string; text: string; delay: number; children?: React.ReactNode }> = ({ span, icon, title, text, delay, children }) => (
  <Reveal delay={delay} variant="up" className={span}>
    <SpotlightCard className="h-full p-7">
      <div className="w-12 h-12 rounded-2xl bg-indigo-500/15 text-indigo-300 flex items-center justify-center mb-5 [&>svg]:w-6 [&>svg]:h-6">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{text}</p>
      {children}
    </SpotlightCard>
  </Reveal>
);

export default Home;
