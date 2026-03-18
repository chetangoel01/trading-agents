from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from agents.base import BaseAgent
from config import ModelRole, STRATEGY_WEIGHTS
from state import AgentState, SignalDirection, StrategyType, TickerThesis
from utils.audit_store import insert_llm_call
from utils.llm import LLMClient
from utils.trace import TraceWriter


class SynthesisAgent(BaseAgent):
    name = "synthesize"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__()
        self.llm = llm_client or LLMClient()

    @staticmethod
    def _response_content(body: dict[str, Any]) -> str:
        return body.get("choices", [{}])[0].get("message", {}).get("content", "{}")

    async def _call_synthesis_llm(self, ticker: str, payload: dict[str, Any]):
        prompt = (
            "Synthesize a single-ticker thesis as JSON keys: direction, confidence, summary, "
            "bull_case, bear_case, key_catalysts, key_risks, dominant_strategy, sector.\n"
            f"Ticker: {ticker}\nPayload:\n{json.dumps(payload, default=str)}"
        )
        return await self.llm.complete(
            ModelRole.SYNTHESIS,
            [
                {"role": "system", "content": "You are a senior equity research analyst."},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
        )

    @staticmethod
    def _neutral_thesis(ticker: str) -> TickerThesis:
        return TickerThesis(
            ticker=ticker,
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            summary="No reliable thesis available due to missing or failed synthesis.",
            bull_case="Insufficient data",
            bear_case="Insufficient data",
            key_catalysts=[],
            key_risks=["synthesis_unavailable"],
            strategy_signals=[],
            dominant_strategy=StrategyType.FUNDAMENTAL,
            data_freshness_hours=999.0,
            signal_count=0,
            conflicting_signals=0,
            sector="unknown",
            synthesis_model="fallback_neutral",
            synthesis_latency_ms=0,
        )

    async def _execute(self, state: AgentState) -> AgentState:
        run_id = state["metadata"].run_id
        trace = TraceWriter(run_id)
        theses: list[TickerThesis] = []

        by_ticker_extract: dict[str, list] = {}
        for sig in state["extracted_signals"]:
            by_ticker_extract.setdefault(sig.ticker, []).append(sig)

        by_ticker_strategy: dict[str, list] = {}
        for sig in state["strategy_signals"]:
            by_ticker_strategy.setdefault(sig.ticker, []).append(sig)

        for ticker in state["metadata"].tickers:
            started = perf_counter()
            payload = {
                "signals": [s.model_dump(mode="json") for s in by_ticker_extract.get(ticker, [])],
                "strategy_signals": [
                    s.model_dump(mode="json") for s in by_ticker_strategy.get(ticker, [])
                ],
                "strategy_weights": STRATEGY_WEIGHTS,
            }
            try:
                body, meta = await self._call_synthesis_llm(ticker, payload)
                content = self._response_content(body)
                parsed = json.loads(content) if isinstance(content, str) else {}
                thesis = TickerThesis(
                    ticker=ticker,
                    direction=parsed.get("direction", "neutral"),
                    confidence=float(parsed.get("confidence", 0.0)),
                    summary=parsed.get("summary", "No summary"),
                    bull_case=parsed.get("bull_case", "N/A"),
                    bear_case=parsed.get("bear_case", "N/A"),
                    key_catalysts=list(parsed.get("key_catalysts", [])),
                    key_risks=list(parsed.get("key_risks", [])),
                    strategy_signals=by_ticker_strategy.get(ticker, []),
                    dominant_strategy=parsed.get("dominant_strategy", "fundamental"),
                    data_freshness_hours=0.0,
                    signal_count=len(payload["signals"]),
                    conflicting_signals=0,
                    sector=parsed.get("sector", "unknown"),
                    synthesis_model=meta.model,
                    synthesis_latency_ms=meta.latency_ms,
                )
                theses.append(thesis)
                trace.write(
                    "llm_call",
                    node=self.name,
                    ticker=ticker,
                    role="synthesis",
                    model=meta.model,
                    input_tokens=meta.input_tokens,
                    output_tokens=meta.output_tokens,
                    latency_ms=meta.latency_ms,
                    cost_usd=meta.estimated_cost_usd,
                    prompt=json.dumps(payload, default=str),
                    response=content,
                    success=True,
                )
                insert_llm_call(
                    run_id=run_id,
                    model=meta.model,
                    role="synthesis",
                    ticker=ticker,
                    input_tokens=meta.input_tokens,
                    output_tokens=meta.output_tokens,
                    cost_usd=meta.estimated_cost_usd,
                    latency_ms=meta.latency_ms,
                    success=True,
                )
            except Exception as exc:
                latency_ms = int((perf_counter() - started) * 1000)
                theses.append(self._neutral_thesis(ticker))
                state["metadata"].warnings.append(
                    {
                        "agent": self.name,
                        "ticker": ticker,
                        "warning": f"synthesis failed; neutral fallback: {exc}",
                    }
                )
                trace.write(
                    "llm_call",
                    node=self.name,
                    ticker=ticker,
                    role="synthesis",
                    model="unknown",
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    cost_usd=0.0,
                    prompt=json.dumps(payload, default=str),
                    response=None,
                    success=False,
                    error=str(exc),
                )
                insert_llm_call(
                    run_id=run_id,
                    model="unknown",
                    role="synthesis",
                    ticker=ticker,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    success=False,
                    error=str(exc),
                )

        state["theses"] = theses
        return state
