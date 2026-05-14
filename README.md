# QuantBR

> Real-time quantitative trading dashboard for B3 (Brazil's exchange) — built for HFT monitoring, technical analysis, and strategy backtesting.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![ISO 25010](https://img.shields.io/badge/ISO-25010-green.svg)](docs/iso-compliance.md)
[![ISO 27001](https://img.shields.io/badge/ISO-27001-green.svg)](docs/iso-compliance.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)

---

## Overview

QuantBR is a three-layer system that consumes B3 market data, computes technical indicators and trading signals in real time, and displays everything in a live browser dashboard.

```
Feed (C++20)  ──ZMQ──►  Backend (Python/FastAPI)  ──WebSocket──►  Frontend (React)
     │                           │
 B3 UMDF (UDP)              Redis pub/sub
 B3 STEP (FIX)              PostgreSQL
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| [Feed](docs/feed.md) | C++20, ZMQ, CMake | Consumes B3 UMDF (UDP multicast) + STEP (FIX 4.4); maintains L2 order book; publishes via ZMQ |
| [Backend](docs/backend.md) | Python, FastAPI, SQLAlchemy, Redis | Consumes ZMQ, computes indicators/signals, exposes REST + WebSocket API |
| [Frontend](docs/frontend.md) | React 18, TypeScript, TailwindCSS, Vite | Live dashboard inspired by professional trading terminals |

---

## Features

### Dashboard (4 workspaces)

- **Visão Geral** — Foreign/bank/retail flow panels, B3 indices (IBOV, IFIX, SMLL, IDIV), relative force gauges, aggression bars, DI futures curve, world markets, commodities, stock tape
- **Tape & Order Flow** — Live stock tape, flow chart (time series), signals panel, L2 order book, time & sales, order flow delta, volume profile
- **Macro & Notícias** — DI yield curve (DI1F26–DI1F33), sector heat map, economic calendar, live news feed (Infomoney, Valor Econômico, Reuters)
- **QuantLab** — Strategy sandbox with AST safety check + 5 s exec timeout; run/backtest; buy/sell/hold signal output

### Technical Indicators (incremental, O(1) per tick)

SMA, EMA, RSI (Wilder 14), Bollinger Bands (20, 2σ), Session VWAP, Order Flow Delta, Volume Profile, Book Imbalance

### Trading Signals

RSI Oversold/Overbought, Bollinger Band touches, VWAP Cross

### AI Agents (Anthropic Claude API)

Three specialist agents in a floating sidebar:
- **Quant Developer** — Explains indicators, reviews strategy code
- **Quant Researcher** — Market analysis, academic context, fundamental data
- **Quant Operator** — Real-time operational guidance, risk management

### Security (ISO 27001)

- JWT (HS256) authentication with 30-min access token + 7-day refresh token
- bcrypt password hashing (cost factor 12)
- RBAC with three roles: `viewer` / `trader` / `admin`
- Structured JSON audit log → PostgreSQL (`AuditLog` model)
- QuantLab AST sandbox — blocks `import`, `exec`, `eval`, dunders
- Rate limiting on AI agents (configurable per-user hourly cap)

---

## Quick Start

See [docs/setup.md](docs/setup.md) for full instructions. Here is the minimum to run locally:

```bash
# 1. Clone
git clone https://github.com/lbaietti/quantbr.git
cd quantbr

# 2. Backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # fill SECRET_KEY and DATABASE_URL
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

> The C++ feed is optional for local development. The backend fetches market data directly from B3's public REST API when the ZMQ feed is not connected.

---

## Repository Structure

```
QuantBR/
├── feed/                   # C++20 HFT feed (UMDF + STEP)
│   ├── include/            # Headers: parser, book, zmq publisher
│   ├── src/                # Implementations
│   └── CMakeLists.txt
├── backend/                # Python FastAPI
│   ├── app/
│   │   ├── api/v1/         # REST + WebSocket routes
│   │   ├── db/             # SQLAlchemy async engine + session
│   │   ├── feed/           # ZMQ subscriber
│   │   ├── indicators/     # SMA, EMA, RSI, Bollinger, VWAP, Delta, VolumeProfile
│   │   ├── market_data/    # B3 REST + BCB + news fetchers
│   │   ├── models/         # ORM models (User, Instrument, Trade, AuditLog…)
│   │   ├── quantlab/       # Strategy sandbox (AST check + exec timeout)
│   │   ├── schemas/        # Pydantic v2 schemas
│   │   ├── security/       # JWT, bcrypt, RBAC, audit
│   │   └── signals/        # Signal engine (RSI, BB, VWAP cross)
│   ├── alembic/            # Database migrations
│   ├── tests/
│   │   ├── unit/           # 37 unit tests (indicators, signals, sandbox AST)
│   │   └── integration/    # Auth integration tests
│   └── pyproject.toml
├── frontend/               # React 18 + TypeScript
│   ├── src/
│   │   ├── api/            # Axios client with JWT auto-refresh
│   │   ├── components/     # All panels + AgentSidebar
│   │   ├── hooks/          # useWebSocket, useAuth
│   │   ├── pages/          # LoginPage, DashboardPage (4-tab workspace)
│   │   ├── store/          # Zustand (authStore, marketStore)
│   │   └── types/          # TypeScript types
│   └── package.json
├── docs/                   # Architecture, setup, ISO compliance
└── scripts/                # Utility scripts
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/setup.md](docs/setup.md) | Installation, environment variables, first run |
| [docs/architecture.md](docs/architecture.md) | System architecture and design decisions |
| [docs/feed.md](docs/feed.md) | C++ feed: UMDF parser, order book, ZMQ publisher |
| [docs/backend.md](docs/backend.md) | Backend API reference, indicators, signals, agents |
| [docs/frontend.md](docs/frontend.md) | Frontend components, state management, WebSocket |
| [docs/iso-compliance.md](docs/iso-compliance.md) | Full ISO 25010 and ISO 27001 compliance mapping |

---

## ISO Compliance

QuantBR was designed and implemented under **ISO 25010** (software product quality) and **ISO 27001** (information security management). See [docs/iso-compliance.md](docs/iso-compliance.md) for a full mapping of controls to code.

| Standard | Areas covered |
|----------|--------------|
| ISO 25010 | Functional suitability, Performance efficiency, Reliability, Security, Maintainability, Testability, Portability |
| ISO 27001 | A.9 Access control, A.10 Cryptography, A.12 Logging & monitoring, A.13 Network security, A.14 Secure development |

---

## Development Methodology

**QuantBR v1 was developed entirely using [Claude Code](https://claude.ai/code)** (Anthropic's AI coding assistant), from initial planning through architecture design, implementation, security audit, and deployment. The development process involved providing domain context — B3 market structure, HFT requirements, ISO standards — and iterating with Claude Code to produce all layers of the system: C++20 feed, Python backend, and React frontend.

This is an intentional and transparent choice. The goal was to explore how far an AI coding assistant can take a complex, multi-layer, standards-compliant system from scratch — and to demonstrate that AI-assisted development can produce production-quality code when the right context and quality criteria are applied.

If you are curious about AI-assisted development at this scale, this project is an open reference.

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

This is an experimental project. If you are interested in extending it — new indicators, broker integration, deployment scripts, Docker setup — open an issue or a pull request.

---

## Roadmap (v1.1+)

- [ ] Docker Compose for full-stack local setup
- [ ] Real B3 UMDF feed connection (requires market participant credentials)
- [ ] More indicators: ATR, ADX, Stochastic, OBV
- [ ] Strategy persistence and backtesting with historical data
- [ ] Alerts (email / Telegram) from signal engine
- [ ] Multi-broker order routing via STEP (FIX 4.4)
- [ ] User management UI (admin panel)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

QuantBR is an experimental educational project. It is **not** financial advice. Use of this software for actual trading is at your own risk. The authors assume no liability for financial losses.
