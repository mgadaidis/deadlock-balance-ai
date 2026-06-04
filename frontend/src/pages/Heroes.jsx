import { useEffect, useMemo, useState } from "react";
import { GiltCorners, SectionHead } from "../components/Bureau.jsx";
import { api } from '../api/client.js';

const COLS = [
  { key: 'name', label: 'Hero' },
  { key: 'matches', label: 'Matches', fmt: (v) => v.toLocaleString() },
  { key: 'win_rate', label: 'Win rate', fmt: (v) => `${(v * 100).toFixed(1)}%` },
  { key: 'pick_rate', label: 'Pick rate', fmt: (v) => `${(v * 100).toFixed(1)}%` },
  { key: 'kda', label: 'KDA', fmt: (v) => v.toFixed(2) },
  { key: 'avg_kills', label: 'Avg K', fmt: (v) => v.toFixed(1) },
  { key: 'avg_deaths', label: 'Avg D', fmt: (v) => v.toFixed(1) },
  { key: 'avg_assists', label: 'Avg A', fmt: (v) => v.toFixed(1) },
  { key: 'avg_damage', label: 'Avg dmg', fmt: (v) => Math.round(v).toLocaleString() },
];

export default function Heroes() {
  const [stats, setStats] = useState([]);
  const [error, setError] = useState(null);
  const [sortKey, setSortKey] = useState('win_rate');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => {
    api.latestStats().then(setStats).catch((e) =>
      setError(e.response?.status === 404
        ? 'No data yet — refresh from the Overview page.'
        : `Backend error: ${e.message}`));
  }, []);

  const sorted = useMemo(() => {
    const c = stats.slice();
    c.sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return c;
  }, [stats, sortKey, sortDir]);

  const onSort = (key) => {
    if (key === sortKey) setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  return (
    <section className="section animate-fade-up">
      <SectionHead title="Hero Stats" sub="Latest dispatch from the Bureau's wire" />
      {error && <div className="error">{error}</div>}
      <div className="card">
        <GiltCorners />
        <table>
          <thead>
            <tr>
              {COLS.map((c) => (
                <th key={c.key} onClick={() => onSort(c.key)} style={{ cursor: 'pointer' }}>
                  {c.label}{sortKey === c.key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.hero_id}>
                {COLS.map((c) => (
                  <td key={c.key} className={typeof s[c.key] === 'number' ? 'mono' : ''}>
                    {c.key === 'name' ? (
                      <span className="entity-cell">
                        {s.image_url ? <img className="entity-icon hero" src={s.image_url} alt="" loading="lazy" /> : <span className="entity-icon placeholder" />}
                        <span>{s.name}</span>
                      </span>
                    ) : (c.fmt ? c.fmt(s[c.key]) : s[c.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
