import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'

interface ChartPoint {
  time: string
  estrangeiro: number
  bancos: number
  pessoaFisica: number
}

// For now build synthetic history from current flows — in production this
// would come from a REST endpoint /api/v1/market/flow-history
function buildHistory(flows: { label: string; value: number }[]): ChartPoint[] {
  const now = Date.now()
  const points: ChartPoint[] = []
  for (let i = 30; i >= 0; i--) {
    const t = new Date(now - i * 60_000)
    const hh = t.getHours().toString().padStart(2, '0')
    const mm = t.getMinutes().toString().padStart(2, '0')
    const noise = () => (Math.random() - 0.5) * 0.05
    points.push({
      time: `${hh}:${mm}`,
      estrangeiro:  (flows[0]?.value ?? 0) * (1 + noise()),
      bancos:       (flows[1]?.value ?? 0) * (1 + noise()),
      pessoaFisica: (flows[2]?.value ?? 0) * (1 + noise()),
    })
  }
  return points
}

const fmt = (v: number) => {
  const abs = Math.abs(v)
  if (abs >= 1e9) return `${(v / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `${(v / 1e6).toFixed(0)}M`
  return v.toFixed(0)
}

export function FlowChart() {
  const flows = useMarketStore((s) => s.flows)
  const data  = useMemo(() => buildHistory(flows), [flows])

  return (
    <PanelBox title="Fluxo Intraday" className="h-36">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 40 }}>
          <XAxis dataKey="time" tick={{ fill: '#9e9e9e', fontSize: 9 }} interval={5} />
          <YAxis tick={{ fill: '#9e9e9e', fontSize: 9 }} tickFormatter={fmt} width={38} />
          <Tooltip
            contentStyle={{ background: '#111', border: '1px solid #1e1e1e', fontSize: 10 }}
            formatter={(v: number) => fmt(v)}
          />
          <Legend wrapperStyle={{ fontSize: 9 }} />
          <Line dataKey="estrangeiro"  stroke="#1565c0" dot={false} strokeWidth={1.5} name="Estrangeiro" />
          <Line dataKey="bancos"       stroke="#f44336" dot={false} strokeWidth={1.5} name="Bancos" />
          <Line dataKey="pessoaFisica" stroke="#00c853" dot={false} strokeWidth={1.5} name="Pessoa Física" />
        </LineChart>
      </ResponsiveContainer>
    </PanelBox>
  )
}
