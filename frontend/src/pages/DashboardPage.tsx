import { useState } from 'react'
import clsx from 'clsx'
import { Bot } from 'lucide-react'
import { useMarketWebSocket } from '@/hooks/useWebSocket'
import { useReferenceData } from '@/hooks/useReferenceData'
import { Header } from '@/components/layout/Header'
import { AgentSidebar } from '@/components/agents/AgentSidebar'

// Overview panels
import { FlowPanel }         from '@/components/panels/FlowPanel'
import { IndicesPanel }      from '@/components/panels/IndicesPanel'
import { ForceGauges }       from '@/components/panels/ForceGauges'
import { AggressionPanel }   from '@/components/panels/AggressionPanel'
import { DIFuturesPanel }    from '@/components/panels/DIFuturesPanel'
import { WorldMarketsPanel } from '@/components/panels/WorldMarketsPanel'
import { CommoditiesPanel }  from '@/components/panels/CommoditiesPanel'
import { StockTape }         from '@/components/panels/StockTape'
import { FlowChart }         from '@/components/panels/FlowChart'
import { SignalsPanel }      from '@/components/panels/SignalsPanel'

// Tape & Order Flow panels
import { TimeAndTrade }      from '@/components/panels/TimeAndTrade'
import { OrderBookPanel }    from '@/components/panels/OrderBookPanel'
import { DeltaPanel }        from '@/components/panels/DeltaPanel'
import { VolumeProfileChart } from '@/components/panels/VolumeProfileChart'

// Macro & News panels
import { DIYieldCurve }      from '@/components/panels/DIYieldCurve'
import { SectorHeatmap }     from '@/components/panels/SectorHeatmap'
import { EconomicCalendar }  from '@/components/panels/EconomicCalendar'
import { NewsPanel }         from '@/components/panels/NewsPanel'

// QuantLab
import { QuantLabPanel }     from '@/components/panels/QuantLabPanel'

type Tab = 'overview' | 'tape' | 'macro' | 'lab'

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Visão Geral' },
  { id: 'tape',     label: 'Tape & Order Flow' },
  { id: 'macro',    label: 'Macro & Notícias' },
  { id: 'lab',      label: 'QuantLab' },
]

// Default symbol for tape/orderflow views — could be made user-selectable later
const DEFAULT_SYMBOL = 'PETR4'

function TabBar({
  active, onChange, agentOpen, onAgentToggle,
}: {
  active: Tab
  onChange: (t: Tab) => void
  agentOpen: boolean
  onAgentToggle: () => void
}) {
  return (
    <div className="flex items-center gap-px px-1 border-b border-border bg-surface shrink-0">
      {TABS.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={clsx(
            'text-2xs px-3 py-1.5 transition-colors border-b-2 -mb-px',
            active === t.id
              ? 'text-white border-accent'
              : 'text-neutral border-transparent hover:text-white hover:border-border',
          )}
        >
          {t.label}
        </button>
      ))}

      {/* Agent sidebar toggle — flush to the right */}
      <button
        onClick={onAgentToggle}
        className={clsx(
          'ml-auto flex items-center gap-1 text-2xs px-2 py-1 rounded transition-colors',
          agentOpen
            ? 'text-white bg-accent/30'
            : 'text-neutral hover:text-white hover:bg-border/40',
        )}
        title="Agentes IA"
      >
        <Bot size={11} />
        <span>Agentes</span>
      </button>
    </div>
  )
}

function OverviewTab() {
  return (
    <div className="flex-1 grid grid-cols-[160px_160px_1fr_120px_130px] grid-rows-[1fr_140px] gap-1 p-1 overflow-hidden min-h-0">
      {/* Col 1: Flow + Indices */}
      <div className="flex flex-col gap-1 row-span-1">
        <FlowPanel />
        <IndicesPanel />
      </div>

      {/* Col 2: Force + Aggression + Signals */}
      <div className="flex flex-col gap-1 row-span-1">
        <ForceGauges />
        <AggressionPanel />
        <SignalsPanel />
      </div>

      {/* Col 3: Stock tape */}
      <StockTape />

      {/* Col 4: DI Futures */}
      <DIFuturesPanel />

      {/* Col 5: World + Commodities */}
      <div className="flex flex-col gap-1 row-span-1">
        <WorldMarketsPanel />
        <CommoditiesPanel />
      </div>

      {/* Row 2: Flow chart */}
      <div className="col-span-3">
        <FlowChart />
      </div>

      <div className="col-span-2" />
    </div>
  )
}

function TapeTab({ symbol }: { symbol: string }) {
  return (
    <div className="flex-1 grid grid-cols-[240px_1fr_200px] gap-1 p-1 overflow-hidden min-h-0">
      {/* Col 1: Order Book + Delta */}
      <div className="flex flex-col gap-1">
        <OrderBookPanel symbol={symbol} />
        <DeltaPanel symbol={symbol} />
      </div>

      {/* Col 2: Times & Trade (full height) */}
      <TimeAndTrade symbol={symbol} />

      {/* Col 3: Volume Profile */}
      <VolumeProfileChart symbol={symbol} />
    </div>
  )
}

function MacroTab() {
  return (
    <div className="flex-1 grid grid-cols-[260px_1fr_300px] grid-rows-[1fr_1fr] gap-1 p-1 overflow-hidden min-h-0">
      {/* Col 1 row 1: DI Yield Curve */}
      <DIYieldCurve />

      {/* Col 2 rows 1-2: Sector Heatmap — must precede EconomicCalendar in DOM for correct auto-placement */}
      <div className="row-span-2 flex flex-col">
        <SectorHeatmap />
      </div>

      {/* Col 3 rows 1-2: News */}
      <div className="row-span-2 flex flex-col">
        <NewsPanel />
      </div>

      {/* Col 1 row 2: Economic Calendar */}
      <EconomicCalendar />
    </div>
  )
}

function LabTab() {
  return (
    <div className="flex-1 p-1 overflow-hidden min-h-0">
      <QuantLabPanel />
    </div>
  )
}

export function DashboardPage() {
  useMarketWebSocket()
  useReferenceData()

  const [tab, setTab]           = useState<Tab>('overview')
  const [agentOpen, setAgentOpen] = useState(false)

  return (
    <div className="flex flex-col h-screen bg-surface text-white overflow-hidden">
      <Header />
      <TabBar
        active={tab}
        onChange={setTab}
        agentOpen={agentOpen}
        onAgentToggle={() => setAgentOpen(o => !o)}
      />

      {/* Main content — shifts left when sidebar is open to avoid overlap */}
      <div className={clsx('flex-1 min-h-0 transition-[margin] duration-200', agentOpen && 'mr-80')}>
        {tab === 'overview' && <OverviewTab />}
        {tab === 'tape'     && <TapeTab symbol={DEFAULT_SYMBOL} />}
        {tab === 'macro'    && <MacroTab />}
        {tab === 'lab'      && <LabTab />}
      </div>

      <AgentSidebar open={agentOpen} onClose={() => setAgentOpen(false)} />
    </div>
  )
}
