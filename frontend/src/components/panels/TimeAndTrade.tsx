import { useState, useEffect, useRef } from 'react'
import clsx from 'clsx'
import { PanelBox } from '@/components/common/PanelBox'
import type { TapeEntry } from '@/types/orderflow'
import { useAuthStore } from '@/store/authStore'

interface Props {
  symbol: string
  maxRows?: number
}

const AGG_COLOR = {
  B: 'text-up bg-up/10',
  S: 'text-down bg-down/10',
  U: 'text-neutral bg-border/20',
}

function fmt(n: number) {
  return n.toLocaleString('pt-BR')
}

export function TimeAndTrade({ symbol, maxRows = 200 }: Props) {
  const [tape, setTape]       = useState<TapeEntry[]>([])
  const [minQty, setMinQty]   = useState(0)
  const [paused, setPaused]   = useState(false)
  const token = useAuthStore(s => s.accessToken)
  const bufRef = useRef<TapeEntry[]>([])

  useEffect(() => {
    if (!token || !symbol) return
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/market/${symbol}?token=${token}`)

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type !== 'trade') return
        const entry: TapeEntry = {
          symbol: msg.symbol,
          price:  msg.price,
          qty:    msg.qty,
          aggressor: msg.aggressor_side ?? 'U',
          ts:     msg.ts,
        }
        bufRef.current = [entry, ...bufRef.current].slice(0, maxRows)
        if (!paused) setTape([...bufRef.current])
      } catch { /* ignore */ }
    }

    return () => ws.close()
  }, [token, symbol, paused])

  const filtered = tape.filter(t => t.qty >= minQty)

  return (
    <PanelBox title={`Times & Trade — ${symbol}`} className="flex flex-col">
      {/* Controls */}
      <div className="flex items-center gap-2 px-1 pb-1 border-b border-border">
        <span className="text-2xs text-neutral">Qtd mín:</span>
        {[0, 100, 500, 1000, 5000].map(q => (
          <button
            key={q}
            onClick={() => setMinQty(q)}
            className={clsx(
              'text-2xs px-1 rounded',
              minQty === q ? 'bg-accent text-white' : 'text-neutral hover:text-white',
            )}
          >
            {q === 0 ? 'Todos' : fmt(q)}
          </button>
        ))}
        <button
          onClick={() => setPaused(p => !p)}
          className={clsx('ml-auto text-2xs px-2 rounded', paused ? 'bg-down/30 text-down' : 'text-neutral hover:text-white')}
        >
          {paused ? '▶ Retomar' : '⏸ Pausar'}
        </button>
      </div>

      {/* Header */}
      <div className="grid grid-cols-[70px_80px_80px_40px] gap-1 px-1 py-px text-2xs text-neutral border-b border-border">
        <span>Hora</span><span className="text-right">Preço</span>
        <span className="text-right">Qtd</span><span className="text-center">Agr</span>
      </div>

      {/* Tape */}
      <div className="flex-1 overflow-y-auto">
        {filtered.map((t, i) => {
          const time = new Date(t.ts / 1_000_000).toLocaleTimeString('pt-BR')
          return (
            <div
              key={i}
              className={clsx(
                'grid grid-cols-[70px_80px_80px_40px] gap-1 px-1 py-px text-2xs font-mono',
                AGG_COLOR[t.aggressor] ?? AGG_COLOR.U,
              )}
            >
              <span className="text-neutral">{time}</span>
              <span className="text-right">{t.price.toFixed(2)}</span>
              <span className="text-right font-bold">{fmt(t.qty)}</span>
              <span className="text-center">{t.aggressor}</span>
            </div>
          )
        })}
        {filtered.length === 0 && (
          <div className="text-center text-neutral text-2xs py-4">Aguardando trades…</div>
        )}
      </div>
    </PanelBox>
  )
}
