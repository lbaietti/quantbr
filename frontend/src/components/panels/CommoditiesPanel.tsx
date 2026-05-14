import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

export function CommoditiesPanel() {
  const commodities = useMarketStore((s) => s.commodities)

  return (
    <PanelBox title="Commodities">
      <div className="flex flex-col gap-px">
        {commodities.map((c) => (
          <div key={c.symbol} className="flex justify-between items-center py-px px-1">
            <span className="text-2xs text-neutral w-10">{c.symbol}</span>
            <span className="text-2xs text-white font-mono">{c.value.toFixed(2)}</span>
            <ValueCell value={c.change} decimals={2} showSign className="text-2xs" />
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
