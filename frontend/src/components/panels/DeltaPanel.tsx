import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, ReferenceLine, Tooltip } from 'recharts'
import { PanelBox } from '@/components/common/PanelBox'
import api from '@/api/client'
import type { DeltaData } from '@/types/orderflow'

interface Props { symbol: string }

export function DeltaPanel({ symbol }: Props) {
  const [data, setData] = useState<DeltaData | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await api.get(`/orderflow/delta/${symbol}`)
        setData(r.data)
      } catch { /* no data yet */ }
    }
    load()
    const iv = setInterval(load, 2000)
    return () => clearInterval(iv)
  }, [symbol])

  if (!data) {
    return <PanelBox title="Delta"><div className="text-2xs text-neutral text-center py-4">Aguardando…</div></PanelBox>
  }

  const histData = data.history.map((v, i) => ({ i, v }))
  const buyPct   = data.buy_pct
  const sellPct  = 100 - buyPct
  const positiveDelta = data.delta >= 0

  return (
    <PanelBox title={`Order Flow Delta — ${symbol}`}>
      {/* Summary row */}
      <div className="flex justify-between text-2xs px-1 mb-1">
        <span className="text-up">C {data.buy_vol.toLocaleString()} ({buyPct.toFixed(1)}%)</span>
        <span className={positiveDelta ? 'text-up font-bold' : 'text-down font-bold'}>
          Δ {data.delta >= 0 ? '+' : ''}{data.delta.toLocaleString()}
        </span>
        <span className="text-down">V {data.sell_vol.toLocaleString()} ({sellPct.toFixed(1)}%)</span>
      </div>

      {/* Buy/sell bar */}
      <div className="flex h-3 rounded overflow-hidden mx-1 mb-2">
        <div className="bg-up transition-all" style={{ width: `${buyPct}%` }} />
        <div className="bg-down transition-all" style={{ width: `${sellPct}%` }} />
      </div>

      {/* Cumulative delta chart */}
      <div className="h-24">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histData} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
            <XAxis hide />
            <YAxis tick={{ fill: '#9e9e9e', fontSize: 8 }} width={32} />
            <ReferenceLine y={0} stroke="#333" />
            <Tooltip
              contentStyle={{ background: '#111', border: '1px solid #1e1e1e', fontSize: 9 }}
              formatter={(v: number) => [v.toLocaleString(), 'Δ Cum.']}
              labelFormatter={() => ''}
            />
            <Bar dataKey="v" radius={[1, 1, 0, 0]}>
              {histData.map((d, i) => (
                <Cell key={i} fill={d.v >= 0 ? '#00c853' : '#f44336'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="text-2xs text-neutral px-1 mt-1">
        Delta Cumulativo: <span className={data.cum_delta >= 0 ? 'text-up' : 'text-down'}>
          {data.cum_delta >= 0 ? '+' : ''}{data.cum_delta.toLocaleString()}
        </span>
      </div>
    </PanelBox>
  )
}
