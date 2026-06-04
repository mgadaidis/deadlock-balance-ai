import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis, ReferenceLine,
} from 'recharts';

const TOOLTIP_STYLE = {
  background: 'var(--c-panel)',
  border: '1px solid var(--c-twilight)',
  borderRadius: 0,
  fontFamily: 'Cormorant Garamond, serif',
  padding: '0.75rem 1rem',
};

function quantile(values, q) {
  if (!values.length) return 0;
  const s = values.slice().sort((a, b) => a - b);
  const pos = (s.length - 1) * q;
  const b = Math.floor(pos);
  const rest = pos - b;
  return s[b] + (s[b + 1] !== undefined ? rest * (s[b + 1] - s[b]) : 0);
}

export default function NetWorthChart({ data }) {
  const sorted = data
    .filter((d) => d.avg_net_worth > 0)
    .slice()
    .sort((a, b) => b.avg_net_worth - a.avg_net_worth)
    .slice(0, 20);

  const q75 = quantile(data.map((d) => d.avg_net_worth || 0), 0.75);
  const chartHeight = Math.max(600, sorted.length * 32);

  return (
    <div className="centered-chart centered-chart--networth" style={{ width: '100%', height: chartHeight, minHeight: 640 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={sorted} layout="vertical" barCategoryGap="18%" margin={{ top: 18, right: 24, left: 14, bottom: 18 }}>
          <CartesianGrid stroke="var(--c-rule)" horizontal={true} vertical={false} />
          <XAxis type="number" stroke="var(--c-ash)" tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 12 }} />
          <YAxis
            type="category"
            dataKey="name"
            stroke="var(--c-ash)"
            width={220}
            interval={0}
            minTickGap={0}
            tick={{ fontSize: 14, letterSpacing: 0.4, fontFamily: 'Cormorant Garamond, serif' }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={{ color: 'var(--c-moonlight)', fontStyle: 'italic', letterSpacing: '0.06em' }}
            itemStyle={{ color: 'var(--c-ghost)' }}
            formatter={(v) => Math.round(v).toLocaleString()}
          />
          <ReferenceLine
            x={q75}
            stroke="var(--c-moonlight)"
            strokeDasharray="5 5"
            label={{
              value: 'spike threshold',
              fill: 'var(--c-moonlight)',
              position: 'insideTop',
              fontSize: 10,
              letterSpacing: 2,
              style: { fontFamily: 'Cinzel, serif' },
            }}
          />
          <Bar dataKey="avg_net_worth" name="Avg net worth" barSize={18} radius={[0, 2, 2, 0]}>
            {sorted.map((d, i) => (
              <Cell key={i} fill={d.avg_net_worth >= q75 ? 'var(--c-moonlight)' : 'var(--c-twilight)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
