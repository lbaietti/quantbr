# Contributing to QuantBR

Thank you for your interest in contributing. QuantBR is an experimental open-source project — contributions are welcome at all levels.

## Getting Started

1. Fork the repository and clone your fork
2. Follow [docs/setup.md](docs/setup.md) to run the project locally
3. Create a branch: `git checkout -b feature/your-feature-name`

## What to Contribute

- **New indicators** — add to `backend/app/indicators/`, follow the `Indicator` ABC in `base.py`, include unit tests
- **New signals** — add to `backend/app/signals/engine.py`, add test cases
- **Frontend panels** — add to `frontend/src/components/panels/`, use `PanelBox` for consistent styling
- **Bug fixes** — open an issue first if the fix is non-trivial
- **Documentation** — corrections, translations, examples
- **Docker / deployment** — Compose file, nginx config, CI/CD pipelines

## Code Standards

### Backend (Python)

- Python 3.11+, async throughout (`async def`, `await`)
- Pydantic v2 for all I/O schemas — no raw dicts across API boundaries
- SQLAlchemy 2.x async ORM — no raw SQL except migrations
- Unit tests for all new indicators and signals (`pytest`, `pytest-asyncio`)
- No secrets in code — all config via environment variables

### Frontend (TypeScript)

- Strict TypeScript — no `any`, explicit types on all props
- Tailwind utility classes — no inline styles, no CSS modules
- Zustand for shared state — no prop drilling beyond 2 levels
- Functional components only — no class components

### Security (ISO 27001 A.14)

- All new API endpoints must require authentication (`require_role(...)`)
- New user-facing inputs must go through Pydantic validation
- Any code executed in QuantLab context must pass through the AST sandbox
- Never log passwords, tokens, or PII — log IDs and event types only

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/unit/ -v                    # unit tests (no external deps)
pytest tests/integration/ -v             # requires running PostgreSQL
```

## Pull Request Checklist

- [ ] Branch is up to date with `main`
- [ ] All existing tests pass (`pytest tests/unit/`)
- [ ] New functionality has unit tests
- [ ] No secrets, credentials, or `.env` files committed
- [ ] Follows the code standards above
- [ ] PR description explains what and why (not just what)

## ISO Compliance Note

QuantBR targets ISO 25010 (software quality) and ISO 27001 (security). When adding features:

- **Security controls** must not be weakened — e.g., do not bypass RBAC, do not expose stack traces in production, do not add new CORS origins beyond what is necessary
- **Testability** — new business logic should be independently testable without external dependencies where possible
- **Audit logging** — security-relevant events (auth, config changes, privileged operations) should be logged via `app.security.audit`

## Questions

Open a GitHub Issue with the `question` label.
