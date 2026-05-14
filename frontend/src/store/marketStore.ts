import { create } from 'zustand'
import type { Snapshot, Trade, Signal, DIFuture, WorldMarket, Commodity, StockRow, FlowEntry, IndexEntry } from '@/types/market'

interface MarketState {
  snapshots: Record<string, Snapshot>
  trades: Record<string, Trade[]>
  signals: Signal[]
  connected: boolean
  lastUpdate: number

  // Reference data — populated by useReferenceData hook from live backend API
  flows: FlowEntry[]
  indices: IndexEntry[]
  diFutures: DIFuture[]
  worldMarkets: WorldMarket[]
  commodities: Commodity[]
  stockTape: StockRow[]
  referenceLoaded: boolean

  setSnapshot: (snap: Snapshot) => void
  addTrade: (trade: Trade) => void
  addSignal: (signal: Signal) => void
  setConnected: (v: boolean) => void
  setFlows: (v: FlowEntry[]) => void
  setIndices: (v: IndexEntry[]) => void
  setDiFutures: (v: DIFuture[]) => void
  setWorldMarkets: (v: WorldMarket[]) => void
  setCommodities: (v: Commodity[]) => void
  setStockTape: (v: StockRow[]) => void
  setReferenceLoaded: (v: boolean) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  snapshots: {},
  trades: {},
  signals: [],
  connected: false,
  lastUpdate: 0,

  // All empty — data arrives from live API only (see useReferenceData hook)
  flows: [],
  indices: [],
  diFutures: [],
  worldMarkets: [],
  commodities: [],
  stockTape: [],
  referenceLoaded: false,

  setSnapshot: (snap) =>
    set((s) => ({
      snapshots: { ...s.snapshots, [snap.symbol]: snap },
      lastUpdate: Date.now(),
    })),

  addTrade: (trade) =>
    set((s) => {
      const prev = s.trades[trade.symbol] ?? []
      return {
        trades: { ...s.trades, [trade.symbol]: [trade, ...prev].slice(0, 200) },
        lastUpdate: Date.now(),
      }
    }),

  addSignal: (signal) =>
    set((s) => ({ signals: [signal, ...s.signals].slice(0, 100) })),

  setConnected: (v) => set({ connected: v }),
  setFlows: (v) => set({ flows: v }),
  setIndices: (v) => set({ indices: v }),
  setDiFutures: (v) => set({ diFutures: v }),
  setWorldMarkets: (v) => set({ worldMarkets: v }),
  setCommodities: (v) => set({ commodities: v }),
  setStockTape: (v) => set({ stockTape: v }),
  setReferenceLoaded: (v) => set({ referenceLoaded: v }),
}))
