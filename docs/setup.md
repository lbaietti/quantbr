# Setup e Execução

## Pré-requisitos

| Ferramenta | Versão Mínima |
|------------|--------------|
| g++ | 13+ (C++20) |
| cmake | 3.20+ |
| libzmq3-dev | 4.3+ |
| Python | 3.11+ |
| Node.js | 20+ |
| PostgreSQL | 15+ |
| Redis | 7+ |

## 1. Feed C++

```bash
# Instalar dependências do sistema
sudo apt install cmake libzmq3-dev

# Build
cd feed
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)

# Executar (variáveis de ambiente obrigatórias)
export B3_MCAST_GROUP_A=233.200.79.1
export B3_MCAST_GROUP_B=233.200.79.2
export B3_MCAST_PORT=20000
export B3_SOURCE_IP=192.168.1.10      # IP da sua interface de rede
export B3_ZMQ_ENDPOINT=tcp://0.0.0.0:5555
./build/quantbr_feed
```

### Variáveis de Ambiente — Feed

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `B3_MCAST_GROUP_A` | Sim | Grupo multicast canal A |
| `B3_MCAST_GROUP_B` | Sim | Grupo multicast canal B |
| `B3_MCAST_PORT` | Sim | Porta UDP dos canais |
| `B3_SOURCE_IP` | Não | IP da interface local (padrão: 0.0.0.0) |
| `B3_ZMQ_ENDPOINT` | Não | Endpoint de publicação ZMQ (padrão: tcp://0.0.0.0:5555) |
| `B3_STEP_HOST` | Não | IP do gateway STEP/FIX (order entry opcional) |
| `B3_STEP_PORT` | Não | Porta STEP (padrão: 21000) |
| `B3_SENDER_COMP_ID` | Não | SenderCompID FIX |
| `B3_TARGET_COMP_ID` | Não | TargetCompID FIX |
| `B3_PASSWORD` | Não | Senha FIX |

## 2. Backend Python

```bash
cd backend

# Ambiente virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Dependências
pip install -e ".[dev]"

# Configuração
cp .env.example .env
# Edite .env com suas credenciais (veja tabela abaixo)

# Banco de dados
createdb quantbr
alembic upgrade head

# Executar
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Variáveis de Ambiente — Backend

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | **Sim** | Chave JWT (mín. 32 chars). Gere com: `openssl rand -hex 32` |
| `DATABASE_URL` | **Sim** | `postgresql+asyncpg://user:pass@host:5432/db` |
| `REDIS_URL` | Sim | `redis://localhost:6379/0` |
| `ZMQ_FEED_ENDPOINT` | Não | Endpoint ZMQ do feed (padrão: tcp://localhost:5555) |
| `CORS_ORIGINS` | Não | JSON array de origens permitidas |
| `APP_ENV` | Não | `development` \| `production` (padrão: production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Não | Expiração do access token (padrão: 30) |
| `ANTHROPIC_API_KEY` | Não | Chave da API Anthropic (obrigatória para os Agentes IA) |
| `ANTHROPIC_MODEL` | Não | Modelo Claude a usar (padrão: `claude-sonnet-4-6`) |
| `AGENT_MESSAGES_PER_HOUR` | Não | Limite de mensagens por usuário por hora (padrão: 20) |

### Criar Primeiro Usuário (admin)

```python
# No shell Python com .venv ativado
from app.security.auth import hash_password
print(hash_password("sua_senha_aqui"))
# Cole o hash no INSERT abaixo
```

```sql
INSERT INTO users (id, email, hashed_password, role, is_active)
VALUES (gen_random_uuid(), 'admin@example.com', '<hash>', 'admin', true);
```

### Migrations

```bash
# Criar nova migration
alembic revision --autogenerate -m "descricao"

# Aplicar
alembic upgrade head

# Reverter
alembic downgrade -1
```

## 3. Frontend React

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

Para produção:

```bash
npm run build   # gera dist/
# Sirva dist/ com nginx ou qualquer servidor estático
```

### Proxy

Em desenvolvimento o Vite proxy encaminha automaticamente:
- `/api/*` → `http://localhost:8000`
- `/ws/*`  → `ws://localhost:8000`

Em produção configure o nginx para fazer o mesmo proxy.

## Ordem de Inicialização

```
1. PostgreSQL + Redis (infraestrutura)
2. Backend uvicorn      (aguarda DB + Redis)
3. Feed C++             (aguarda Backend ZMQ bind)
4. Frontend dev server  (qualquer ordem)
```

## Verificação de Saúde

```bash
# Backend liveness
curl http://localhost:8000/healthz

# Backend readiness (Redis + DB)
curl http://localhost:8000/readyz

# Métricas Prometheus
curl http://localhost:8000/metrics
```
