// Phase-by-phase timeline component. The three phase cards have staggered
// fade-in animations driven by CSS classes (.delay-1/2/3).
export default function SimulationTimeline({ result }) {
  if (!result || !result.phases || result.phases.length === 0) return null;

  const probability = (result.win_probability * 100).toFixed(1);
  const colour = result.win_probability >= 0.5 ? '#9EA4D9' : '#C2A6F0';
  const teamCompat = result.team_build_compatibility != null ? Math.round(result.team_build_compatibility * 100) : null;
  const enemyCompat = result.enemy_build_compatibility != null ? Math.round(result.enemy_build_compatibility * 100) : null;

  return (
    <div className="animate-fade-in">
      <div className="card" style={{ marginBottom: 'var(--s-3)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--s-4)', flexWrap: 'wrap' }}>
          <h4 style={{ margin: 0 }}>Win probability</h4>
          <span className="mono" style={{ fontSize: '2.6rem', fontWeight: 300, color: colour }}>
            {probability}%
          </span>
        </div>
        {teamCompat != null && (
          <div className="compat-readout">
            <span>Build compatibility — your team <b className="mono">{teamCompat}%</b></span>
            {enemyCompat != null && <span>· enemy <b className="mono">{enemyCompat}%</b></span>}
          </div>
        )}
        <p className="muted" style={{ marginTop: 'var(--s-2)' }}>{result.summary}</p>
        {result.model_note && <p className="compat-note" style={{ marginTop: 'var(--s-2)' }}>{result.model_note}</p>}
      </div>

      <div className="timeline">
        {result.phases.map((p, i) => (
          <div key={p.phase} className={`phase-card delay-${i + 1}`}>
            <div className="phase-label">
              <span className="phase-name">{p.phase}</span>
              <span className="phase-time">{p.time_range}</span>
              <div className="phase-bar">
                {/* visual indicator of advantage: bar fills from centre */}
                <span style={{
                  left:  p.team_advantage >= 0 ? '50%' : `${50 + p.team_advantage * 50}%`,
                  right: p.team_advantage >= 0 ? `${50 - p.team_advantage * 50}%` : '50%',
                  background: p.team_advantage >= 0 ? '#9EA4D9' : '#C2A6F0',
                }} />
              </div>
            </div>
            <div>
              <div className="phase-headline">{p.headline}</div>
              <ul className="phase-events">
                {p.events.map((ev, j) => <li key={j}>{ev}</li>)}
              </ul>
            </div>
          </div>
        ))}
      </div>
      {result.item_analysis && result.item_analysis.length > 0 && (
        <div className="card" style={{ marginTop: 'var(--s-3)' }}>
          <h4 style={{ marginTop: 0 }}>Build compatibility notes</h4>
          <ul className="sim-build-analysis">
            {result.item_analysis.map((note, i) => <li key={i}>{note}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
