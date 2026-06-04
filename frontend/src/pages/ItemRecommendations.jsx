// Item Recommendations — categorized item case files.
// There are many items, so this page uses compact category lists and expands
// one item at a time instead of rendering huge hero-style cards.
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { SectionHead, GiltCorners } from '../components/Bureau.jsx';

const CATEGORY_LABELS = {
  weapon: 'Weapon',
  spirit: 'Spirit',
  vitality: 'Vitality',
};

function ItemRow({ item, open, onToggle }) {
  return (
    <div className={`item-rec-row ${open ? 'open' : ''}`}>
      <button type="button" className="item-rec-head" onClick={onToggle} aria-expanded={open}>
        <span className="entity-cell">
          {item.icon_url && <img className="item-icon" src={item.icon_url} alt="" loading="lazy" />}
          <span>{item.name}</span>
        </span>
        <span className="item-rec-meta">
          <span className={`verdict-pill ${item.verdict.includes('under') || item.verdict.includes('weak') ? 'underpowered' : item.verdict.includes('over') || item.verdict.includes('strong') ? 'overpowered' : 'balanced'}`}>
            {item.verdict}
          </span>
          <span className="mono">{(item.win_rate * 100).toFixed(1)}% WR</span>
          <span className="mono">{((item.usage_rate || 0) * 100).toFixed(2)}% use</span>
          <span className="mono">Tier {item.tier}</span>
          <span className="caret" aria-hidden>{open ? '▴' : '▾'}</span>
        </span>
      </button>

      {open && (
        <div className="item-rec-body">
          <div className="rec-meta item-rec-stats">
            <span>Matches <b className="mono">{item.matches.toLocaleString()}</b></span>
            <span>Usage share <b className="mono">{((item.usage_rate || 0) * 100).toFixed(2)}%</b></span>
            <span>Confidence <b className="mono">{item.confidence.toFixed(2)}</b></span>
            <span>Severity <b className="mono">{item.severity}</b></span>
            {item.exclusive_names?.length > 0 && (
              <span>Direct exclusions <b className="mono">{item.exclusive_names.join(', ')}</b></span>
            )}
          </div>

          <div className="rec-section">
            <div className="heading">i · Evidence</div>
            <p>{item.evidence}</p>
          </div>
          <div className="rec-section">
            <div className="heading">ii · Simulator impact</div>
            <p>{item.simulation_note}</p>
          </div>
          <div className="rec-section action">
            <div className="heading">iii · Recommendation</div>
            <p>{item.recommendation}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryPanel({ id, index, title, items }) {
  const [openId, setOpenId] = useState(null);
  const sorted = useMemo(() => items || [], [items]);

  return (
    <section id={id} className="section animate-fade-up">
      <SectionHead
        index={index}
        title={`${title} Items`}
        sub="Compact item balance list; open an item to view the full recommendation"
        right={<span className="muted mono">{sorted.length} items</span>}
      />
      <div className="card item-rec-panel">
        <GiltCorners />
        {sorted.length === 0 ? (
          <p className="muted">No item recommendations in this category yet. Run Refresh Data from Overview.</p>
        ) : (
          <div className="item-rec-list">
            {sorted.map((item) => (
              <ItemRow
                key={item.item_id}
                item={item}
                open={openId === item.item_id}
                onToggle={() => setOpenId(openId === item.item_id ? null : item.item_id)}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default function ItemRecommendations() {
  const [data, setData] = useState({ weapon: [], spirit: [], vitality: [] });
  const [error, setError] = useState(null);

  useEffect(() => {
    api.itemRecommendations()
      .then((d) => setData({ weapon: [], spirit: [], vitality: [], ...d }))
      .catch((e) => setError(
        e.response?.status === 404
          ? 'No item case files yet. Run Refresh from the Overview page.'
          : `The wire has gone cold — ${e.message}`));
  }, []);

  return (
    <>
      {error && <div className="error">{error}</div>}
      <CategoryPanel id="weapon" index={0} title={CATEGORY_LABELS.weapon} items={data.weapon} />
      <CategoryPanel id="spirit" index={1} title={CATEGORY_LABELS.spirit} items={data.spirit} />
      <CategoryPanel id="vitality" index={2} title={CATEGORY_LABELS.vitality} items={data.vitality} />
    </>
  );
}
