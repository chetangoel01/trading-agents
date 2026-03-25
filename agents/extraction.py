from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import Any

from agents.base import BaseAgent
from config import ModelRole
from state import (
    AgentState,
    ExtractedSignal,
    FinancialMetric,
    RawDocument,
    RiskFactor,
    SentimentSignal,
)
from utils.audit_store import insert_llm_call
from utils.llm import LLMClient
from utils.trace import TraceWriter

MAX_CONCURRENT_EXTRACTIONS = 10


class ExtractionAgent(BaseAgent):
    name = "extract"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        super().__init__()
        self.llm = llm_client or LLMClient()
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)

    @staticmethod
    def _response_content(body: dict[str, Any]) -> str:
        content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content if content else "{}"

    async def _call_extraction_llm(self, ticker: str, content: str) -> tuple[dict[str, Any], Any]:
        prompt = (
            "Extract structured financial signals as JSON with keys: "
            "metrics, sentiments, risks, key_events, management_guidance, insider_activity.\n"
            f"Ticker: {ticker}\nContent:\n{content}"
        )
        return await self.llm.complete(
            ModelRole.EXTRACTION,
            [
                {"role": "system", "content": "You are a financial extraction engine."},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
        )

    @staticmethod
    def _parse_metrics(items: list[dict[str, Any]]) -> list[FinancialMetric]:
        out: list[FinancialMetric] = []
        for item in items:
            try:
                out.append(
                    FinancialMetric(
                        name=item["name"],
                        value=float(item["value"]),
                        unit=item.get("unit", "unknown"),
                        period=item.get("period", "unknown"),
                        yoy_change=(
                            float(item["yoy_change"]) if item.get("yoy_change") is not None else None
                        ),
                        beat_estimate=item.get("beat_estimate"),
                    )
                )
            except Exception:
                continue
        return out

    async def _extract_one(
        self, doc: RawDocument, run_id: str, trace: TraceWriter,
    ) -> ExtractedSignal | None:
        """Extract signals from a single document. Returns None on failure."""
        async with self._semaphore:
            started = perf_counter()
            try:
                body, meta = await self._call_extraction_llm(doc.ticker, doc.content)
                content = self._response_content(body)
                parsed = json.loads(content) if isinstance(content, str) else {}
                sentiments = []
                for s in parsed.get("sentiments", []):
                    try:
                        sentiments.append(
                            SentimentSignal(
                                direction=s.get("direction", "neutral"),
                                confidence=float(s.get("confidence", 0.0)),
                                key_phrase=s.get("key_phrase", ""),
                                context=s.get("context", ""),
                            )
                        )
                    except Exception:
                        continue
                risks = []
                for r in parsed.get("risks", []):
                    try:
                        risks.append(
                            RiskFactor(
                                description=r.get("description", ""),
                                severity=float(r.get("severity", 0.0)),
                                category=r.get("category", "operational"),
                                is_new=bool(r.get("is_new", False)),
                            )
                        )
                    except Exception:
                        continue

                raw_guidance = parsed.get("management_guidance")
                raw_insider = parsed.get("insider_activity")

                signal = ExtractedSignal(
                    source_doc_hash=doc.content_hash,
                    ticker=doc.ticker,
                    source_type=doc.source_type,
                    metrics=self._parse_metrics(parsed.get("metrics", [])),
                    sentiments=sentiments,
                    risks=risks,
                    key_events=[
                        str(e) if not isinstance(e, str) else e
                        for e in parsed.get("key_events", [])
                    ],
                    management_guidance=(
                        json.dumps(raw_guidance) if isinstance(raw_guidance, (dict, list))
                        else raw_guidance
                    ),
                    insider_activity=(
                        json.dumps(raw_insider) if isinstance(raw_insider, (dict, list))
                        else raw_insider
                    ),
                    extraction_model=meta.model,
                    extraction_latency_ms=meta.latency_ms,
                )
                trace.write(
                    "llm_call",
                    node=self.name,
                    ticker=doc.ticker,
                    role="extraction",
                    model=meta.model,
                    input_tokens=meta.input_tokens,
                    output_tokens=meta.output_tokens,
                    latency_ms=meta.latency_ms,
                    cost_usd=meta.estimated_cost_usd,
                    prompt=doc.content,
                    response=content,
                    success=True,
                )
                insert_llm_call(
                    run_id=run_id,
                    model=meta.model,
                    role="extraction",
                    ticker=doc.ticker,
                    input_tokens=meta.input_tokens,
                    output_tokens=meta.output_tokens,
                    cost_usd=meta.estimated_cost_usd,
                    latency_ms=meta.latency_ms,
                    success=True,
                )
                return signal
            except Exception as exc:
                latency_ms = int((perf_counter() - started) * 1000)
                trace.write(
                    "llm_call",
                    node=self.name,
                    ticker=doc.ticker,
                    role="extraction",
                    model="unknown",
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    cost_usd=0.0,
                    prompt=doc.content,
                    response=None,
                    success=False,
                    error=str(exc),
                )
                insert_llm_call(
                    run_id=run_id,
                    model="unknown",
                    role="extraction",
                    ticker=doc.ticker,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    latency_ms=latency_ms,
                    success=False,
                    error=str(exc),
                )
                return None

    async def _execute(self, state: AgentState) -> AgentState:
        run_id = state["metadata"].run_id
        trace = TraceWriter(run_id)

        results = await asyncio.gather(
            *(self._extract_one(doc, run_id, trace) for doc in state["raw_documents"])
        )

        docs = state["raw_documents"]
        output = [sig for sig in results if sig is not None]
        failed_tickers = {docs[i].ticker for i, sig in enumerate(results) if sig is None}
        if failed_tickers:
            state["metadata"].warnings.append(
                {
                    "agent": self.name,
                    "warning": f"{len(results) - len(output)}/{len(results)} extractions failed",
                    "tickers": sorted(failed_tickers),
                }
            )

        state["extracted_signals"] = output
        return state
