export interface L2Level {
  price: number
  qty: number
  orders: number
}

export interface Snapshot {
  security_id: number
  symbol: string
  ts: string
  best_bid: number | null
  best_ask: number | null
  bid_qty: number | null
  ask_qty: number | null
  spread: number | null
  mid: number | null
  last_trade_price: number | null
  last_trade_qty: number | null
  vwap: number | null
  total_traded_qty: number | null
  total_traded_value: number | null
  bids: L2Level[]
  asks: L2Level[]
}

export interface Trade {
  security_id: number
  symbol: string
  ts: string
  price: number
  qty: number
  aggressor_side: 'B' | 'S'
}

export interface Signal {
  symbol: string
  signal: string
  direction: 'BUY' | 'SELL' | 'NEUTRAL'
  strength: number
  ts: string
  detail: Record<string, unknown>
}

export interface WsMessage {
  type: 'snapshot' | 'trade'
  security_id: number
  symbol: string
  ts: number
  [key: string]: unknown
}

// ── Static reference data for dashboard panels ────────────────────────────────

export interface FlowEntry {
  label: string
  value: number      // R$ millions
  change: number
}

export interface IndexEntry {
  label: string
  value: number
  change: number
  max: number
  min: number
}

export interface DIFuture {
  code: string       // e.g. "DI1F26"
  rate: number
  change: number
}

export interface WorldMarket {
  symbol: string
  value: number
  change: number
}

export interface Commodity {
  symbol: string
  value: number
  change: number
  unit: string
}

export interface StockRow {
  symbol: string
  last: number
  change: number
  volume: number
}
