// Visual tier list: one row per letter (S/A/B/C/D) packed with item chips.
// Reads from the global ItemsContext rather than fetching directly.
import { useItems } from '../contexts/ItemsContext.jsx';

export default function ItemTierList({ limitPerTier = 999 }) {
  const { tierList, loading, error } = useItems();

  if (loading) return <p className="muted">Loading items…</p>;
  if (error)   return <div className="error">Items unavailable: {error}</div>;

  const tiers = ['S', 'A', 'B', 'C', 'D'];
  const anyData = tiers.some((t) => (tierList[t] || []).length > 0);
  if (!anyData) {
    return <p className="muted">No item data yet — run a refresh.</p>;
  }

  return (
    <div>
      {tiers.map((t) => {
        const bucket = (tierList[t] || []).slice(0, limitPerTier);
        return (
          <div key={t} className="tier-row">
            <div className={`tier-letter ${t}`}>{t}</div>
            <div className="tier-items">
              {bucket.length === 0
                ? <span className="muted" style={{ fontSize: '0.82rem' }}>—</span>
                : bucket.map((it) => (
                    <span key={it.item_id} className="tier-chip" title={`Win rate ${(it.win_rate*100).toFixed(1)}% · ${it.matches.toLocaleString()} matches`}>
                      {it.icon_url && <img className="item-icon" src={it.icon_url} alt="" loading="lazy" />}
                      <span>{it.name}</span>
                    </span>
                  ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
