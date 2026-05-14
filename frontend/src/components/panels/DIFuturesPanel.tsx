import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

export function DIFuturesPanel() {
  const diFutures = useMarketStore((s) => s.diFutures)

  return (
    <PanelBox title="DI Futuros">
      <div className="flex flex-col gap-px">
        {diFutures.map((di) => (
          <div key={di.code} className="flex justify-between items-center py-px px-1 hover:bg-border/30">
            <span className="text-2xs text-white font-mono">{di.code}</span>
            <ValueCell value={di.change} decimals={2} showSign className="text-2xs" />
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
