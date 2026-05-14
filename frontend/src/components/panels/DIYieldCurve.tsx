import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export function DIYieldCurve() {
  const diFutures = useMarketStore(s => s.diFutures)

  // Build yield curve data from DI futures
  const curveData = diFutures.map(di => ({
    maturity: di.code.replace('DI1', ''),
    rate: di.rate,
    change: di.change,
  }))

  const minRate = Math.min(...curveData.map(d => d.rate)) - 0.5
  const maxRate = Math.max(...curveData.map(d => d.rate)) + 0.5

  return (
    <PanelBox title="Curva DI — ETTJ" className="h-48">
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={curveData} margin={{ top: 4, right: 8, bottom: 4, left: 24 }}>
            <XAxis
              dataKey="maturity"
              tick={{ fill: '#9e9e9e', fontSize: 9 }}
            />
            <YAxis
              domain={[minRate, maxRate]}
              tick={{ fill: '#9e9e9e', fontSize: 9 }}
              tickFormatter={(v: number) => v.toFixed(2) + '%'}
              width={36}
            />
            <Tooltip
              contentStyle={{ background: '#111', border: '1px solid #1e1e1e', fontSize: 10 }}
              formatter={(v: number) => [v.toFixed(4) + '%', 'Taxa DI']}
            />
            <ReferenceLine y={0} stroke="#333" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="#1565c0"
              strokeWidth={2}
              dot={{ fill: '#1565c0', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Mini table */}
      <div className="grid grid-cols-4 gap-px text-2xs px-1 border-t border-border pt-1">
        {diFutures.map(di => (
          <div key={di.code} className="flex flex-col items-center">
            <span className="text-neutral">{di.code.replace('DI1', '')}</span>
            <span className={di.change >= 0 ? 'text-up' : 'text-down'}>
              {di.change >= 0 ? '+' : ''}{di.change.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
