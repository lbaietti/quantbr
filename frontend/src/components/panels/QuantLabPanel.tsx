import { useState, useEffect, useRef, useCallback } from 'react'
import clsx from 'clsx'
import { Play, Trash2, ChevronRight, AlertCircle, CheckCircle, Circle } from 'lucide-react'
import { PanelBox } from '@/components/common/PanelBox'
import api from '@/api/client'
import { useAuthStore } from '@/store/authStore'

interface Strategy {
  id: string
  name: string
  description: string
  symbols: string[]
  active: boolean
  error: string | null
  created_at: string
}

interface LabSignal {
  strategy_id: string
  strategy_name: string
  symbol: string
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  reason: string
  ts: number
}

interface ValidationResult {
  valid: boolean
  errors: string[]
  strategy_name: string | null
}

const STARTER = `from quantlab import BaseStrategy, TradeEvent, Signal, EMA, RSI

class MyCrossStrategy(BaseStrategy):
    name        = "EMA Cross"
    description = "Sinal quando EMA9 cruza EMA21"
    symbols     = ["PETR4", "VALE3"]

    def init(self):
        self.fast = EMA(9)
        self.slow = EMA(21)
        self.rsi  = RSI(14)

    def on_trade(self, ev: TradeEvent):
        self.fast.update(ev.price)
        self.slow.update(ev.price)
        self.rsi.update(ev.price)

        if not self.fast.ready or not self.slow.ready:
            return

        if self.fast.value > self.slow.value and self.rsi.value < 70:
            self.emit(Signal(
                action     = "BUY",
                symbol     = ev.symbol,
                confidence = 0.75,
                reason     = f"EMA9 acima de EMA21, RSI={self.rsi.value:.1f}",
            ))
        elif self.fast.value < self.slow.value and self.rsi.value > 30:
            self.emit(Signal(
                action     = "SELL",
                symbol     = ev.symbol,
                confidence = 0.70,
                reason     = f"EMA9 abaixo de EMA21, RSI={self.rsi.value:.1f}",
            ))
`

const ACTION_COLOR: Record<'BUY' | 'SELL' | 'HOLD', string> = {
  BUY:  'text-up bg-up/10 border-up/40',
  SELL: 'text-down bg-down/10 border-down/40',
  HOLD: 'text-neutral bg-border/20 border-border',
}

function timeFmt(ts: number) {
  return new Date(ts / 1_000_000).toLocaleTimeString('pt-BR')
}

const PANEL_CLS = 'bg-panel border border-border rounded flex flex-col min-h-0'
const TITLE_CLS = 'text-2xs font-bold uppercase tracking-widest text-neutral px-2 py-1 border-b border-border shrink-0'

export function QuantLabPanel() {
  const [code, setCode]             = useState(STARTER)
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [signals, setSignals]       = useState<LabSignal[]>([])
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [validating, setValidating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [lineCount, setLineCount]   = useState(1)
  const token = useAuthStore(s => s.accessToken)
  const wsRef = useRef<WebSocket | null>(null)

  const loadStrategies = useCallback(async () => {
    try {
      const r = await api.get('/lab/strategies')
      setStrategies(r.data.strategies ?? [])
    } catch { /* not yet authenticated */ }
  }, [])

  useEffect(() => { loadStrategies() }, [loadStrategies])

  useEffect(() => {
    setLineCount(code.split('\n').length)
  }, [code])

  useEffect(() => {
    if (wsRef.current) { wsRef.current.close(); wsRef.current = null }
    if (!selectedId || !token) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/lab/${selectedId}?token=${token}`)
    wsRef.current = ws

    ws.onmessage = (ev) => {
      try {
        const sig: LabSignal = JSON.parse(ev.data)
        setSignals(prev => [sig, ...prev].slice(0, 100))
      } catch { /* ignore */ }
    }

    return () => ws.close()
  }, [selectedId, token])

  async function validate() {
    setValidating(true)
    setValidation(null)
    try {
      const r = await api.post('/lab/validate', { source: code })
      setValidation(r.data)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setValidation({ valid: false, errors: [detail ?? 'Erro de rede'], strategy_name: null })
    } finally {
      setValidating(false)
    }
  }

  async function submit() {
    setSubmitting(true)
    try {
      await api.post('/lab/strategies', { source: code })
      await loadStrategies()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setValidation({ valid: false, errors: [detail ?? 'Erro ao submeter'], strategy_name: null })
    } finally {
      setSubmitting(false)
    }
  }

  async function deleteStrategy(id: string) {
    try {
      await api.delete(`/lab/strategies/${id}`)
      if (selectedId === id) setSelectedId(null)
      await loadStrategies()
    } catch { /* ignore */ }
  }

  async function toggleActive(s: Strategy) {
    try {
      await api.patch(`/lab/strategies/${s.id}`, { active: !s.active })
      await loadStrategies()
    } catch { /* ignore */ }
  }

  const selectedName = strategies.find(s => s.id === selectedId)?.name ?? null

  return (
    <div className="flex h-full gap-1">

      {/* ── Left: Editor — manual flex column (PanelBox wraps in non-flex div) ── */}
      <div className={clsx(PANEL_CLS, 'flex-1 min-w-0')}>
        <div className={TITLE_CLS}>Editor — QuantLab</div>

        {/* Toolbar */}
        <div className="flex items-center gap-1 px-1 py-1 border-b border-border shrink-0">
          <button
            onClick={validate}
            disabled={validating}
            className="flex items-center gap-1 text-2xs px-2 py-px rounded bg-border hover:bg-accent/30 text-neutral hover:text-white transition-colors disabled:opacity-50"
          >
            <CheckCircle size={10} />
            {validating ? 'Validando…' : 'Validar'}
          </button>
          <button
            onClick={submit}
            disabled={submitting || (validation !== null && !validation.valid)}
            className="flex items-center gap-1 text-2xs px-2 py-px rounded bg-accent/80 hover:bg-accent text-white transition-colors disabled:opacity-50"
          >
            <Play size={10} />
            {submitting ? 'Enviando…' : 'Enviar Estratégia'}
          </button>
        </div>

        {/* Validation feedback */}
        {validation && (
          <div className={clsx(
            'flex items-start gap-1 px-2 py-1 text-2xs border-b border-border shrink-0',
            validation.valid ? 'text-up bg-up/10' : 'text-down bg-down/10',
          )}>
            {validation.valid
              ? <><CheckCircle size={10} className="mt-px shrink-0" /> Válido — estratégia "{validation.strategy_name}"</>
              : <><AlertCircle size={10} className="mt-px shrink-0" />
                  <span className="flex flex-col gap-px">
                    {validation.errors.map((err, i) => <span key={i}>{err}</span>)}
                  </span>
                </>
            }
          </div>
        )}

        {/* Code editor — flex-1 fills remaining height */}
        <div className="flex flex-1 min-h-0 overflow-hidden font-mono text-xs">
          {/* Line numbers */}
          <div className="flex flex-col items-end px-2 py-2 select-none text-neutral/40 bg-surface leading-5 min-w-[2.5rem] overflow-hidden shrink-0">
            {Array.from({ length: lineCount }, (_, i) => (
              <span key={i}>{i + 1}</span>
            ))}
          </div>
          {/* Textarea */}
          <textarea
            value={code}
            onChange={e => { setCode(e.target.value); setValidation(null) }}
            className="flex-1 bg-surface text-white resize-none outline-none p-2 leading-5 overflow-auto"
            spellCheck={false}
          />
        </div>
      </div>

      {/* ── Middle: Strategy list ─────────────────────────────── */}
      <div className="w-52 flex flex-col gap-1 min-h-0">
        <div className={clsx(PANEL_CLS, 'flex-1')}>
          <div className={TITLE_CLS}>Estratégias</div>
          <div className="flex-1 overflow-y-auto p-1">
            {strategies.length === 0 && (
              <div className="text-2xs text-neutral text-center py-4">
                Nenhuma estratégia ainda.<br />
                <span className="opacity-60">Escreva e envie acima.</span>
              </div>
            )}
            <div className="flex flex-col gap-px">
              {strategies.map(s => (
                <div
                  key={s.id}
                  onClick={() => { setSelectedId(s.id); setSignals([]) }}
                  className={clsx(
                    'flex flex-col gap-0.5 px-2 py-1 rounded cursor-pointer border transition-colors',
                    selectedId === s.id
                      ? 'border-accent bg-accent/10'
                      : 'border-transparent hover:border-border hover:bg-border/20',
                  )}
                >
                  <div className="flex items-center gap-1">
                    <button
                      onClick={e => { e.stopPropagation(); toggleActive(s) }}
                      className="shrink-0"
                      title={s.active ? 'Pausar' : 'Ativar'}
                    >
                      <Circle
                        size={8}
                        className={s.active ? 'fill-up text-up' : 'fill-neutral/30 text-neutral/30'}
                      />
                    </button>
                    <span className="text-2xs text-white font-medium truncate flex-1">{s.name}</span>
                    <button
                      onClick={e => { e.stopPropagation(); deleteStrategy(s.id) }}
                      className="text-neutral hover:text-down shrink-0"
                      title="Deletar"
                    >
                      <Trash2 size={9} />
                    </button>
                  </div>
                  {s.description && (
                    <span className="text-2xs text-neutral leading-tight truncate pl-3">{s.description}</span>
                  )}
                  {s.symbols.length > 0 && (
                    <div className="flex gap-0.5 pl-3 flex-wrap">
                      {s.symbols.map(sym => (
                        <span key={sym} className="text-2xs bg-border/60 rounded px-0.5 text-neutral">{sym}</span>
                      ))}
                    </div>
                  )}
                  {s.error && (
                    <span className="text-2xs text-down pl-3 truncate">{s.error}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Right: Signal stream ──────────────────────────────── */}
      <div className="w-60 flex flex-col gap-1 min-h-0">
        <div className={clsx(PANEL_CLS, 'flex-1')}>
          <div className={TITLE_CLS}>
            {selectedName ? `Sinais — ${selectedName}` : 'Sinais'}
          </div>
          <div className="flex-1 overflow-y-auto p-1">
            {!selectedId && (
              <div className="text-2xs text-neutral text-center py-4 flex flex-col items-center gap-1">
                <ChevronRight size={14} className="opacity-40" />
                Selecione uma estratégia
              </div>
            )}
            {selectedId && signals.length === 0 && (
              <div className="text-2xs text-neutral text-center py-4">
                Aguardando sinais…<br />
                <span className="opacity-60 text-2xs">O feed precisa estar ativo.</span>
              </div>
            )}
            <div className="flex flex-col gap-px">
              {signals.map((sig, i) => (
                <div
                  key={i}
                  className={clsx('flex flex-col gap-0.5 px-2 py-1 border-l-2 rounded-r', ACTION_COLOR[sig.action])}
                >
                  <div className="flex items-center gap-1">
                    <span className="text-2xs font-bold">{sig.action}</span>
                    <span className="text-2xs text-white">{sig.symbol}</span>
                    <span className="text-2xs text-neutral ml-auto">{(sig.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div className="text-2xs text-neutral leading-tight">{sig.reason}</div>
                  <div className="text-2xs text-neutral/50">{timeFmt(sig.ts)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}
