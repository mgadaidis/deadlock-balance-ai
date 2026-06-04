// Simulator — phase-by-phase prognostication of a draft.
import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { useItems } from '../contexts/ItemsContext.jsx';
import { GiltCorners, SectionHead } from '../components/Bureau.jsx';
import SimulationTimeline from '../components/SimulationTimeline.jsx';

// Each hero may carry up to 12 items. A full build improves confidence,
// but it is not mandatory; users can run the ML simulation with partial or empty builds.
const MAX_ITEMS = 12;

function HeroPicker({ heroes, selected, onChange, label }) {
  const toggle = (id) => {
    if (selected.includes(id)) onChange(selected.filter((x) => x !== id));
    else if (selected.length < 6) onChange([...selected, id]);
  };
  return (
    <div className="card">
      <GiltCorners />
      <h3 style={{ marginBottom: 'var(--s-3)' }}>{label}
        <span className="muted" style={{ fontFamily: 'var(--f-mono)', fontSize: '0.86rem', marginLeft: 'var(--s-2)' }}>
          {selected.length}/6
        </span>
      </h3>
      <div className="picker-grid">
        {heroes.map((h) => (
          <button key={h.id} type="button" onClick={() => toggle(h.id)}
            className={selected.includes(h.id) ? 'active' : ''}>
            {h.image_url ? <img className="entity-icon hero" src={h.image_url} alt="" loading="lazy" /> : <span className="entity-icon placeholder" />}
            <span>{h.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// One collapsible build editor per selected hero.
function HeroBuildCard({ hero, heroId, current, itemMap, filtered, open, onToggleOpen, onToggleItem }) {
  // Items blocked because a selected item excludes them (e.g. an upgraded
  // version of an item that is already in the build).
  const blocked = useMemo(() => {
    const set = new Set();
    for (const id of current) {
      const it = itemMap.get(id);
      if (it?.exclusive_ids) it.exclusive_ids.forEach((e) => set.add(e));
    }
    return set;
  }, [current, itemMap]);

  const full = current.length >= MAX_ITEMS;
  const complete = current.length === MAX_ITEMS;

  return (
    <div className="hero-build-card">
      <button
        type="button"
        className="hero-build-head as-toggle"
        onClick={onToggleOpen}
        aria-expanded={open}
      >
        <span className="entity-cell">
          {hero?.image_url ? <img className="entity-icon hero" src={hero.image_url} alt="" /> : <span className="entity-icon placeholder" />}
          {hero?.name || `Hero #${heroId}`}
        </span>
        <span className="hero-build-head-right">
          <span className={`mono build-count ${complete ? 'ok' : 'pending'}`}>{current.length}/{MAX_ITEMS}</span>
          <span className={`caret ${open ? 'open' : ''}`} aria-hidden>▾</span>
        </span>
      </button>

      {/* Selected items stay visible even when the picker is collapsed. */}
      {current.length > 0 && (
        <div className="hero-build-selected">
          {current.map((id) => {
            const it = itemMap.get(id);
            return (
              <button key={id} type="button" className="mini-item-btn active" title="Remove from build"
                onClick={() => onToggleItem(heroId, id)}>
                {it?.icon_url ? <img className="item-icon" src={it.icon_url} alt="" loading="lazy" /> : <span className="item-icon placeholder" />}
                <span>{it ? it.name : `#${id}`}</span>
                <span className="remove-x" aria-hidden>×</span>
              </button>
            );
          })}
        </div>
      )}

      {open && (
        <div className="hero-build-items">
          {filtered.length === 0 && <span className="muted" style={{ fontSize: '0.86rem' }}>No items match the current filters.</span>}
          {filtered.map((it) => {
            const isSelected = current.includes(it.item_id);
            const isBlocked = !isSelected && blocked.has(it.item_id);
            const disabled = !isSelected && (isBlocked || full);
            const title = isBlocked
              ? `Blocked: cannot be combined with an item already in this build (mutually exclusive / upgraded version).`
              : full && !isSelected
                ? `Build is full (${MAX_ITEMS} items). Remove one to swap.`
                : `Tier ${it.tier} · ${(it.win_rate * 100).toFixed(1)}% WR · ${it.category || 'unknown'}`;
            return (
              <button
                key={it.item_id}
                type="button"
                disabled={disabled}
                className={`mini-item-btn ${isSelected ? 'active' : ''} ${isBlocked ? 'blocked' : ''}`}
                onClick={() => onToggleItem(heroId, it.item_id)}
                title={title}
              >
                {it.icon_url ? <img className="item-icon" src={it.icon_url} alt="" loading="lazy" /> : <span className="item-icon placeholder" />}
                <span>[{it.tier}]</span>
                <span>{it.name}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function BuildEditor({ heroes, selectedHeroes, items, builds, onChange, label }) {
  const [tier, setTier] = useState('');
  const [category, setCategory] = useState('');
  const [query, setQuery] = useState('');
  const [openHeroes, setOpenHeroes] = useState({});

  const categories = useMemo(() => [...new Set(items.map((it) => it.category).filter(Boolean))].sort(), [items]);
  const filtered = useMemo(() => items
    .filter((it) => (tier ? it.tier === tier : true))
    .filter((it) => (category ? it.category === category : true))
    .filter((it) => (query.trim() ? it.name.toLowerCase().includes(query.trim().toLowerCase()) : true))
    .slice(0, 120), [items, tier, category, query]);

  const heroMap = useMemo(() => Object.fromEntries(heroes.map((h) => [h.id, h])), [heroes]);
  const itemMap = useMemo(() => {
    const m = new Map();
    for (const it of items) m.set(it.item_id, it);
    return m;
  }, [items]);

  const toggleItem = (heroId, itemId) => {
    const key = String(heroId);
    const current = builds[key] || [];
    if (current.includes(itemId)) {
      onChange({ ...builds, [key]: current.filter((x) => x !== itemId) });
      return;
    }
    if (current.length >= MAX_ITEMS) return;          // 12-item cap
    // Exclusivity guard: never allow two mutually-exclusive items together.
    const blockedNow = new Set();
    for (const id of current) {
      const it = itemMap.get(id);
      if (it?.exclusive_ids) it.exclusive_ids.forEach((e) => blockedNow.add(e));
    }
    if (blockedNow.has(itemId)) return;
    onChange({ ...builds, [key]: [...current, itemId] });
  };

  const toggleOpen = (heroId) => setOpenHeroes((o) => ({ ...o, [heroId]: !o[heroId] }));

  if (selectedHeroes.length === 0) {
    return (
      <div className="card">
        <GiltCorners />
        <h3>{label}</h3>
        <p className="muted">Select heroes first. Item builds are optional, but adding items improves build-specific prediction detail.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <GiltCorners />
      <h3 style={{ marginBottom: 'var(--s-2)' }}>{label}</h3>
      <p className="compat-note">
        Each hero can run with 0–{MAX_ITEMS} selected items. More items improve build confidence, but the supervised ML baseline still works without a full build. Mutually exclusive items — including upgraded versions of the same item — cannot both be chosen. The result weighs how well the selected build fits the hero, not just item win rates. Use the dropdown on each hero to open or close its item picker.
      </p>
      <div className="build-filter-row" style={{ margin: 'var(--s-3) 0' }}>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search items" />
        <select value={tier} onChange={(e) => setTier(e.target.value)}>
          <option value="">All tiers</option>
          {['S','A','B','C','D'].map((t) => <option key={t} value={t}>Tier {t}</option>)}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
      <div className="grid" style={{ gap: 'var(--s-3)' }}>
        {selectedHeroes.map((heroId) => (
          <HeroBuildCard
            key={heroId}
            heroId={heroId}
            hero={heroMap[heroId]}
            current={builds[String(heroId)] || []}
            itemMap={itemMap}
            filtered={filtered}
            open={!!openHeroes[heroId]}
            onToggleOpen={() => toggleOpen(heroId)}
            onToggleItem={toggleItem}
          />
        ))}
      </div>
    </div>
  );
}

// At least one friendly hero is required. Item builds are optional.
function draftReady(selected) {
  return selected.length > 0;
}

export default function Simulator() {
  const [heroes, setHeroes] = useState([]);
  const [team, setTeam] = useState([]);
  const [enemy, setEnemy] = useState([]);
  const [teamBuilds, setTeamBuilds] = useState({});
  const [enemyBuilds, setEnemyBuilds] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { items } = useItems();

  useEffect(() => {
    api.listHeroes().then(setHeroes).catch((e) => setError(
      e.response?.status === 404
        ? 'No personnel files on hand. Run a Refresh on the Overview page first.'
        : `The wire has gone cold — ${e.message}`));
  }, []);

  const cleanBuilds = (builds, selected) => {
    const allowed = new Set(selected.map(String));
    return Object.fromEntries(Object.entries(builds).filter(([k, v]) => allowed.has(k) && Array.isArray(v) && v.length));
  };

  // Run only requires at least one friendly hero. Item builds are optional;
  // missing/partial builds lower build-confidence but do not block the ML prediction.
  const canRun = draftReady(team) && !loading;

  const missingNote = useMemo(() => {
    if (team.length === 0) return 'Draft at least one hero for your team to run the ML simulation.';
    const countItems = (selected, builds) => selected.reduce((sum, id) => sum + ((builds[String(id)] || []).length), 0);
    const teamItems = countItems(team, teamBuilds);
    const enemyItems = countItems(enemy, enemyBuilds);
    if (teamItems === 0 && enemyItems === 0) {
      return 'No item builds selected yet. The simulator will still run using the trained ML hero baseline; item/build confidence will be lower.';
    }
    return `Partial builds accepted — your side has ${teamItems} selected item${teamItems === 1 ? '' : 's'} and the enemy side has ${enemyItems} selected item${enemyItems === 1 ? '' : 's'}.`;
  }, [team, enemy, teamBuilds, enemyBuilds]);

  const run = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await api.simulate({
        hero_ids: team,
        enemy_hero_ids: enemy.length ? enemy : null,
        team_hero_item_builds: cleanBuilds(teamBuilds, team),
        enemy_hero_item_builds: cleanBuilds(enemyBuilds, enemy),
      });
      setResult(r);
    } catch (e) {
      setError(`Simulation failed: ${e.message}`);
    } finally { setLoading(false); }
  };

  const reset = () => {
    setTeam([]); setEnemy([]); setTeamBuilds({}); setEnemyBuilds({});
    setResult(null); setError(null);
  };

  return (
    <>
      <section id="team-draft" className="section animate-fade-up">
        <SectionHead
          index={0}
          title="Simulator"
          sub="A phase-by-phase prognostication of the draft"
          right={
            <div style={{ display: 'flex', gap: 'var(--s-2)' }}>
              <button className="btn secondary" onClick={reset}>Reset</button>
              <button className="btn" onClick={run} disabled={!canRun}>
                {loading ? 'Conjuring' : 'Run simulation'}
              </button>
            </div>
          }
        />
        {error && <div className="error">{error}</div>}

        <div className="grid grid-2">
          <HeroPicker heroes={heroes} selected={team}  onChange={setTeam}  label="Your team" />
          <HeroPicker heroes={heroes} selected={enemy} onChange={setEnemy} label="Opposition" />
        </div>
      </section>

      <section id="items" className="section animate-fade-up">
        <SectionHead
          index={1}
          title="Item Configuration"
          sub={`Optionally assign up to ${MAX_ITEMS} items per selected hero — partial builds are allowed`}
        />
        {missingNote && <div className="build-gate-note">{missingNote}</div>}
        <div className="grid grid-2 sim-build-grid">
          <BuildEditor heroes={heroes} selectedHeroes={team} items={items} builds={teamBuilds} onChange={setTeamBuilds} label="Your hero builds" />
          <BuildEditor heroes={heroes} selectedHeroes={enemy} items={items} builds={enemyBuilds} onChange={setEnemyBuilds} label="Enemy hero builds" />
        </div>
      </section>

      <section id="timeline" className="section">
        <SectionHead
          index={2}
          title="Phase Timeline"
          sub="Early lane · mid-game spikes · late-game decisive fights"
        />
        {result
          ? <SimulationTimeline result={result} />
          : <div className="card"><GiltCorners /><p className="muted">Draft at least one hero, optionally add items, then run the ML simulation to chart the timeline.</p></div>}
      </section>
    </>
  );
}
