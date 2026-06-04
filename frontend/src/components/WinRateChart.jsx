import {
  Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts';
import { VERDICT_COLOR } from '../theme/colors.js';

const TOOLTIP_STYLE = {
  background: 'var(--c-panel)',
  border: '1px solid var(--c-twilight)',
  borderRadius: 0,
  fontFamily: 'Cormorant Garamond, serif',
  padding: '0.75rem 1rem',
};

export default function WinRateChart({ data, low = 0.47, high = 0.53 }) {
  const chartData = data.slice()
    .sort((a, b) => b.win_rate - a.win_rate)
    .map((d) => ({ ...d, win_rate_pct: +(d.win_rate * 100).toFixed(2) }));

  return (
    <div className="centered-chart centered-chart--roster" style={{ width: '100%', height: 540, minHeight: 540 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} barCategoryGap="10%" margin={{ top: 24, right: 42, left: 18, bottom: 112 }}>
          <CartesianGrid stroke="var(--c-rule)" vertical={false} />
          <XAxis
            dataKey="name"
            angle={-38}
            textAnchor="end"
            interval={0}
            stroke="var(--c-ash)"
            fontSize={14}
            height={112}
            tickMargin={10}
          />
          <YAxis
            domain={[40, 60]}
            stroke="var(--c-ash)"
            width={62}
            tick={{ fontSize: 13 }}
            label={{
              value: 'WIN RATE %',
              angle: -90,
              position: 'insideLeft',
              offset: 6,
              fill: 'var(--c-ash)',
              fontSize: 11,
              letterSpacing: 3,
              style: { fontFamily: 'Cinzel, serif' },
            }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={{ color: 'var(--c-moonlight)', fontStyle: 'italic', letterSpacing: '0.06em' }}
            itemStyle={{ color: 'var(--c-ghost)' }}
            formatter={(v) => `${v}%`}
          />
          <ReferenceLine y={low * 100} stroke="var(--c-twilight)" strokeDasharray="5 5" />
          <ReferenceLine y={high * 100} stroke="var(--c-moonlight)" strokeDasharray="5 5" />
          <Bar dataKey="win_rate_pct" name="Win rate" barSize={30} radius={[2, 2, 0, 0]}>
            {chartData.map((d, i) => (
              <Cell key={i} fill={VERDICT_COLOR[d.verdict] || VERDICT_COLOR.balanced} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
