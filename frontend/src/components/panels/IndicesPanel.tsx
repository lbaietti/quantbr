import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

export function IndicesPanel() {
  const indices = useMarketStore((s) => s.indices)

  return (
    <PanelBox title="Índices">
      <div className="flex flex-col gap-2">
        {indices.map((idx) => (
          <div key={idx.label} className="flex flex-col border-b border-border pb-1 last:border-0">
            <div className="flex justify-between items-center">
              <span className="text-2xs text-neutral uppercase">{idx.label}</span>
              <ValueCell value={idx.change} decimals={2} showSign className="text-2xs" />
            </div>
            <ValueCell value={idx.value} decimals={1} className="text-xs font-bold" />
            <div className="flex justify-between text-2xs text-neutral">
              <span>MÁX <span className="text-up">{idx.max.toFixed(0)}</span></span>
              <span>MÍN <span className="text-down">{idx.min.toFixed(0)}</span></span>
            </div>
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
