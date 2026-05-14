import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { Flame, Thermometer, Snowflake, ExternalLink } from 'lucide-react'
import { PanelBox } from '@/components/common/PanelBox'
import api from '@/api/client'

interface NewsItem {
  id: string
  source: string
  language: string
  title: string
  summary: string
  url: string
  published: string
  impact: 'HOT' | 'WARM' | 'COLD'
  keywords: string[]
}

type ImpactFilter = 'all' | 'hot' | 'warm' | 'cold'

const IMPACT_META = {
  HOT:  { label: 'Quente',  icon: Flame,       cls: 'text-down bg-down/20 border-down/40' },
  WARM: { label: 'Moderado', icon: Thermometer, cls: 'text-yellow-400 bg-yellow-400/20 border-yellow-400/40' },
  COLD: { label: 'Neutro',  icon: Snowflake,   cls: 'text-neutral bg-border border-border' },
}

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)   return `${Math.floor(diff)}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}min`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return `${Math.floor(diff / 86400)}d`
}

export function NewsPanel() {
  const [items, setItems]     = useState<NewsItem[]>([])
  const [filter, setFilter]   = useState<ImpactFilter>('all')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get(`/news/?impact=${filter}&limit=60`)
        setItems(data.items ?? [])
      } catch { /* feed may still be starting */ }
      finally { setLoading(false) }
    }
    setLoading(true)
    load()
    const iv = setInterval(load, 60_000)
    return () => clearInterval(iv)
  }, [filter])

  const hotCount  = items.filter(i => i.impact === 'HOT').length
  const warmCount = items.filter(i => i.impact === 'WARM').length

  return (
    <PanelBox title="Notícias de Mercado" className="flex flex-col">
      {/* Filter bar */}
      <div className="flex items-center gap-1 px-1 pb-1 border-b border-border">
        {(['all', 'hot', 'warm', 'cold'] as ImpactFilter[]).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={clsx(
              'text-2xs px-2 py-px rounded capitalize transition-colors',
              filter === f ? 'bg-accent text-white' : 'text-neutral hover:text-white',
            )}
          >
            {f === 'all' ? `Todas (${items.length})` :
             f === 'hot' ? `🔥 Quentes (${hotCount})` :
             f === 'warm' ? `🌡 Moderadas (${warmCount})` : '❄ Neutras'}
          </button>
        ))}
        {loading && <span className="text-2xs text-neutral ml-auto">Carregando…</span>}
      </div>

      {/* News list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-px">
        {items.length === 0 && !loading && (
          <div className="text-center text-neutral text-2xs py-6">
            Aguardando feed de notícias…
            <div className="text-2xs mt-1 opacity-60">Fontes: Reuters · Infomoney · Valor · CVM · BCB</div>
          </div>
        )}
        {items.map(item => {
          const meta = IMPACT_META[item.impact]
          const Icon = meta.icon
          const isOpen = expanded === item.id

          return (
            <div
              key={item.id}
              className={clsx(
                'border-l-2 px-2 py-1 hover:bg-border/20 cursor-pointer transition-colors',
                meta.cls,
              )}
              onClick={() => setExpanded(isOpen ? null : item.id)}
            >
              {/* Title row */}
              <div className="flex items-start gap-1">
                <Icon size={10} className="mt-0.5 shrink-0" />
                <span className="text-2xs text-white leading-tight flex-1">{item.title}</span>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="text-neutral hover:text-white shrink-0 mt-0.5"
                >
                  <ExternalLink size={9} />
                </a>
              </div>

              {/* Meta row */}
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-2xs text-neutral">{item.source}</span>
                <span className="text-2xs text-neutral">·</span>
                <span className="text-2xs text-neutral">{timeAgo(item.published)}</span>
                {item.language === 'en' && (
                  <span className="text-2xs text-neutral opacity-50">EN</span>
                )}
                {item.keywords.length > 0 && (
                  <div className="flex gap-0.5 ml-auto">
                    {item.keywords.slice(0, 3).map(kw => (
                      <span key={kw} className="text-2xs bg-border/60 rounded px-0.5 text-neutral">
                        {kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Expanded summary */}
              {isOpen && item.summary && (
                <p className="text-2xs text-neutral mt-1 leading-relaxed border-t border-border/40 pt-1">
                  {item.summary}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Source credits */}
      <div className="text-2xs text-neutral/50 px-1 py-0.5 border-t border-border text-center">
        Reuters · Bloomberg via Infomoney · Valor Econômico · CVM · BCB
      </div>
    </PanelBox>
  )
}
