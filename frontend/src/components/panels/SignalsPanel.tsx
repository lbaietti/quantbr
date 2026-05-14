import clsx from 'clsx'
import { useMarketStore } from '@/store/marketStore'
import { PanelBox } from '@/components/common/PanelBox'

export function SignalsPanel() {
  const signals = useMarketStore((s) => s.signals)

  return (
    <PanelBox title="Sinais">
      <div className="flex flex-col gap-px overflow-y-auto max-h-28">
        {signals.length === 0 ? (
          <div className="text-2xs text-neutral text-center py-2">Sem sinais</div>
        ) : (
          signals.map((sig, i) => (
            <div key={i} className="flex items-center gap-1 text-2xs px-1 py-px border-b border-border/40">
              <span
                className={clsx(
                  'font-bold w-8 text-center rounded px-0.5',
                  sig.direction === 'BUY' ? 'bg-up/20 text-up' : 'bg-down/20 text-down',
                )}
              >
                {sig.direction === 'BUY' ? 'C' : 'V'}
              </span>
              <span className="text-white font-mono w-12 truncate">{sig.symbol}</span>
              <span className="text-neutral truncate flex-1">{sig.signal}</span>
              <span className="text-neutral w-8 text-right">{(sig.strength * 100).toFixed(0)}%</span>
            </div>
          ))
        )}
      </div>
    </PanelBox>
  )
}
