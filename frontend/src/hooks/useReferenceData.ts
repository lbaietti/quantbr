/**
 * Fetches live B3/BCB reference data from the backend (indices, DI futures,
 * PTAX, SELIC) and populates the market store.
 * Runs once on mount, then refreshes every 30 seconds.
 */
import { useEffect } from 'react'
import api from '@/api/client'
import { useMarketStore } from '@/store/marketStore'
import type { IndexEntry, DIFuture } from '@/types/market'

export function useReferenceData() {
  const { setIndices, setDiFutures, setReferenceLoaded } = useMarketStore()

  useEffect(() => {
    async function load() {
      try {
        const { data } = await api.get('/reference/all')

        // Indices
        if (Array.isArray(data.indices) && data.indices.length > 0) {
          const indices: IndexEntry[] = data.indices.map((d: Record<string, unknown>) => ({
            label:  String(d.label ?? ''),
            value:  Number(d.value ?? 0),
            change: Number(d.change ?? 0),
            max:    Number(d.max   ?? 0),
            min:    Number(d.min   ?? 0),
          }))
          setIndices(indices)
        }

        // DI Futures
        if (Array.isArray(data.di_futures) && data.di_futures.length > 0) {
          const dis: DIFuture[] = data.di_futures.map((d: Record<string, unknown>) => ({
            code:   String(d.code   ?? ''),
            rate:   Number(d.rate   ?? 0),
            change: Number(d.change ?? 0),
          }))
          setDiFutures(dis)
        }

        setReferenceLoaded(true)
      } catch {
        // Backend may not be ready yet — retry next cycle
      }
    }

    load()
    const iv = setInterval(load, 30_000)
    return () => clearInterval(iv)
  }, [])
}
