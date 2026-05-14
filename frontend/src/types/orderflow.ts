export interface TapeEntry {
  symbol: string
  price: number
  qty: number
  aggressor: 'B' | 'S' | 'U'
  ts: number
}

export interface DeltaData {
  symbol: string
  buy_vol: number
  sell_vol: number
  delta: number
  cum_delta: number
  buy_pct: number
  history: number[]
}

export interface VolumeLevel {
  price: number
  buy: number
  sell: number
  total: number
  delta: number
}

export interface VolumeProfileData {
  symbol: string
  poc: number
  vah: number
  val: number
  total_volume: number
  total_delta: number
  levels: VolumeLevel[]
}

export interface ImbalanceData {
  symbol: string
  bid_vol: number
  ask_vol: number
  ratio: number
  imbalance_pct: number
  side: 'BID' | 'ASK' | 'NEUTRAL'
  strong: boolean
}

export interface LabStrategy {
  id: string
  name: string
  author: string
  enabled: boolean
  signal_count: number
  error_count: number
  last_error: string | null
  created_at: string
}

export interface LabSignal {
  source: string
  strategy: string
  strategy_id: string
  symbol: string
  direction: 'BUY' | 'SELL' | 'NEUTRAL'
  strength: number
  ts: string
  meta: Record<string, unknown>
}
