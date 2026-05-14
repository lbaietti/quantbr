import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

export function WorldMarketsPanel() {
  const worldMarkets = useMarketStore((s) => s.worldMarkets)

  return (
    <PanelBox title="Mundo">
      <div className="grid grid-cols-2 gap-px">
        {worldMarkets.map((m) => (
          <div key={m.symbol} className="flex justify-between items-center py-px px-1">
            <span className="text-2xs text-neutral">{m.symbol}</span>
            <ValueCell value={m.change} decimals={2} showSign className="text-2xs" />
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
