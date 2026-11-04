import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { metric } from '@/lib/format'

export interface MetricBarDatum {
  label: string
  value: number | null
}

/** One metric across configurations. The axis starts at zero and values sit on the bars. */
export function MetricBars({ data, metricName }: { data: MetricBarDatum[]; metricName: string }) {
  const known = data.filter((item) => item.value !== null)
  return (
    <div style={{ height: known.length * 30 + 36 }} role="img" aria-label={`${metricName} by configuration. The same values are in the table below.`}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={known} layout="vertical" margin={{ top: 0, right: 58, bottom: 0, left: 0 }} barCategoryGap={8}>
          <XAxis type="number" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tick={{ fontSize: 12, fill: 'var(--ink-3)' }} tickLine={false} axisLine={{ stroke: 'var(--line)' }} />
          <YAxis type="category" dataKey="label" width={210} tick={{ fontSize: 12, fill: 'var(--ink-2)' }} tickLine={false} axisLine={false} interval={0} />
          <Tooltip
            cursor={{ fill: 'var(--panel)' }}
            formatter={(value) => [metric(Number(value)), metricName]}
            contentStyle={{ background: 'var(--raised)', border: '1px solid var(--line)', borderRadius: 6, fontSize: 13, color: 'var(--ink)' }}
            labelStyle={{ color: 'var(--ink)' }}
            itemStyle={{ color: 'var(--ink)' }}
          />
          <Bar dataKey="value" fill="var(--bar)" radius={[0, 4, 4, 0]} barSize={14} isAnimationActive={false}>
            <LabelList dataKey="value" position="right" formatter={(value: unknown) => metric(Number(value))} style={{ fontSize: 12, fill: 'var(--ink)', fontFamily: 'var(--font-mono)' }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
