// Overview — Bureau dossier on current balance signal.
//
// IMPORTANT STATE NOTE: refresh status (the "Dispatch received" line) is
// stored separately from load errors so the two never overwrite each other.
// After a refresh, the user always sees:
//   - what the upstream returned (mode, counts)
//   - any soft errors from the refresh
//   - the visible page state (charts, tables) reflecting the new DB rows
import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { useItems } from '../contexts/ItemsContext.jsx';
import { Divider, GiltCorners, SectionHead } from '../components/Bureau.jsx';
import ItemTierList from '../components/ItemTierList.jsx';
import MetaShift from '../components/MetaShift.jsx';
import NetWorthChart from '../components/NetWorthChart.jsx';
import WinRateChart from '../components/WinRateChart.jsx';

export default function Overview() {
  const [summary, setSummary] = useState(null);
  const [flags, setFlags] = useState([]);
  const [stats, setStats] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loadError, setLoadError] = useState(null);    // from /heroes etc.
  const [dispatch, setDispatch] = useState(null);      // {kind, message} from refresh
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { reload: reloadItems } = useItems();

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);

    const [summaryResult, flagsResult, statsResult, metaResult] = await Promise.allSettled([
      api.balanceSummary(), api.balanceFlags(), api.latestStats(), api.metaShift(),
    ]);

    if (summaryResult.status === 'fulfilled') setSummary(summaryResult.value);
    if (flagsResult.status === 'fulfilled') setFlags(flagsResult.value);
    if (statsResult.status === 'fulfilled') setStats(statsResult.value);
    if (metaResult.status === 'fulfilled') setMeta(metaResult.value);

    const notReady = [summaryResult, flagsResult, statsResult].some(
      (r) => r.status === 'rejected' && r.reason?.response?.status === 404
    );
    const hardFailures = [summaryResult, flagsResult, statsResult, metaResult].filter(
      (r) => r.status === 'rejected' && r.reason?.response?.status !== 404
    );

    if (notReady) {
      setLoadError('No records on file. Engage the Refresh dispatch to draw the latest figures.');
      if (flagsResult.status === 'rejected') setFlags([]);
      if (statsResult.status === 'rejected') setStats([]);
      if (metaResult.status === 'rejected') setMeta(null);
    } else if (hardFailures.length) {
      setLoadError(`Some data is delayed — ${hardFailures.map((r) => r.reason?.message || 'request failed').join(' · ')}`);
    }

    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setDispatch(null);
    try {
      const result = await api.refresh();
      // Compose the dispatch message — show upstream vs DB counts so the user
      // can immediately tell if the upstream returned nothing or our DB rejected it.
      const lines = [
        `mode: ${result.match_mode || '—'}` + (result.mode_param_used ? ` (via ${result.mode_param_used})` : ' (unfiltered)'),
        `upstream heroes: ${result.upstream_heroes}  ·  upstream stats: ${result.upstream_stats}`,
        `inserted: ${result.heroes_loaded} heroes · ${result.stats_inserted} stats · ${result.items_inserted} items · ${result.flags_generated} flags · ${result.ability_paths_inserted ?? 0} ability paths`,
      ];
      if (result.upstream_stats === 0) {
        lines.push('⚠ Upstream returned zero hero-stats rows. Check /diagnose at the backend, or set MATCH_MODE="" in backend/.env.');
      }
      const message = lines.join('  ·  ');
      setDispatch({
        kind: result.errors?.length > 0 ? 'warning' : (result.upstream_stats === 0 ? 'warning' : 'info'),
        message,
        notices: result.errors || [],
      });
      await Promise.all([load(), reloadItems()]);
    } catch (e) {
      const details = e.response?.data ? ` (${JSON.stringify(e.response.data)})` : '';
      setDispatch({
        kind: 'error',
        message: `Refresh failed: ${e.message}${details}`,
        notices: [],
      });
    } finally {
      setRefreshing(false);
    }
  }, [load, reloadItems]);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <section id="summary" className="section animate-fade-up">
        <SectionHead
          index={0}
          title="Overview"
          sub="The standing balance signal across the current matchmade lobby"
          right={
            <button
              className={`btn refresh ${refreshing ? 'spinning' : ''}`}
              onClick={refresh} disabled={refreshing}
            >
              <span className="refresh-inner">
                {refreshing && <span className="refresh-spinner" aria-hidden />}
                <span>{refreshing ? 'Wiring' : 'Refresh data'}</span>
              </span>
            </button>
          }
        />

        {dispatch && (
          <div className={`dispatch ${dispatch.kind}`}>
            <div className="dispatch-head">DISPATCH</div>
            <div className="dispatch-body">{dispatch.message}</div>
            {dispatch.notices.length > 0 && (
              <ul className="dispatch-notices">
                {dispatch.notices.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            )}
          </div>
        )}
        {loadError && !dispatch && <div className="error">{loadError}</div>}

        <div className="grid grid-3">
          <div className="tile op"><div className="label">Overpowered</div><div className="value mono">{summary?.overpowered ?? '—'}</div></div>
          <div className="tile up"><div className="label">Underpowered</div><div className="value mono">{summary?.underpowered ?? '—'}</div></div>
          <div className="tile bal"><div className="label">Balanced</div><div className="value mono">{summary?.balanced ?? '—'}</div></div>
        </div>

        {flags.length > 0 && (
          <>
            <Divider />
            <div className="card chart-card chart-card-roster animate-fade-up">
              <GiltCorners />
              <h3 style={{ marginBottom: 'var(--s-3)' }}>Win rate · roster</h3>
              <WinRateChart data={flags} />
            </div>
          </>
        )}
      </section>

      <section id="net-worth" className="section animate-fade-up">
        <SectionHead index={1} title="Net Worth Spikes" sub="Heroes whose souls outrun the lobby — the empire builders" />
        <div className="card chart-card chart-card-networth">
          <GiltCorners />
          {stats.length === 0
            ? <p className="muted">No figures on the wire yet. Trigger Refresh.</p>
            : <NetWorthChart data={stats} />}
        </div>
      </section>

      <section id="tier-list" className="section animate-fade-up">
        <SectionHead index={2} title="Item Tier List" sub="Ranked by win rate, weighted by the volume of observed games" />
        <div className="card"><GiltCorners /><ItemTierList /></div>
      </section>

      <section id="meta-shift" className="section animate-fade-up">
        <SectionHead index={3} title="Meta Shift" sub="Movement of the meta between the two most recent dispatches" />
        <div className="card">
          <GiltCorners />
          {meta ? <MetaShift data={meta} /> : <p className="muted">{loading ? 'Drawing the wire…' : 'No movement on record.'}</p>}
        </div>
      </section>
    </>
  );
}
