import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'

interface Props { symbol: string }

export function OrderBookPanel({ symbol }: Props) {
  const snap = useMarketStore((s) => s.snapshots[symbol])

  if (!snap) {
    return (
      <PanelBox title={`Book — ${symbol}`}>
        <div className="text-2xs text-neutral text-center py-2">Aguardando…</div>
      </PanelBox>
    )
  }

  return (
    <PanelBox title={`Book — ${symbol}`}>
      <div className="flex gap-1 text-2xs font-mono">
        {/* Bids */}
        <div className="flex-1 flex flex-col gap-px">
          <div className="flex justify-between text-neutral px-1">
            <span>Qtd</span><span>Compra</span>
          </div>
          {snap.bids.map((b, i) => (
            <div key={i} className="flex justify-between px-1 bg-up/10 rounded">
              <span className="text-neutral">{b.qty.toLocaleString()}</span>
              <span className="text-up">{b.price.toFixed(2)}</span>
            </div>
          ))}
        </div>
        {/* Asks */}
        <div className="flex-1 flex flex-col gap-px">
          <div className="flex justify-between text-neutral px-1">
            <span>Venda</span><span>Qtd</span>
          </div>
          {snap.asks.map((a, i) => (
            <div key={i} className="flex justify-between px-1 bg-down/10 rounded">
              <span className="text-down">{a.price.toFixed(2)}</span>
              <span className="text-neutral">{a.qty.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex justify-between text-2xs mt-1 px-1 text-neutral">
        <span>VWAP: <span className="text-white">{snap.vwap?.toFixed(2) ?? '—'}</span></span>
        <span>Spread: <span className="text-white">{snap.spread?.toFixed(2) ?? '—'}</span></span>
      </div>
    </PanelBox>
  )
}
