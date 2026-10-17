import React, { useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Video, Upload, LayoutDashboard, Sparkles } from "lucide-react";
import { cn } from "../utils/cn";

const links = [
  { to: "/", label: "Home", icon: Video },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/dashboard", label: "Projects", icon: LayoutDashboard },
  { to: "/explainer", label: "AI Explainer", icon: Sparkles },
];

/** Floating pill navigation with a sliding active indicator. */
const Navbar: React.FC = () => {
  const { pathname } = useLocation();
  const refs = useRef<(HTMLAnchorElement | null)[]>([]);
  const [pill, setPill] = useState({ left: 0, width: 0, show: false });
  const [scrolled, setScrolled] = useState(false);

  useLayoutEffect(() => {
    const place = () => {
      const i = links.findIndex((l) => (l.to === "/" ? pathname === "/" : pathname.startsWith(l.to)));
      const el = refs.current[i];
      setPill(el ? { left: el.offsetLeft, width: el.offsetWidth, show: true } : { left: 0, width: 0, show: false });
    };
    place();
    window.addEventListener("resize", place);
    return () => window.removeEventListener("resize", place);
  }, [pathname]);

  useLayoutEffect(() => {
    const on = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  return (
    <header className="fixed top-4 inset-x-0 z-50 flex justify-center px-4 nav-drop">
      <nav className={cn("glass-strong rounded-full pl-3 pr-2 py-2 flex items-center gap-4 transition-all duration-500", scrolled && "shadow-glow scale-[0.98]")}>
        <Link to="/" className="flex items-center gap-2 group">
          <span className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-fuchsia-500 flex items-center justify-center group-hover:rotate-[360deg] transition-transform duration-700">
            <Video className="w-4 h-4 text-white" />
          </span>
          <span className="font-display font-bold gradient-text hidden sm:block">Reel Studio</span>
        </Link>

        <div className="relative flex items-center">
          <span
            className="absolute top-0 bottom-0 rounded-full bg-white/10 border border-white/10 transition-all duration-500 ease-[cubic-bezier(.2,.9,.3,1.2)]"
            style={{ left: pill.left, width: pill.width, opacity: pill.show ? 1 : 0 }}
          />
          {links.map((l, i) => {
            const Icon = l.icon;
            const active = pill.show && refs.current[i]?.offsetLeft === pill.left;
            return (
              <Link
                key={l.to}
                to={l.to}
                ref={(el) => { refs.current[i] = el; }}
                className={cn("relative z-10 flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors", active ? "text-white" : "text-slate-400 hover:text-white")}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{l.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
