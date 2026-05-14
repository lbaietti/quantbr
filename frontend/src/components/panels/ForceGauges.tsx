import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'
import { GaugeChart } from '@/components/common/GaugeChart'

export function ForceGauges() {
  const flows = useMarketStore((s) => s.flows)

  // Normalise flows to -100…+100 for gauge display
  const max = flows.reduce((m, f) => Math.max(m, Math.abs(f.value)), 1)
  const gauges = flows.map((f) => ({
    label: f.label,
    value: (f.value / max) * 100,
  }))

  return (
    <PanelBox title="Força Relativa">
      <div className="flex justify-around items-center gap-1 py-1">
        {gauges.map((g) => (
          <GaugeChart key={g.label} label={g.label} value={g.value} size={90} />
        ))}
      </div>
    </PanelBox>
  )
}
