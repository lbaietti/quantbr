import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

function formatMillions(v: number): string {
  const abs = Math.abs(v)
  if (abs >= 1_000_000_000) return `R$ ${(v / 1_000_000_000).toFixed(2)}B`
  if (abs >= 1_000_000)     return `R$ ${(v / 1_000_000).toFixed(2)}M`
  return `R$ ${v.toLocaleString('pt-BR')}`
}

export function FlowPanel() {
  const flows = useMarketStore((s) => s.flows)

  return (
    <PanelBox title="Fluxo">
      <div className="flex flex-col gap-1">
        {flows.map((f) => (
          <div key={f.label} className="flex flex-col">
            <span className="text-2xs text-neutral uppercase">{f.label}</span>
            <ValueCell value={f.value} className="text-xs" />
            <ValueCell value={f.change} decimals={2} showSign className="text-2xs" />
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
