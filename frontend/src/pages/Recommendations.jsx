// Recommendations — case files on each flagged hero.
import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { SectionHead } from '../components/Bureau.jsx';

function RecCard({ f }) {
  return (
    <div className="rec-card animate-fade-up">
      <div className="rec-head">
        <div className="name entity-cell rec-name">
          {f.image_url ? <img className="entity-icon hero" src={f.image_url} alt="" loading="lazy" /> : <span className="entity-icon placeholder" />}
          <span>{f.name}</span>
        </div>
        <span className={`verdict-pill ${f.verdict}`}>{f.verdict}</span>
      </div>
      <div className="rec-meta">
        <span>Win rate <b className="mono">{(f.win_rate * 100).toFixed(1)}%</b></span>
        <span>Pick rate <b className="mono">{(f.pick_rate * 100).toFixed(1)}%</b></span>
        <span>KDA <b className="mono">{f.kda.toFixed(2)}</b></span>
        <span>Avg damage <b className="mono">{Math.round(f.avg_damage).toLocaleString()}</b></span>
        <span>Deviation <b className="mono">{f.score.toFixed(3)}</b></span>
        {typeof f.ml_predicted_win_rate === 'number' && (
          <>
            <span>ML baseline <b className="mono">{(f.ml_predicted_win_rate * 100).toFixed(1)}%</b></span>
            <span>ML gap <b className="mono">{`${f.ml_observed_gap >= 0 ? '+' : ''}${(f.ml_observed_gap * 100).toFixed(1)}pp`}</b></span>
          </>
        )}
        {f.ml_balance_class && (
          <span>ML class <b className="mono">{f.ml_balance_class}</b></span>
        )}
      </div>
      <div className="rec-section">
        <div className="heading">i · Evidence</div>
        <p>{f.rationale}</p>
      </div>
      {(f.ml_interpretation || f.ml_balance_class) && (
        <div className="rec-section ml-evidence">
          <div className="heading">ML · Model cross-check</div>
          {f.ml_balance_class && (
            <p style={{ marginBottom: 'var(--s-2)' }}>
              <span className="ml-class-pill">classification: {f.ml_balance_class} · confidence {((f.ml_balance_confidence || 0) * 100).toFixed(0)}%</span>
            </p>
          )}
          {f.ml_interpretation && <p>{f.ml_interpretation}</p>}
        </div>
      )}
      <div className="rec-section">
        <div className="heading">ii · Mechanical reasoning</div>
        <p>{f.mechanical_reasoning}</p>
      </div>
      <div className="rec-section">
        <div className="heading">iii · Macro impact</div>
        <p>{f.macro_impact}</p>
      </div>
      <div className="rec-section action">
        <div className="heading">iv · Recommendation</div>
        <p>{f.recommendation}</p>
      </div>
    </div>
  );
}

function Section({ id, index, title, sub, items }) {
  return (
    <section id={id} className="section animate-fade-up">
      <SectionHead
        index={index}
        title={title}
        sub={sub}
        right={<span className="muted mono">{items.length} on file</span>}
      />
      {items.length === 0
        ? <div className="card"><p className="muted">No entries in this dossier.</p></div>
        : <div className="grid" style={{ gap: 'var(--s-4)' }}>
            {items.map((f) => <RecCard key={f.hero_id} f={f} />)}
          </div>}
    </section>
  );
}

function MLStatusCard({ status }) {
  if (!status) return null;
  const reg = status.regression || {};
  const clf = status.classification || {};
  const featureCount = Array.isArray(status.features) ? status.features.length : 0;
  return (
    <section id="ml-model" className="section animate-fade-up">
      <SectionHead
        index={0}
        title="ML Balance Model"
        sub="Supervised regression and classification used as a second opinion for recommendations"
        right={<span className="muted mono">{status.available ? 'trained' : 'waiting for data'}</span>}
      />
      <div className="card ml-status-card">
        <div className="ml-status-grid">
          <div className="ml-stat"><div className="label">Regression</div><div className="value">{reg.model_type || 'Random Forest'}</div></div>
          <div className="ml-stat"><div className="label">Classifier</div><div className="value">{clf.model_type || 'Random Forest'}</div></div>
          <div className="ml-stat"><div className="label">Training rows</div><div className="value">{status.training_rows ?? '—'}</div></div>
          <div className="ml-stat"><div className="label">Features</div><div className="value">{featureCount || '—'}</div></div>
        </div>
        <p>{status.message}</p>
        <div className="ml-pipeline">
          <span>Public API stats</span>
          <span>Feature formatting</span>
          <span>Random Forest models</span>
          <span>Prediction + recommendation</span>
        </div>
      </div>
    </section>
  );
}

export default function Recommendations() {
  const [flags, setFlags] = useState([]);
  const [modelStatus, setModelStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    api.balanceFlags()
      .then((f) => { if (!cancelled) setFlags(f); })
      .catch((e) => {
        if (!cancelled) {
          setError(e.response?.status === 404
            ? 'No case files filed. Run Refresh from the Overview page.'
            : `The wire has gone cold — ${e.message}`);
        }
      });

    // Model status is useful, but it should never block recommendation cards.
    // If the ML endpoint is still training or temporarily fails, the flags
    // still render and the model card can stay empty.
    api.modelStatus()
      .then((m) => { if (!cancelled) setModelStatus(m); })
      .catch(() => { if (!cancelled) setModelStatus(null); });

    return () => { cancelled = true; };
  }, []);

  const op  = flags.filter((f) => f.verdict === 'overpowered');
  const up  = flags.filter((f) => f.verdict === 'underpowered');
  const bal = flags.filter((f) => f.verdict === 'balanced');

  return (
    <>
      {error && <div className="error">{error}</div>}
      <MLStatusCard status={modelStatus} />
      <Section id="overpowered"  index={1} title="Overpowered"  sub="Specific nerf paths with mechanical reasoning" items={op}  />
      <Section id="underpowered" index={2} title="Underpowered" sub="Targeted buffs tied to the failing mechanic"   items={up}  />
      <Section id="balanced"     index={3} title="Balanced"     sub="No-action heroes — file for periodic review"   items={bal} />
    </>
  );
}
