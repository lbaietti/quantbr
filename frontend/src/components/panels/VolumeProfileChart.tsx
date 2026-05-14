import { useEffect, useState } from 'react'
import { PanelBox } from '@/components/common/PanelBox'
import api from '@/api/client'
import type { VolumeProfileData } from '@/types/orderflow'

interface Props { symbol: string }

export function VolumeProfileChart({ symbol }: Props) {
  const [data, setData] = useState<VolumeProfileData | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await api.get(`/orderflow/volume-profile/${symbol}`)
        setData(r.data)
      } catch { /* no data yet */ }
    }
    load()
    const iv = setInterval(load, 3000)
    return () => clearInterval(iv)
  }, [symbol])

  if (!data || data.levels.length === 0) {
    return <PanelBox title="Volume Profile"><div className="text-2xs text-neutral text-center py-4">Aguardando…</div></PanelBox>
  }

  const maxTotal = Math.max(...data.levels.map(l => l.total), 1)
  // Show top 30 levels by price range
  const levels = [...data.levels].reverse().slice(0, 30)

  return (
    <PanelBox title={`Volume Profile — ${symbol}`}>
      <div className="flex justify-between text-2xs px-1 mb-1">
        <span className="text-neutral">POC <span className="text-white">{data.poc.toFixed(2)}</span></span>
        <span className="text-up">VAH <span className="text-white">{data.vah.toFixed(2)}</span></span>
        <span className="text-down">VAL <span className="text-white">{data.val.toFixed(2)}</span></span>
      </div>

      <div className="flex flex-col gap-px overflow-y-auto max-h-52">
        {levels.map((l, i) => {
          const isPoc = l.price === data.poc
          const inVa  = l.price <= data.vah && l.price >= data.val
          const buyW  = (l.buy  / maxTotal) * 100
          const sellW = (l.sell / maxTotal) * 100

          return (
            <div key={i} className="flex items-center gap-1 text-2xs font-mono">
              <span className={`w-12 text-right text-xs ${isPoc ? 'text-yellow-400 font-bold' : inVa ? 'text-white' : 'text-neutral'}`}>
                {l.price.toFixed(2)}
              </span>
              <div className="flex-1 flex h-2.5 gap-px">
                {/* Buy side */}
                <div className="flex-1 flex justify-end">
                  <div className="bg-up/70 h-full rounded-l" style={{ width: `${buyW}%` }} />
                </div>
                {/* Sell side */}
                <div className="flex-1">
                  <div className="bg-down/70 h-full rounded-r" style={{ width: `${sellW}%` }} />
                </div>
              </div>
              <span className={`w-16 text-right ${l.delta >= 0 ? 'text-up' : 'text-down'}`}>
                {l.delta >= 0 ? '+' : ''}{l.delta.toLocaleString()}
              </span>
            </div>
          )
        })}
      </div>

      <div className="flex justify-between text-2xs text-neutral px-1 mt-1 border-t border-border pt-1">
        <span>Vol total: <span className="text-white">{data.total_volume.toLocaleString()}</span></span>
        <span>Δ total: <span className={data.total_delta >= 0 ? 'text-up' : 'text-down'}>
          {data.total_delta >= 0 ? '+' : ''}{data.total_delta.toLocaleString()}
        </span></span>
      </div>
    </PanelBox>
  )
}
