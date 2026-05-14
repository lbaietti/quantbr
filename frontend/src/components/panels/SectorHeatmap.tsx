import clsx from 'clsx'
import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'

const SECTORS = [
  { name: 'Petróleo', tickers: ['PETR4', 'RRRP3', 'PRIO3', 'RECV3'] },
  { name: 'Mineração', tickers: ['VALE3', 'CMIN3', 'CSNA3'] },
  { name: 'Bancos', tickers: ['ITUB4', 'BBDC4', 'BBAS3', 'SANB11'] },
  { name: 'Varejo', tickers: ['MGLU3', 'VIIA3', 'AMER3', 'LREN3'] },
  { name: 'Energia', tickers: ['ELET3', 'ENBR3', 'CPFE3', 'EQTL3'] },
  { name: 'Agro', tickers: ['AGRO3', 'SLC3', 'SLCE3'] },
]

function heatColor(change: number): string {
  if (change >  2) return 'bg-up text-black'
  if (change >  0.5) return 'bg-up/60 text-white'
  if (change > -0.5) return 'bg-border text-neutral'
  if (change > -2) return 'bg-down/60 text-white'
  return 'bg-down text-white'
}

export function SectorHeatmap() {
  const snapshots = useMarketStore(s => s.snapshots)

  return (
    <PanelBox title="Heatmap Setorial">
      <div className="flex flex-col gap-1">
        {SECTORS.map(sector => {
          // Average sector change from live snapshots
          const changes = sector.tickers
            .map(t => snapshots[t])
            .filter(Boolean)
            .map(s => {
              const last = s!.last_trade_price ?? s!.mid ?? 0
              const ref  = s!.vwap ?? last
              return ref ? ((last - ref) / ref) * 100 : 0
            })
          const avgChange = changes.length
            ? changes.reduce((a, b) => a + b, 0) / changes.length
            : 0

          return (
            <div key={sector.name}>
              <div className="flex items-center gap-1 mb-0.5">
                <span className="text-2xs text-neutral w-16">{sector.name}</span>
                <span className={clsx('text-2xs px-1 rounded', heatColor(avgChange))}>
                  {avgChange >= 0 ? '+' : ''}{avgChange.toFixed(2)}%
                </span>
              </div>
              <div className="flex gap-px flex-wrap">
                {sector.tickers.map(ticker => {
                  const snap = snapshots[ticker]
                  const last = snap?.last_trade_price ?? snap?.mid ?? 0
                  const ref  = snap?.vwap ?? last
                  const chg  = ref && last ? ((last - ref) / ref) * 100 : 0
                  return (
                    <div
                      key={ticker}
                      className={clsx('text-2xs px-1 py-px rounded font-mono', heatColor(chg))}
                      title={`${ticker}: ${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%`}
                    >
                      {ticker}
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </PanelBox>
  )
}
