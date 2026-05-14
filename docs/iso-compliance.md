# Conformidade ISO 25010 e ISO 27001

## ISO 25010 — Qualidade de Software

### Adequação Funcional
- Feed C++ consome todos os tipos de mensagem UMDF (snapshot `W`, incremental `X`, security def `d`)
- Backend expõe REST + WebSocket completos para todos os dados do sistema
- Motor de sinais (RSI, Bollinger, VWAP Cross) gera alertas acionáveis em tempo real
- QuantLab permite extensão por desenvolvedores sem alterar o código principal

### Eficiência de Performance
- Feed C++ compilado com `-O3 -march=native` e operações de book em O(1) (std::map)
- Backend totalmente assíncrono (asyncio + asyncpg + aioredis)
- Redis como cache L1 para snapshots (latência sub-ms para o frontend)
- Indicadores incrementais: cada trade processa em O(1) por indicador
- Volume profile e delta acumulados in-memory, publicados no Redis

### Confiabilidade
- Feed: canais A e B redundantes, deduplicação por seq_num, detecção de gaps
- Backend: lifespan gerencia todos os recursos; graceful shutdown
- WebSocket: reconexão automática no frontend (3 segundos)
- `/healthz` (liveness) e `/readyz` (readiness) para orquestração

### Segurança
Ver seção ISO 27001 abaixo.

### Manutenibilidade
- Módulos com responsabilidades únicas (feed, indicators, signals, quantlab, market_data, api)
- Dependências injetadas (Redis, engine) — testáveis em isolamento
- Pydantic v2 valida todas as entradas e saídas da API
- Alembic gerencia schema migrations com versionamento

### Testabilidade
- Indicadores são classes puras sem dependências externas — 100% unitáveis
- Motor de sinais testável sem banco ou rede
- 37+ testes unitários passando (SMA, EMA, RSI, Bollinger, VWAP, OrderFlowDelta, VolumeProfile, BookImbalance, Signals, Sandbox AST)
- Testes de integração: auth flow completo (login, refresh, token inválido)
- Estrutura preparada para testes adicionais (conftest.py com AsyncClient)

### Portabilidade
- Feed: Linux x86-64 com CMake; dependências apenas libzmq
- Backend: Python 3.11+ com pyproject.toml; Docker-ready
- Frontend: Node 20+; build estático servível em qualquer CDN
- Toda configuração via variáveis de ambiente (12-factor app)

---

## ISO 27001 — Segurança da Informação

### A.9 — Controle de Acesso

**A.9.2 Gerenciamento de acesso de usuários**
- Modelo `User` com `role` (`viewer` / `trader` / `admin`)
- Senhas armazenadas exclusivamente como hash bcrypt (fator de custo 12)
- `is_active` permite revogar acesso sem deletar o usuário

**A.9.4 Controle de acesso a sistemas e aplicações**
- Todos os endpoints REST requerem `Authorization: Bearer <JWT>`
- WebSocket valida token antes de aceitar a conexão (fecha com 1008 se inválido)
- `require_role(Role.VIEWER)` / `require_role(Role.TRADER)` — hierarquia aplicada em cada rota
- QuantLab: apenas `trader` pode submeter/deletar estratégias

### A.10 — Criptografia

**A.10.1 Política de uso de controles criptográficos**
- Senhas: bcrypt (resistente a rainbow table e brute-force)
- JWT: HS256 com `SECRET_KEY` ≥ 32 bytes (gerado com `openssl rand -hex 32`)
- Access token: 30 min de expiração; refresh token: 7 dias
- TLS: responsabilidade do proxy reverso (nginx/traefik) — documentado em setup.md

### A.12 — Segurança em Operações

**A.12.4 Logging e monitoramento**
- Todos os eventos de autenticação logados como JSON estruturado (structlog)
- `AuditLog` model persiste eventos no PostgreSQL para auditoria permanente
- Eventos auditados: login success/failure, logout, token refresh, access denied, order sent/cancel, user created/deleted, config changed
- Prometheus metrics em `/metrics` para monitoramento operacional
- IP do cliente capturado em cada evento de auth (`X-Forwarded-For` aware)

### A.14 — Segurança no Desenvolvimento

**A.14.2 Segurança no desenvolvimento e suporte**
- CORS estritamente configurado: apenas origens em `CORS_ORIGINS` (lista explícita); métodos explícitos (`GET, POST, PATCH, DELETE`) — sem wildcard
- Pydantic valida e rejeita toda entrada inválida antes de tocar no banco
- Docs OpenAPI (`/docs`) desabilitados em `APP_ENV=production`
- Stack traces nunca expostos na resposta de erro em produção (exception handler global)
- `/metrics` (Prometheus) desabilitado em produção — exposto apenas em desenvolvimento; em produção deve ser protegido via proxy reverso com `allow 127.0.0.1`
- QuantLab sandbox: AST safety check bloqueia `import`, `exec`, `eval`, `open` e acesso a dunders antes de executar qualquer código de usuário
- QuantLab exec com timeout de 5 s em thread pool — loops infinitos no módulo não bloqueiam o event loop
- XML das feeds RSS parseado com `defusedxml` — proteção contra billion-laughs e XXE
- `DATABASE_URL` não possui valor default — obrigatório via env var para prevenir uso acidental de credenciais de desenvolvimento em produção

### A.13 — Segurança em Comunicações

**A.13.1 Controles de segurança de redes**
- ZMQ entre feed e backend é local (loopback) — sem exposição de rede externa
- Redis configurável com senha (`REDIS_PASSWORD`)
- Todos os endpoints externos devem ser servidos atrás de TLS (documentado)

---

## Conformidade — Resumo por Módulo

| Módulo | ISO 25010 | ISO 27001 |
|--------|-----------|-----------|
| `feed/` | Performance, Confiabilidade | — |
| `app/security/auth.py` | Segurança | A.9.4, A.10.1 |
| `app/security/rbac.py` | Segurança | A.9.2, A.9.4 |
| `app/security/audit.py` | — | A.12.4 |
| `app/quantlab/sandbox.py` | Segurança | A.14.2 |
| `app/market_data/fetcher.py` | Funcionalidade | — |
| `app/market_data/news_fetcher.py` | Funcionalidade | — |
| `app/main.py` (CORS, error handler) | Segurança | A.14.2 |
| `app/api/` (Pydantic schemas) | Manutenibilidade | A.14.2 |
| `app/api/v1/agents.py` | Funcionalidade, Segurança | A.9.4, A.12.4 |
| `app/api/v1/lab.py` | Segurança, Funcionalidade | A.9.4, A.14.2 |
| `app/api/v1/reference.py` | Funcionalidade | — |
| `app/api/v1/news.py` | Funcionalidade | — |
| `frontend/AgentSidebar.tsx` | Funcionalidade, Segurança | A.9.4 |
| `frontend/QuantLabPanel.tsx` | Funcionalidade | — |
| `.gitignore` (exclui .env, secrets) | — | A.10.1 |
