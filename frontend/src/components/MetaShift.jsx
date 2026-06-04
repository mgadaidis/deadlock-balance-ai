// Snapshot-to-snapshot win-rate deltas.
// If only one snapshot exists, we still show a current baseline table so the
// module never looks broken/empty after the first refresh.
export default function MetaShift({ data }) {
  if (!data) return null;

  const formatDelta = (v) => `${v >= 0 ? '+' : ''}${(v * 100).toFixed(2)}%`;

  if (!data.previous_snapshot) {
    const current = (data.entries || [])
      .slice()
      .sort((a, b) => Math.abs(b.win_rate - 0.5) - Math.abs(a.win_rate - 0.5))
      .slice(0, 20);

    if (!current.length) {
      return <p className="muted">No current snapshot rows available yet. Run Refresh Data.</p>;
    }

    return (
      <>
        <p className="muted" style={{ textAlign: 'center', marginBottom: 'var(--s-3)' }}>
          Only one snapshot exists, so true movement cannot be calculated yet. Displaying the current snapshot baseline instead.
        </p>
        <table>
          <thead>
            <tr>
              <th>Hero</th>
              <th>Snapshot signal</th>
              <th className="mono">Win rate</th>
              <th className="mono">Distance from 50%</th>
              <th className="mono">Pick rate</th>
            </tr>
          </thead>
          <tbody>
            {current.map((e) => {
              const distance = e.win_rate - 0.5;
              const signal = distance > 0.03 ? 'above baseline' : distance < -0.03 ? 'below baseline' : 'near baseline';
              return (
                <tr key={e.hero_id}>
                  <td>{e.name}</td>
                  <td>
                    <span className={`verdict-pill ${signal === 'above baseline' ? 'overpowered' : signal === 'below baseline' ? 'underpowered' : 'balanced'}`}>
                      {signal}
                    </span>
                  </td>
                  <td className="mono">{(e.win_rate * 100).toFixed(1)}%</td>
                  <td className="mono">{formatDelta(distance)}</td>
                  <td className="mono">{(e.pick_rate * 100).toFixed(1)}%</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </>
    );
  }

  const top = data.entries
    .filter((e) => e.direction !== 'stable')
    .slice(0, 20);

  if (!top.length) {
    return <p className="muted">No notable win-rate movement between the last two snapshots.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Hero</th>
          <th>Direction</th>
          <th className="mono">Win rate</th>
          <th className="mono">Δ WR</th>
          <th className="mono">Pick rate</th>
          <th className="mono">Δ PR</th>
        </tr>
      </thead>
      <tbody>
        {top.map((e) => (
          <tr key={e.hero_id}>
            <td>{e.name}</td>
            <td>
              <span className={`verdict-pill ${e.direction === 'rising' ? 'underpowered' : 'overpowered'}`}>
                {e.direction}
              </span>
            </td>
            <td className="mono">{(e.win_rate * 100).toFixed(1)}%</td>
            <td className="mono">{formatDelta(e.win_rate_delta)}</td>
            <td className="mono">{(e.pick_rate * 100).toFixed(1)}%</td>
            <td className="mono">{formatDelta(e.pick_rate_delta)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
