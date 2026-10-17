import React, { useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar";
import CursorGlow from "./components/CursorGlow";
import Home from "./pages/Home";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Editor from "./pages/Editor";
import TopicExplainer from "./pages/TopicExplainer";

const ScrollProgress: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const on = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      if (ref.current) ref.current.style.transform = `scaleX(${h > 0 ? window.scrollY / h : 0})`;
    };
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return <div ref={ref} className="scroll-progress" />;
};

const AnimatedRoutes: React.FC = () => {
  const location = useLocation();
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);
  return (
    <div key={location.pathname} className="page-enter">
      <Routes location={location}>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/editor/:videoId" element={<Editor />} />
        <Route path="/explainer" element={<TopicExplainer />} />
      </Routes>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <div className="bg-mesh min-h-screen relative overflow-hidden">
        <div className="bg-grid" aria-hidden />
        <div className="aurora a1" aria-hidden />
        <div className="aurora a2" aria-hidden />
        <div className="aurora a3" aria-hidden />
        <CursorGlow />
        <ScrollProgress />
        <Navbar />
        <main className="container mx-auto px-4 pt-28 pb-12 max-w-7xl relative z-10">
          <AnimatedRoutes />
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
