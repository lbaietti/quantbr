# Arquitetura do Sistema

## Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              B3 (Exchange)                              │
│   UDP Multicast (UMDF)                    TCP FIX (STEP)               │
└────────────┬──────────────────────────────────────┬────────────────────┘
             │                                       │
             ▼                                       │
┌────────────────────────┐                           │
│      Feed (C++)        │                           │
│                        │                           │
│  UMDFParser            │                           │
│  ├── handle_snapshot   │                           │
│  └── handle_incremental│                           │
│                        │                           │
│  BookManager           │◄──────────────────────────┘
│  └── OrderBook[]       │         StepClient
│      ├── apply_bid     │         (order entry)
│      ├── apply_ask     │
│      └── apply_trade   │
│                        │
│  SessionManager        │
│  ├── Channel A (UDP)   │
│  └── Channel B (UDP)   │
│                        │
│  ZmqPublisher          │
│  ├── "snapshot" topic  │──── ZMQ PUB ────►
│  └── "trade" topic     │
└────────────────────────┘
                                ┌────────────────────────────────────┐
                                │         Backend (Python)           │
                  ZMQ SUB ────► │  FeedSubscriber                    │
                                │  └── parse JSON frames             │
                                │       ├── snapshot → Redis PUBLISH │
                                │       └── trade → SignalEngine      │
                                │                                     │
                                │  SignalEngine                       │
                                │  ├── per-instrument state           │
                                │  │   ├── RSI (Wilder, 14)          │
                                │  │   ├── BollingerBands (20, 2σ)   │
                                │  │   ├── EMA (9, 21)               │
                                │  │   └── SessionVWAP               │
                                │  └── signals → Redis PUBLISH        │
                                │                                     │
                                │  FastAPI                            │
                                │  ├── POST /api/v1/auth/login        │
                                │  ├── POST /api/v1/auth/refresh      │
                                │  ├── GET  /api/v1/market/snapshot   │
                                │  ├── GET  /api/v1/market/trades     │
                                │  ├── GET  /api/v1/signals/:symbol   │
                                │  └── WS   /ws/market[/:symbol]      │
                                │                                     │
                                │  PostgreSQL (async SQLAlchemy)      │
                                │  ├── users                          │
                                │  ├── instruments                    │
                                │  ├── market_snapshots               │
                                │  ├── trades                         │
                                │  └── audit_logs                     │
                                │                                     │
                                │  Redis                              │
                                │  ├── pub/sub (market:snapshot:*)    │
                                │  ├── pub/sub (market:trade:*)       │
                                │  ├── pub/sub (signal:*)             │
                                │  └── cache:snapshot:{symbol}        │
                                └──────────────────┬─────────────────┘
                                                   │ WebSocket
                                                   ▼
                                ┌────────────────────────────────────┐
                                │        Frontend (React)            │
                                │                                    │
                                │  useWebSocket (auto-reconnect)     │
                                │  └── Zustand marketStore           │
                                │       ├── snapshots{}              │
                                │       ├── trades{}                 │
                                │       └── signals[]                │
                                │                                    │
                                │  Dashboard Panels                  │
                                │  ├── FlowPanel                     │
                                │  ├── IndicesPanel                  │
                                │  ├── ForceGauges (SVG)             │
                                │  ├── AggressionPanel               │
                                │  ├── DIFuturesPanel                │
                                │  ├── WorldMarketsPanel             │
                                │  ├── CommoditiesPanel              │
                                │  ├── StockTape                     │
                                │  ├── FlowChart (Recharts)          │
                                │  ├── SignalsPanel                  │
                                │  └── OrderBookPanel                │
                                └────────────────────────────────────┘
```

## Decisões de Design

### Feed — Por que C++20?

O feed precisa processar pacotes UDP com latência de sub-milissegundo. C++20 com flags `-O3 -march=native` garante acesso direto à memória sem GC. Os dois canais redundantes (A e B) do UMDF são consumidos em threads separadas, desduplicados pelo número de sequência no parser.

### Backend — Por que ZMQ entre o Feed e o Python?

ZMQ PUB/SUB desacopla completamente o feed do backend. O feed não conhece nem depende do backend — se o backend reiniciar, o feed continua publicando sem perder conexão. O backend reconecta automaticamente.

### Backend — Por que Redis como hub de pub/sub?

O Redis permite que múltiplas instâncias do backend (scale horizontal) e múltiplos clientes WebSocket recebam os mesmos dados sem que o FeedSubscriber precise saber quantos estão conectados. O padrão `market:snapshot:*` é uma P-subscription que cobre todos os símbolos de uma vez.

### Frontend — Por que Zustand?

Zustand é mais leve que Redux e não exige providers. O `marketStore` centraliza todo o estado de mercado; qualquer painel lê diretamente do store sem prop drilling. A persistência do refresh token usa `zustand/middleware/persist` com `localStorage`.

### Segurança — Fluxo de Autenticação

```
POST /auth/login
    └── bcrypt.verify(password, hash)
    └── create_access_token (30 min)  ← usado em cada requisição
    └── create_refresh_token (7 dias) ← armazenado no localStorage

WebSocket /ws/market?token=<access_token>
    └── decode_token() antes de aceitar conexão
    └── fecha com 1008 se inválido

Axios interceptor
    └── 401 recebido → POST /auth/refresh → retry automático
    └── refresh falhou → logout() + redirect /login
```

## Escalabilidade

| Componente | Escala horizontal? | Como |
|------------|-------------------|------|
| Feed C++ | Não (single instance por canal B3) | Redundância via canais A+B |
| Backend | Sim | Múltiplas instâncias compartilham Redis + PostgreSQL |
| Frontend | Sim (CDN) | Assets estáticos após `npm run build` |
| Redis | Sim | Redis Cluster ou Redis Sentinel |
| PostgreSQL | Sim (read replicas) | Separar leituras em réplicas |
