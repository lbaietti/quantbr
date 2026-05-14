# Frontend React — Documentação

Dashboard quantitativo ao vivo, estilo ProfitPro, para o mercado B3.

## Stack

| Biblioteca | Versão | Uso |
|-----------|--------|-----|
| React | 18.3 | UI component framework |
| TypeScript | 5.4 | Tipagem estática |
| Vite | 5.3 | Build tool + dev server |
| TailwindCSS | 3.4 | Utility-first styling |
| Zustand | 4.5 | Estado global (auth + market) |
| React Query | 5.x | Cache de chamadas REST |
| Recharts | 2.x | Gráficos (FlowChart) |
| React Router | 6.x | Roteamento SPA |
| Axios | 1.7 | HTTP client com interceptors |
| Lucide React | 0.390 | Ícones SVG |

## Estrutura de Arquivos

```
src/
├── api/
│   └── client.ts          — Axios com interceptor JWT auto-refresh
├── components/
│   ├── common/
│   │   ├── GaugeChart.tsx — Gauge SVG circular (Força Relativa)
│   │   ├── PanelBox.tsx   — Container padrão dos painéis
│   │   └── ValueCell.tsx  — Valor colorido red/green
│   ├── layout/
│   │   └── Header.tsx     — Barra superior: logo, status WS, logout
│   └── panels/
│       ├── FlowPanel.tsx       — Fluxo Estrangeiro/Bancos/Pessoa Física
│       ├── IndicesPanel.tsx    — Índice/Dólar/Ações com máx/mín
│       ├── ForceGauges.tsx     — Gauges SVG de força relativa
│       ├── AggressionPanel.tsx — AGR Dólar/Índice/Ações/DI's
│       ├── DIFuturesPanel.tsx  — Tape de futuros DI (DI1F26–DI1F33)
│       ├── WorldMarketsPanel.tsx — SPX, DOW, FTSE100, EURUSD…
│       ├── CommoditiesPanel.tsx — BRENT, WTI, OURO, PRATA, GÁS
│       ├── StockTape.tsx       — Lista ao vivo de ações com variação
│       ├── FlowChart.tsx       — Série temporal de fluxos (Recharts)
│       ├── SignalsPanel.tsx    — Sinais gerados pelo motor
│       └── OrderBookPanel.tsx  — Book L2 top-5 bid/ask de um símbolo
├── hooks/
│   ├── useAuth.ts         — Abstração sobre authStore
│   └── useWebSocket.ts    — WS com auto-reconnect (3s), roteamento de mensagens
├── components/
│   ├── agents/
│   │   └── AgentSidebar.tsx   — Floating sidebar com os 3 agentes IA (SSE streaming)
│   ├── common/
│   │   ├── GaugeChart.tsx     — Gauge SVG semicircular
│   │   ├── PanelBox.tsx       — Container padrão dos painéis
│   │   └── ValueCell.tsx      — Valor colorido red/green
│   ├── layout/
│   │   └── Header.tsx         — Logo, status WS, hora, botão Agentes, logout
│   └── panels/
│       ├── FlowPanel.tsx           — Fluxo Estrangeiro/Bancos/Pessoa Física
│       ├── IndicesPanel.tsx        — IBOV, IFIX, SMLL, IDIV
│       ├── ForceGauges.tsx         — Gauges de força relativa (SVG)
│       ├── AggressionPanel.tsx     — AGR Dólar/Índice/Ações/DI's
│       ├── DIFuturesPanel.tsx      — Tape de futuros DI (DI1F26–DI1F33)
│       ├── WorldMarketsPanel.tsx   — SPX, DOW, FTSE100, EURUSD…
│       ├── CommoditiesPanel.tsx    — BRENT, WTI, OURO, PRATA, GÁS
│       ├── StockTape.tsx           — Lista ao vivo de ações com variação
│       ├── FlowChart.tsx           — Série temporal de fluxos (Recharts)
│       ├── SignalsPanel.tsx        — Sinais do motor com direcção e força
│       ├── OrderBookPanel.tsx      — Book L2 top-5 bid/ask
│       ├── TimeAndTrade.tsx        — Time & Sales (tape de negócios)
│       ├── DeltaPanel.tsx          — Order Flow Delta acumulado
│       ├── VolumeProfileChart.tsx  — Volume Profile da sessão (SVG barras)
│       ├── DIYieldCurve.tsx        — Curva de juros DI (Recharts LineChart)
│       ├── SectorHeatmap.tsx       — Heatmap de sectores B3
│       ├── EconomicCalendar.tsx    — Calendário de eventos económicos
│       ├── NewsPanel.tsx           — Feed de notícias em tempo real
│       └── QuantLabPanel.tsx       — Sandbox de estratégias Python
├── pages/
│   ├── LoginPage.tsx      — Formulário de login
│   └── DashboardPage.tsx  — 4 workspaces com TabBar + AgentSidebar flutuante
├── store/
│   ├── authStore.ts       — Zustand: tokens, login, refresh, logout
│   └── marketStore.ts     — Zustand: snapshots, trades, signals, dados dos painéis
├── types/
│   ├── auth.ts            — LoginRequest, TokenResponse
│   └── market.ts          — Snapshot, Trade, Signal, FlowEntry, DIFuture, etc.
├── App.tsx                — BrowserRouter + PrivateRoute
├── main.tsx               — ReactDOM.createRoot + QueryClientProvider
└── index.css              — Tailwind base + scrollbar customizado
```

## Estado Global

### `authStore` (Zustand + persist)

```typescript
const { isAuthenticated, login, logout } = useAuth()

// login faz POST /api/v1/auth/login e armazena tokens
await login(email, password)

// O refresh token é persistido no localStorage
// O access token vive apenas em memória
```

### `marketStore` (Zustand)

```typescript
const snapshots    = useMarketStore(s => s.snapshots)    // Record<symbol, Snapshot>
const trades       = useMarketStore(s => s.trades)        // Record<symbol, Trade[]>
const signals      = useMarketStore(s => s.signals)       // Signal[]
const connected    = useMarketStore(s => s.connected)     // boolean
const flows        = useMarketStore(s => s.flows)         // FlowEntry[]
const diFutures    = useMarketStore(s => s.diFutures)     // DIFuture[]
// ... worldMarkets, commodities, indices
```

## WebSocket

`useMarketWebSocket()` é chamado uma vez em `DashboardPage`:

1. Conecta em `ws://{host}/ws/market?token={accessToken}`
2. Roteamento de mensagens:
   - `type === "snapshot"` → `setSnapshot()`
   - `type === "trade"` → `addTrade()`
   - mensagem com campo `signal` → `addSignal()`
3. Reconecta automaticamente após 3 segundos se a conexão cair

## Workspaces do Dashboard

O dashboard tem 4 workspaces seleccionáveis pela TabBar. Um botão "Agentes" no canto direito abre o `AgentSidebar` flutuante sobre qualquer workspace.

### Tab 1 — Visão Geral
```
┌─────────────────────────────────────────────────────────┐
│ HEADER: Logo · Status WS · Hora · [Agentes]  · Logout  │
├──────────┬──────────┬─────────────────┬───────┬─────────┤
│  Flow    │  Force   │                 │  DI   │  World  │
│  Panel   │  Gauges  │   Stock Tape    │  Fut. │  Mkts   │
│          ├──────────┤   (ao vivo)     │       ├─────────┤
│  Indices │  Aggres  │                 │       │ Commod. │
│  Panel   │  Panel   │                 │       │         │
├──────────┴──────────┴────────────────┴───────┴─────────┤
│  Flow Chart (Recharts — Estrangeiro/Bancos/P.Física)    │
└─────────────────────────────────────────────────────────┘
```

### Tab 2 — Tape & Order Flow
```
┌──────────────┬────────────────────────┬─────────────────┐
│  StockTape   │   FlowChart            │  SignalsPanel   │
│  (símbolo    ├────────────────────────┤                 │
│   activo)    │   OrderBookPanel       │  DeltaPanel     │
│              │                        │                 │
│  TimeAndTrade│   VolumeProfileChart   │                 │
└──────────────┴────────────────────────┴─────────────────┘
```

### Tab 3 — Macro & Notícias
```
┌──────────────────────┬───────────────┬─────────────────┐
│  SectorHeatmap       │ EconomicCal.  │                 │
│  (row-span-2)        ├───────────────┤   NewsPanel     │
│                      │  DIYieldCurve │   (row-span-2)  │
└──────────────────────┴───────────────┴─────────────────┘
```

### Tab 4 — QuantLab
```
┌──────────────────────┬──────────────────────────────────┐
│  Editor Python       │  Output / Resultados             │
│  (com nºs de linha)  │  ┌──────────────────────────┐   │
│                      │  │ BUY  / SELL / HOLD badge  │   │
│  [Validar]  [Executar│  │ Signals list              │   │
│  Estratégias:        │  └──────────────────────────┘   │
│  lista de submetidas │                                  │
└──────────────────────┴──────────────────────────────────┘
```

### AgentSidebar (flutuante, w-80, lado direito)

Painel deslizante com 3 tabs de agentes IA (SSE streaming via Anthropic API):
- **Quant Dev** — Revisão de código de estratégias, explicação de indicadores
- **Researcher** — Análise de mercado, contexto académico, dados fundamentais
- **Operator** — Orientação operacional em tempo real, gestão de risco

Grid CSS (Tab 1): `grid-cols-[160px_160px_1fr_120px_130px] grid-rows-[1fr_140px]`

## Paleta de Cores (Tailwind)

| Token | Hex | Uso |
|-------|-----|-----|
| `surface` | `#0d0d0d` | Background principal |
| `panel` | `#111111` | Background dos painéis |
| `border` | `#1e1e1e` | Bordas |
| `up` | `#00c853` | Valores positivos / compra |
| `down` | `#f44336` | Valores negativos / venda |
| `neutral` | `#9e9e9e` | Labels, valores neutros |
| `accent` | `#1565c0` | Botão primário, estrangeiro |

## Componentes Reutilizáveis

### `<ValueCell>`

```tsx
// Exibe número colorido (verde se ≥ 0, vermelho se < 0)
<ValueCell value={-0.45} decimals={2} showSign />  // "-0.45" em vermelho
<ValueCell value={38.50} prefix="R$" />             // "R$38.50" em verde
```

### `<GaugeChart>`

```tsx
// Gauge SVG semicircular, value de -100 a +100
<GaugeChart value={-4.16} label="FORÇA RELATIVA" size={90} />
```

### `<PanelBox>`

```tsx
// Container padrão com título e borda
<PanelBox title="Fluxo" className="h-40">
  {/* conteúdo */}
</PanelBox>
```

## Executar

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
npm run build     # produção → dist/
npm run preview   # preview do build
```

O `vite.config.ts` proxy encaminha `/api` e `/ws` para `http://localhost:8000`.

## Adicionar Novo Painel

1. Criar `src/components/panels/MeuPainel.tsx`
2. Ler estado do `useMarketStore`
3. Importar e posicionar em `DashboardPage.tsx`

Nenhum prop drilling necessário — todos os painéis leem direto do store.
