import { PanelBox } from '@/components/common/PanelBox'

// Static Brazilian economic calendar — in production this would come from a data provider
const EVENTS = [
  { date: '15/05', time: '09:00', event: 'IPCA-15 Maio',         impact: 'ALTO',  prev: '0,44%',  exp: '0,41%' },
  { date: '22/05', time: '09:00', event: 'IPCA Semanal',         impact: 'MÉDIO', prev: '0,26%',  exp: '-' },
  { date: '29/05', time: '—',     event: 'Reunião COPOM (SELIC)', impact: 'ALTO',  prev: '10,50%', exp: '10,25%' },
  { date: '06/06', time: '09:00', event: 'IPCA Maio',            impact: 'ALTO',  prev: '0,38%',  exp: '0,35%' },
  { date: '13/06', time: '09:30', event: 'IGP-M Junho',          impact: 'MÉDIO', prev: '0,44%',  exp: '-' },
  { date: '18/06', time: '09:00', event: 'IPCA-15 Junho',        impact: 'ALTO',  prev: '0,44%',  exp: '-' },
  { date: '18/06', time: '16:00', event: 'FED Rate Decision',    impact: 'ALTO',  prev: '5,50%',  exp: '5,50%' },
]

const IMPACT_COLOR: Record<string, string> = {
  ALTO:  'text-down bg-down/20',
  MÉDIO: 'text-yellow-400 bg-yellow-400/20',
  BAIXO: 'text-neutral bg-border',
}

export function EconomicCalendar() {
  return (
    <PanelBox title="Calendário Econômico">
      <div className="flex flex-col gap-px overflow-y-auto max-h-52">
        {/* Header */}
        <div className="grid grid-cols-[44px_36px_1fr_44px_48px_48px] gap-1 text-2xs text-neutral px-1 border-b border-border pb-px">
          <span>Data</span><span>Hora</span><span>Evento</span>
          <span className="text-center">Impacto</span>
          <span className="text-right">Ant.</span>
          <span className="text-right">Esp.</span>
        </div>
        {EVENTS.map((e, i) => (
          <div
            key={i}
            className="grid grid-cols-[44px_36px_1fr_44px_48px_48px] gap-1 text-2xs px-1 py-0.5 hover:bg-border/20"
          >
            <span className="text-neutral font-mono">{e.date}</span>
            <span className="text-neutral font-mono">{e.time}</span>
            <span className="text-white truncate">{e.event}</span>
            <span className={`text-center rounded px-0.5 text-2xs ${IMPACT_COLOR[e.impact] ?? ''}`}>
              {e.impact}
            </span>
            <span className="text-neutral text-right font-mono">{e.prev}</span>
            <span className="text-white text-right font-mono">{e.exp}</span>
          </div>
        ))}
      </div>
    </PanelBox>
  )
}
