# Backend Python — Documentação

API REST + WebSocket em FastAPI com autenticação JWT, RBAC, auditoria e motor de indicadores/sinais.

## Estrutura de Módulos

```
app/
├── main.py           — FastAPI app, lifespan, middleware, exception handler
├── config.py         — Settings via pydantic-settings (lê .env)
├── security/
│   ├── auth.py       — JWT (HS256), bcrypt password hashing
│   ├── rbac.py       — Roles: viewer < trader < admin
│   └── audit.py      — Structured audit log (ISO 27001 A.12)
├── db/
│   ├── base.py       — SQLAlchemy async engine
│   └── session.py    — AsyncSession dependency
├── models/           — ORM tables
│   ├── user.py
│   ├── instrument.py
│   ├── snapshot.py
│   ├── trade.py
│   └── audit_log.py
├── schemas/          — Pydantic v2 I/O schemas
│   ├── auth.py
│   ├── market.py
│   └── signal.py
├── feed/
│   └── subscriber.py — ZMQ SUB → Redis pub/sub + SignalEngine
├── indicators/       — Indicadores incrementais O(1) por tick
│   ├── base.py       — Indicator ABC + RollingBuffer
│   ├── moving_average.py — SMA, EMA
│   ├── rsi.py        — Wilder RSI (14)
│   ├── bollinger.py  — Bollinger Bands (20, 2σ)
│   └── vwap.py       — Session VWAP
├── signals/
│   ├── base.py       — BaseSignal ABC + SignalResult
│   └── engine.py     — SignalEngine: estado por instrumento + 3 sinais built-in
└── api/
    ├── health.py     — GET /healthz, GET /readyz
    └── v1/
        ├── auth.py      — POST /auth/login, POST /auth/refresh
        ├── market.py    — GET /market/instruments, /market/snapshot/:sym, /market/trades/:sym
        ├── signals.py   — GET /signals/:symbol
        ├── reference.py — GET /reference/all (macro: indices, DI futures, PTAX, SELIC, sectors)
        ├── news.py      — GET /news (aggregated RSS feed)
        ├── lab.py       — QuantLab sandbox CRUD + run/validate
        ├── agents.py    — POST /agents/{quantdev|researcher|operator}/chat (SSE streaming)
        └── ws.py        — WS /ws/market[/:symbol]
```

## Endpoints REST

### Autenticação

#### `POST /api/v1/auth/login`

```json
// Request
{ "email": "user@example.com", "password": "minimo8chars" }

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}

// Response 401
{ "detail": "Invalid credentials" }
```

#### `POST /api/v1/auth/refresh`

```json
// Request
{ "refresh_token": "eyJ..." }

// Response 200 — novos tokens
{ "access_token": "eyJ...", "refresh_token": "eyJ...", ... }
```

### Mercado

Todos os endpoints de mercado requerem `Authorization: Bearer <access_token>`.

#### `GET /api/v1/market/instruments`

Retorna lista de instrumentos cadastrados.

```json
[
  {
    "security_id": 12345,
    "symbol": "PETR4",
    "security_type": "CS",
    "currency": "BRL",
    "lot_size": 100
  }
]
```

#### `GET /api/v1/market/snapshot/{symbol}`

Retorna o snapshot mais recente (Redis cache → PostgreSQL fallback).

```json
{
  "security_id": 12345,
  "symbol": "PETR4",
  "ts": "2024-05-14T13:30:00Z",
  "best_bid": 38.49,
  "best_ask": 38.51,
  "spread": 0.02,
  "mid": 38.50,
  "vwap": 38.42,
  "last_trade_price": 38.50,
  "bids": [{"price": 38.49, "qty": 500, "orders": 0}],
  "asks": [{"price": 38.51, "qty": 300, "orders": 0}]
}
```

#### `GET /api/v1/market/trades/{symbol}?limit=50`

Últimos trades de um símbolo. Limite máximo: 500.

### Sinais

#### `GET /api/v1/signals/{symbol}?limit=20`

Sinais mais recentes gerados pelo motor.

```json
[
  {
    "symbol": "PETR4",
    "signal": "RSI_OVERSOLD",
    "direction": "BUY",
    "strength": 0.72,
    "ts": "2024-05-14T13:31:00Z",
    "detail": {"rsi": 27.43}
  }
]
```

## WebSocket

### `WS /ws/market/{symbol}?token=<access_token>`

Recebe snapshots, trades e sinais do símbolo em tempo real.

### `WS /ws/market?token=<access_token>`

Recebe dados de **todos** os símbolos simultaneamente (P-subscription `market:*`).

#### Mensagens recebidas

```json
// Snapshot
{"type": "snapshot", "symbol": "PETR4", "best_bid": 38.49, ...}

// Trade
{"type": "trade", "symbol": "PETR4", "price": 38.50, "qty": 100, "aggressor_side": "B"}

// Sinal
{"symbol": "PETR4", "signal": "VWAP_CROSS", "direction": "BUY", "strength": 0.015, ...}
```

O token é validado **antes** de aceitar a conexão. Conexão inválida → close 1008.

## Indicadores

Todos os indicadores são **incrementais** — `update(value)` é O(1).

| Classe | Parâmetros | Método principal |
|--------|------------|-----------------|
| `SMA` | `period` | `update(float)` → `value() → float\|None` |
| `EMA` | `period` | `update(float)` → `value()` |
| `RSI` | `period=14` | `update(float)` → `value()` (retorna None até `period` ticks) |
| `BollingerBands` | `period=20, num_std=2.0` | `update(float)` → `value() → BandValue\|None` |
| `SessionVWAP` | — | `update_trade(price, qty)` → `value()` |

`RSI` retorna `50.0` quando mercado completamente flat (avg_gain=0 e avg_loss=0).

## Motor de Sinais

O `SignalEngine` mantém um `_InstrumentState` por símbolo com RSI, BB, EMA9/21, VWAP.

```python
engine = SignalEngine()

# Chamado a cada trade recebido do feed
results: list[SignalResult] = engine.on_trade("PETR4", price=38.50, qty=100)

# Reset no início de cada sessão
engine.session_reset("PETR4")  # ou engine.session_reset() para todos

# Registrar sinal customizado
engine.register(MeuSinal())
```

### Sinais Built-in

| Sinal | Trigger | Direção |
|-------|---------|---------|
| `RSI_OVERSOLD` | RSI < 30 | BUY |
| `RSI_OVERBOUGHT` | RSI > 70 | SELL |
| `BB_LOWER_TOUCH` | pct_b < 0.05 | BUY |
| `BB_UPPER_TOUCH` | pct_b > 0.95 | SELL |
| `VWAP_CROSS` | preço cruza VWAP | BUY/SELL |

`strength` varia de 0.0 a 1.0 indicando intensidade do sinal.

## Roles (RBAC)

| Role | Permissões |
|------|-----------|
| `viewer` | Leitura de market data, snapshots, trades, sinais |
| `trader` | viewer + envio de ordens (futuro) |
| `admin` | trader + gestão de usuários |

```python
# Uso em endpoints
@router.get("/endpoint")
async def ep(user: Annotated[TokenData, Depends(require_role(Role.VIEWER))]):
    ...
```

## Auditoria

Todo evento de segurança é logado como JSON estruturado:

```json
{
  "event": "auth.login.success",
  "subject": "user@example.com",
  "ip": "192.168.1.10",
  "timestamp": "2024-05-14T13:30:00Z",
  "level": "info"
}
```

Eventos auditados: `auth.login.success`, `auth.login.failure`, `auth.logout`, `auth.token.refresh`, `authz.access.denied`, `trading.order.sent`, `trading.order.cancel`, `admin.user.created`, `admin.user.deleted`, `admin.config.changed`.

## QuantLab — Sandbox de Estratégias

O QuantLab permite que usuários `trader`/`admin` submetam estratégias Python que são executadas num sandbox com protecção em duas camadas:

1. **AST check** — verifica o código antes de executar; bloqueia `import`, `exec`, `eval`, `open`, acesso a dunders
2. **Thread pool timeout** — exec corre em `ThreadPoolExecutor` com timeout de 5 s; loops infinitos não bloqueiam o event loop

```
POST /api/v1/lab/strategies          — submete estratégia (source Python)
GET  /api/v1/lab/strategies          — lista estratégias do utilizador
GET  /api/v1/lab/strategies/{name}   — detalhe de uma estratégia
PATCH /api/v1/lab/strategies/{name}  — activa/desactiva estratégia
DELETE /api/v1/lab/strategies/{name} — remove estratégia
POST /api/v1/lab/strategies/{name}/run      — executa com dados de mercado
POST /api/v1/lab/strategies/{name}/validate — valida AST sem executar
```

## Agentes IA (Anthropic Claude API)

Três agentes especializados, acessíveis via SSE streaming:

```
POST /api/v1/agents/quantdev/chat    — Quant Developer
POST /api/v1/agents/researcher/chat  — Quant Researcher
POST /api/v1/agents/operator/chat    — Quant Operator
```

Requer `ANTHROPIC_API_KEY` configurado. Rate limiting por utilizador via Redis (`AGENT_MESSAGES_PER_HOUR`, padrão: 20). Respostas chegam como Server-Sent Events com campos `data: {"text": "..."}`.

## Dados de Referência e Notícias

```
GET /api/v1/reference/all   — índices B3, futuros DI, PTAX, SELIC, mercados mundiais, commodities
GET /api/v1/news            — feed agregado de notícias (Infomoney, Reuters, Valor, BCB, CVM)
```

Estes endpoints consultam APIs públicas e RSS feeds com caching no backend. Não requerem feed ZMQ ativo.

## Saúde e Métricas

```bash
GET /healthz        → {"status": "ok"}                    (liveness)
GET /readyz         → {"status": "ok", "checks": {...}}   (readiness)
GET /metrics        → Prometheus text format
```

O `/readyz` verifica conectividade com Redis. Em Kubernetes use `/healthz` como liveness probe e `/readyz` como readiness probe.
