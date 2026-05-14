import { useEffect, useRef } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useMarketStore } from '@/store/marketStore'
import type { Snapshot, Trade, Signal } from '@/types/market'

const RECONNECT_MS = 3000

export function useMarketWebSocket() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const { setSnapshot, addTrade, addSignal, setConnected } = useMarketStore()
  const wsRef  = useRef<WebSocket | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!accessToken) return

    function connect() {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${proto}://${window.location.host}/ws/market?token=${accessToken}`)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data as string)
          if (msg.type === 'snapshot') {
            const snap = msg as unknown as Snapshot
            setSnapshot(snap)
          } else if (msg.type === 'trade') {
            addTrade(msg as unknown as Trade)
          } else if (msg.signal) {
            addSignal(msg as unknown as Signal)
          }
        } catch {
          // malformed frame — ignore
        }
      }

      ws.onclose = () => {
        setConnected(false)
        timerRef.current = setTimeout(connect, RECONNECT_MS)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      timerRef.current && clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [accessToken])
}
