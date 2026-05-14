import clsx from 'clsx'
import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'

// Build the tape from live snapshots — fall back to empty rows
export function StockTape() {
  const snapshots = useMarketStore((s) => s.snapshots)

  const rows = Object.values(snapshots)
    .sort((a, b) => a.symbol.localeCompare(b.symbol))

  const empty = rows.length === 0

  return (
    <PanelBox title="Tape" className="overflow-hidden">
      <div className="flex flex-col gap-px overflow-y-auto max-h-full">
        {empty ? (
          <div className="text-2xs text-neutral text-center py-4">Aguardando dados…</div>
        ) : (
          rows.map((snap) => {
            const last   = snap.last_trade_price ?? snap.mid ?? 0
            const prev   = snap.vwap ?? last
            const change = prev ? ((last - prev) / prev) * 100 : 0
            const up     = change >= 0
            return (
              <div
                key={snap.symbol}
                className={clsx(
                  'flex justify-between items-center px-1 py-px rounded text-2xs font-mono',
                  up ? 'bg-up/10' : 'bg-down/10',
                )}
              >
                <span className="text-white w-12 truncate">{snap.symbol}</span>
                <span className={up ? 'text-up' : 'text-down'}>{last.toFixed(2)}</span>
                <span className={clsx('w-12 text-right', up ? 'text-up' : 'text-down')}>
                  {up ? '+' : ''}{change.toFixed(2)}%
                </span>
              </div>
            )
          })
        )}
      </div>
    </PanelBox>
  )
}
