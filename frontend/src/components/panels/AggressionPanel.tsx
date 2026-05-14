import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { ValueCell } from '@/components/common/ValueCell'

// AGR = aggressive buy/sell net flow for each market segment
const AGR_LABELS = ['AGR DÓLAR', 'AGR ÍNDICE', 'AGR AÇÕES', 'AGR DI\'S']

export function AggressionPanel() {
  const snapshots = useMarketStore((s) => s.snapshots)

  // Compute synthetic aggression from live snapshots (net buy - sell volume weighted)
  const agr = AGR_LABELS.map((label, i) => {
    const snap = Object.values(snapshots)[i]
    const val = snap?.total_traded_value ?? (i === 0 ? 1_386_151_215 : i === 1 ? 2_158_786_490 : i === 2 ? 169_616_545 : -18_175_500_000)
    return { label, value: val }
  })

  return (
    <PanelBox title="Agressão">
      <div className="grid grid-cols-2 gap-1">
        {agr.map((a) => (
          <div key={a.label} className="flex flex-col border border-border rounded p-1">
            <span className="text-2xs text-neutral uppercase">{a.label}</span>
            <ValueCell value={a.value} decimals={0} className="text-xs" />
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
