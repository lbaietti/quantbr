import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from 'react'
import clsx from 'clsx'
import { X, Send, Bot, Code2, FlaskConical, LineChart, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

type AgentId = 'quantdev' | 'researcher' | 'operator'

interface Message {
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
}

interface AgentDef {
  id:       AgentId
  label:    string
  short:    string
  icon:     typeof Bot
  color:    string
  hint:     string
}

const AGENTS: AgentDef[] = [
  {
    id:    'quantdev',
    label: 'Quant Developer',
    short: 'Dev',
    icon:  Code2,
    color: 'text-accent',
    hint:  'Estratégias, SDK QuantLab, Python, debugging do sandbox…',
  },
  {
    id:    'researcher',
    label: 'Quant Researcher',
    short: 'Research',
    icon:  FlaskConical,
    color: 'text-yellow-400',
    hint:  'Indicadores, matemática, estatísticas, finanças quantitativas…',
  },
  {
    id:    'operator',
    label: 'Quant Operator',
    short: 'Operador',
    icon:  LineChart,
    color: 'text-up',
    hint:  'Operações, leitura de fluxo, gestão de risco, sessão B3…',
  },
]

function useAgentChat(agentId: AgentId) {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const token = useAuthStore(s => s.accessToken)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(async (text: string) => {
    if (!text.trim() || streaming || !token) return

    const userMsg: Message = { role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages([...history, { role: 'assistant', content: '', streaming: true }])
    setStreaming(true)

    abortRef.current = new AbortController()
    let accumulated = ''

    try {
      const res = await fetch('/api/v1/agents/' + agentId + '/chat', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body:    JSON.stringify({ messages: history }),
        signal:  abortRef.current.signal,
      })

      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({ detail: 'Erro de rede' }))
        setMessages(prev => [
          ...prev.slice(0, -1),
          { role: 'assistant', content: `⚠ ${err.detail ?? 'Erro desconhecido'}` },
        ])
        return
      }

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') break
          try {
            const parsed = JSON.parse(payload)
            if (parsed.text) {
              accumulated += parsed.text
              setMessages(prev => [
                ...prev.slice(0, -1),
                { role: 'assistant', content: accumulated, streaming: true },
              ])
            }
            if (parsed.error) {
              accumulated = `⚠ ${parsed.error}`
            }
          } catch { /* ignore malformed chunk */ }
        }
      }
    } catch (e) {
      if ((e as Error).name === 'AbortError') return
      accumulated = '⚠ Erro ao conectar com o agente.'
    } finally {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: accumulated || '…', streaming: false },
      ])
      setStreaming(false)
    }
  }, [agentId, messages, streaming, token])

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const clear = useCallback(() => {
    abortRef.current?.abort()
    setMessages([])
    setStreaming(false)
  }, [])

  return { messages, streaming, send, stop, clear }
}

interface ChatProps {
  agent:    AgentDef
  messages: Message[]
  streaming: boolean
  onSend:   (text: string) => void
  onStop:   () => void
  onClear:  () => void
}

function ChatView({ agent, messages, streaming, onSend, onStop, onClear }: ChatProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const Icon = agent.icon

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    if (!input.trim() || streaming) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Agent header */}
      <div className={clsx('flex items-center gap-2 px-3 py-2 border-b border-border shrink-0', agent.color)}>
        <Icon size={13} />
        <span className="text-xs font-semibold">{agent.label}</span>
        {messages.length > 0 && (
          <button onClick={onClear} className="ml-auto text-neutral hover:text-white text-2xs">
            Limpar
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-2 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-6 px-2 text-center">
            <Icon size={20} className={clsx('opacity-30', agent.color)} />
            <p className="text-2xs text-neutral leading-relaxed">{agent.hint}</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={clsx(
              'text-2xs leading-relaxed rounded px-2 py-1.5 whitespace-pre-wrap',
              msg.role === 'user'
                ? 'bg-accent/20 text-white self-end max-w-[85%] ml-auto'
                : 'bg-border/40 text-white self-start max-w-full',
            )}
          >
            {msg.content}
            {msg.streaming && (
              <span className="inline-block w-1 h-3 bg-white/70 ml-0.5 animate-pulse" />
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex items-end gap-1 px-2 py-2 border-t border-border shrink-0">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escreva sua pergunta… (Enter para enviar)"
          rows={2}
          className="flex-1 bg-surface border border-border rounded text-2xs text-white px-2 py-1 resize-none outline-none focus:border-accent/60 leading-relaxed"
        />
        {streaming ? (
          <button
            onClick={onStop}
            className="shrink-0 p-1.5 rounded bg-down/30 hover:bg-down/50 text-down transition-colors"
            title="Parar"
          >
            <Loader2 size={13} className="animate-spin" />
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={!input.trim()}
            className="shrink-0 p-1.5 rounded bg-accent/80 hover:bg-accent text-white transition-colors disabled:opacity-30"
            title="Enviar (Enter)"
          >
            <Send size={13} />
          </button>
        )}
      </div>
    </div>
  )
}

interface Props {
  open:     boolean
  onClose:  () => void
}

export function AgentSidebar({ open, onClose }: Props) {
  const [activeAgent, setActiveAgent] = useState<AgentId>('quantdev')

  const dev        = useAgentChat('quantdev')
  const researcher = useAgentChat('researcher')
  const operator   = useAgentChat('operator')

  const chats = { quantdev: dev, researcher, operator }
  const current = chats[activeAgent]
  const agentDef = AGENTS.find(a => a.id === activeAgent)!

  return (
    <>
      {/* Backdrop (mobile-style dim) — hidden on wide screens */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <div
        className={clsx(
          'fixed top-0 right-0 h-full z-40 flex flex-col bg-panel border-l border-border transition-transform duration-200',
          'w-80',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-header shrink-0">
          <Bot size={13} className="text-accent" />
          <span className="text-xs font-bold uppercase tracking-widest text-neutral">Agentes IA</span>
          <button onClick={onClose} className="ml-auto text-neutral hover:text-white">
            <X size={13} />
          </button>
        </div>

        {/* Agent tabs */}
        <div className="flex border-b border-border shrink-0">
          {AGENTS.map(a => (
            <button
              key={a.id}
              onClick={() => setActiveAgent(a.id)}
              className={clsx(
                'flex-1 text-2xs py-1.5 transition-colors border-b-2 -mb-px',
                activeAgent === a.id
                  ? clsx('text-white border-accent', a.color)
                  : 'text-neutral border-transparent hover:text-white',
              )}
            >
              {a.short}
            </button>
          ))}
        </div>

        {/* Chat area — grows to fill remaining space */}
        <div className="flex-1 min-h-0">
          <ChatView
            agent={agentDef}
            messages={current.messages}
            streaming={current.streaming}
            onSend={current.send}
            onStop={current.stop}
            onClear={current.clear}
          />
        </div>
      </div>
    </>
  )
}
