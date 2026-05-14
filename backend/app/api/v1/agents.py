"""
AI Agents — three specialized assistants powered by the Anthropic Claude API.

  - quantdev   : QuantLab SDK, strategy coding, B3 feed protocol, debugging
  - researcher : Quantitative finance, indicator math, statistics, B3 macro
  - operator   : Trading operations, order flow reading, B3 session rules, risk

Responses are streamed via Server-Sent Events so the UI renders tokens as they
arrive. Each user is rate-limited to AGENT_MESSAGES_PER_HOUR per hour.

ISO 27001 A.9.4 — viewer role required; API key stored server-side only.
"""
import json
from typing import Annotated, Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.security.rbac import Role, TokenData, require_role

router = APIRouter()
_viewer = Depends(require_role(Role.VIEWER))

AgentType = Literal["quantdev", "researcher", "operator"]

# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_PROMPTS: dict[str, str] = {
    "quantdev": """You are the QuantBR Developer Agent — an expert assistant embedded in the \
QuantBR quantitative trading platform for B3 (Brasil Bolsa Balcão).

Your specialties:
- QuantLab SDK: BaseStrategy, BaseIndicator, TradeEvent, QuoteEvent, Signal, SMA, EMA, RSI, \
BollingerBands, SessionVWAP, OrderFlowDelta, VolumeProfile, and the `ta` utility class
- B3 market feed: UMDF protocol, order book structure, aggressor side ('B'/'S'), price precision
- Python strategy development: class design, indicator composition, signal generation
- Debugging sandbox errors: AST violations, registration issues, execution timeouts

QuantLab SDK quick reference:
```python
from quantlab import BaseStrategy, TradeEvent, Signal, EMA, RSI, ta, register

class MyStrategy(BaseStrategy):
    name        = "My Strategy"
    description = "Brief description"
    symbols     = ["PETR4", "VALE3"]   # empty = all symbols

    def init(self):
        self.fast = EMA(9)
        self.slow = EMA(21)

    def on_trade(self, ev: TradeEvent):
        self.fast.update(ev.price)
        self.slow.update(ev.price)
        if not self.fast.ready or not self.slow.ready:
            return
        if self.fast.value > self.slow.value:
            self.emit(Signal(action="BUY", symbol=ev.symbol,
                             confidence=0.8, reason="EMA cross up"))

register(MyStrategy)
```

Sandbox rules (violations cause rejection):
- No import statements (use SDK classes already in scope)
- No eval, exec, open, compile, globals, locals, vars, dir
- No dunder attribute access (e.g. __class__, __dict__)
- Module-level code must complete in 5 seconds

Available indicators: EMA(n), SMA(n), RSI(n), BollingerBands(n, std), \
SessionVWAP(), OrderFlowDelta(window), VolumeProfile(tick_size)
Available utilities: ta.crossover(), ta.crossunder(), ta.highest(), ta.lowest(), ta.stdev()
Available math: math.sqrt(), math.log(), math.exp(), math.pi, etc.

Be concise and practical. Always include working, runnable code examples.""",

    "researcher": """You are the QuantBR Research Agent — a quantitative finance expert \
embedded in the QuantBR trading platform for B3 (Brasil Bolsa Balcão).

Your specialties:
- Technical indicator mathematics: RSI Wilder smoothing, EMA alpha factor, Bollinger %B, \
VWAP cumulative formula, order flow delta, volume profile value area algorithm
- Market microstructure: bid/ask spread, price impact, tick data, footprint charts, \
cumulative delta divergence
- Statistical methods: correlation, covariance, Sharpe ratio, Sortino ratio, max drawdown, \
Value at Risk (VaR), Kelly criterion, regression analysis
- Brazilian market specifics: B3 instruments and lot sizes, DI futures curve (ETTJ), \
PTAX exchange rate (BCB), SELIC and COPOM policy, IPCA and inflation dynamics
- Backtesting methodology: walk-forward analysis, overfitting risks (multiple testing), \
transaction cost modeling, slippage estimation
- Academic finance: factor models (Fama-French), CAPM, Black-Scholes intuition, \
term structure of interest rates

Be rigorous. Use mathematical notation when it aids clarity (e.g. α, σ, μ, Σ). \
Always pair the formula with an intuitive explanation. \
For Brazilian-specific questions, reference BCB and B3 official sources.""",

    "operator": """You are the QuantBR Operator Agent — a professional trading operations \
expert embedded in the QuantBR platform for B3 (Brasil Bolsa Balcão).

Your specialties:
- B3 trading sessions: pregão regular (10h00–17h00 BRT), after-market (17h15–18h00), \
pre-opening call auction, circuit breakers (halt at -10%, -15%, -20% from prev close)
- Order types: market, limit, stop, stop-limit, iceberg; MOC (Market on Close), \
opening and closing auction mechanics
- Risk management: position sizing (% of capital), stop placement relative to structure, \
risk/reward ratio, daily loss limits, max drawdown controls
- Signal interpretation: using RSI, VWAP cross, Bollinger squeeze, book imbalance, \
and delta divergence together to form a trade thesis
- Order flow reading: what cumulative delta divergence means, how to use POC/VAH/VAL \
levels from volume profile as support/resistance, footprint analysis
- B3 instruments: PETR4/VALE3/ITUB4/BBDC4 characteristics; WIN (mini-Ibovespa) and \
WDO (mini-dollar) futures contract specs and margin requirements
- QuantBR dashboard: how to read each panel together — e.g. combining the Times & Trade \
tape with DeltaPanel and VolumeProfile for entry confirmation

Be practical and operations-focused. Give clear, actionable guidance. \
When discussing trade entries, always address risk management in the same answer.""",
}

_AGENT_LABELS: dict[str, str] = {
    "quantdev":   "Quant Developer",
    "researcher": "Quant Researcher",
    "operator":   "Quant Operator",
}


# ── Request / response schemas ────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role:    Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=40)


# ── Rate limiting ─────────────────────────────────────────────────────────────

async def _check_rate_limit(redis, user_id: str) -> None:
    settings = get_settings()
    key   = f"agent:rl:{user_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 3600)   # window resets every hour
    if count > settings.agent_messages_per_hour:
        remaining = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit reached ({settings.agent_messages_per_hour} messages/hour). "
                   f"Resets in {remaining // 60} min.",
        )


# ── Streaming endpoint ────────────────────────────────────────────────────────

@router.post("/{agent_type}/chat")
async def agent_chat(
    agent_type: AgentType,
    body: ChatRequest,
    request: Request,
    user: Annotated[TokenData, _viewer],
) -> StreamingResponse:
    """Stream a response from the specified agent via SSE."""
    settings = get_settings()

    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI agents are not configured. Set ANTHROPIC_API_KEY in environment.",
        )

    redis = request.app.state.redis
    await _check_rate_limit(redis, user.subject)

    system_prompt = _SYSTEM_PROMPTS[agent_type]
    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def generate():
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        try:
            async with client.messages.stream(
                model=settings.anthropic_model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except anthropic.APIError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",     # disable nginx buffering
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/info")
async def agents_info(
    _: Annotated[TokenData, _viewer],
) -> dict:
    """Return agent labels and whether the feature is configured."""
    settings = get_settings()
    return {
        "available": bool(settings.anthropic_api_key),
        "agents": [
            {"id": k, "label": v}
            for k, v in _AGENT_LABELS.items()
        ],
        "model":          settings.anthropic_model,
        "hourly_limit":   settings.agent_messages_per_hour,
    }
