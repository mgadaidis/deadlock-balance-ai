// App shell — Bureau of Equilibrium, occult-noir variant.
import { useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';

import NavDropdown from './components/NavDropdown.jsx';
import Heroes from './pages/Heroes.jsx';
import Overview from './pages/Overview.jsx';
import Recommendations from './pages/Recommendations.jsx';
import ItemRecommendations from './pages/ItemRecommendations.jsx';
import Simulator from './pages/Simulator.jsx';
import './App.css';

const NAV = [
  { to: '/', label: 'Overview', sections: [
      { id: 'summary',    label: 'Summary' },
      { id: 'net-worth',  label: 'Net worth spikes' },
      { id: 'tier-list',  label: 'Item tier list' },
      { id: 'meta-shift', label: 'Meta shift' },
    ]},
  { to: '/simulator', label: 'Simulator', sections: [
      { id: 'team-draft', label: 'Team draft' },
      { id: 'items',      label: 'Item configuration' },
      { id: 'timeline',   label: 'Phase timeline' },
    ]},
  { to: '/hero-recommendations', label: 'Hero Recommendations', sections: [
      { id: 'ml-model',     label: 'ML balance model' },
      { id: 'overpowered',  label: 'Overpowered' },
      { id: 'underpowered', label: 'Underpowered' },
      { id: 'balanced',     label: 'Balanced' },
    ]},
  { to: '/item-recommendations', label: 'Item Recommendations', sections: [
      { id: 'weapon',   label: 'Weapon items' },
      { id: 'spirit',   label: 'Spirit items' },
      { id: 'vitality', label: 'Vitality items' },
    ]},
];

// SVG monogram: an Art Deco sunburst around an open eye — the "Bureau" seal.
function BrandMark() {
  return (
    <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <defs>
        <linearGradient id="gilt" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"  stopColor="var(--c-moonlight)" />
          <stop offset="50%" stopColor="var(--c-gilt)" />
          <stop offset="100%" stopColor="var(--c-moonlight)" />
        </linearGradient>
      </defs>
      {/* sunburst rays */}
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={i}
          x1="32" y1="32" x2="32" y2="6"
          stroke="url(#gilt)" strokeWidth="0.8"
          transform={`rotate(${i * 30} 32 32)`} />
      ))}
      {/* outer ring */}
      <circle cx="32" cy="32" r="22" fill="none" stroke="url(#gilt)" strokeWidth="0.8" />
      <circle cx="32" cy="32" r="18" fill="none" stroke="var(--c-twilight)" strokeWidth="0.5" />
      {/* the eye */}
      <ellipse cx="32" cy="32" rx="10" ry="5.5" fill="none" stroke="var(--c-moonlight)" strokeWidth="0.9" />
      <circle cx="32" cy="32" r="2.6" fill="var(--c-moonlight)" />
      <circle cx="32.8" cy="31.2" r="0.7" fill="var(--c-ink)" />
    </svg>
  );
}

function HashScroller() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) { window.scrollTo({ top: 0 }); return; }
    const id = hash.replace('#', '');
    const t = setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
    return () => clearTimeout(t);
  }, [pathname, hash]);
  return null;
}

export default function App() {
  const location = useLocation();
  // Final proposal version: use the first/Overview palette across the whole site
  // so the UI has one consistent visual identity instead of page-by-page colors.
  const themeName = 'overview';

  useEffect(() => {
    document.body.dataset.theme = themeName;
    return () => {
      delete document.body.dataset.theme;
    };
  }, [themeName]);

  const handleReset = () => {
    try { sessionStorage.clear(); localStorage.clear(); } catch {}
    window.location.assign('/');
  };

  return (
    <div className={`app theme-${themeName}`}>
      <HashScroller />
      <header className="topbar">
        <button type="button" className="brand" onClick={handleReset}
          title="Reset session and return to the Overview">
          <span className="brand-mark lamp-flicker"><BrandMark /></span>
          <span>
            <h1>Deadlock Balance</h1>
          </span>
        </button>
        <nav className="nav">
          {NAV.map((n) => <NavDropdown key={n.to} {...n} />)}
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/"                element={<Overview />} />
          <Route path="/simulator"       element={<Simulator />} />
          <Route path="/hero-recommendations" element={<Recommendations />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/item-recommendations" element={<ItemRecommendations />} />
          <Route path="/heroes"          element={<Heroes />} />
        </Routes>
      </main>
      <footer className="footer">
        <div className="footer-left">
          <span>Deadlock Balance AI</span>
          <small>public analytics prototype</small>
        </div>
        <div className="footer-right">
          <span>Data sources</span>
          <a href="https://deadlock-api.com" target="_blank" rel="noreferrer">Deadlock API</a>
          <a href="https://statlocker.gg" target="_blank" rel="noreferrer">Statlocker</a>
          <a href="https://liquipedia.net/deadlock" target="_blank" rel="noreferrer">Liquipedia</a>
        </div>
      </footer>
    </div>
  );
}
