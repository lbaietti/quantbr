import { useMarketStore } from '@/store/marketStore'
import { useAuth } from '@/hooks/useAuth'
import { LogOut, Wifi, WifiOff } from 'lucide-react'
import clsx from 'clsx'

export function Header() {
  const connected  = useMarketStore((s) => s.connected)
  const lastUpdate = useMarketStore((s) => s.lastUpdate)
  const { logout } = useAuth()

  const time = lastUpdate
    ? new Date(lastUpdate).toLocaleTimeString('pt-BR')
    : '—'

  return (
    <header className="flex items-center justify-between px-3 py-1 bg-header border-b border-border h-8">
      <div className="flex items-center gap-3">
        <span className="text-white font-bold text-sm tracking-widest">QUANTBR</span>
        <span className="text-2xs text-neutral">Dashboard B3</span>
      </div>

      <div className="flex items-center gap-4">
        <div className={clsx('flex items-center gap-1 text-2xs', connected ? 'text-up' : 'text-down')}>
          {connected ? <Wifi size={11} /> : <WifiOff size={11} />}
          <span>{connected ? `AO VIVO · ${time}` : 'DESCONECTADO'}</span>
        </div>
        <button
          onClick={logout}
          className="text-neutral hover:text-white transition-colors"
          title="Sair"
        >
          <LogOut size={13} />
        </button>
      </div>
    </header>
  )
}
