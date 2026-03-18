from __future__ import annotations

from collections import defaultdict

from agents.base import BaseAgent
from config import STRATEGY_WEIGHTS
from state import (
    AgentState,
    ExtractedSignal,
    SignalDirection,
    StrategySignal,
    StrategyType,
    TechnicalSnapshot,
)


class StrategyEngine(BaseAgent):
    name = "strategize"

    @staticmethod
    def _momentum_signal(tech: TechnicalSnapshot) -> StrategySignal:
        confidence = 0.5
        direction = SignalDirection.NEUTRAL
        reasons: list[str] = []

        if tech.rsi_14 is not None:
            if tech.rsi_14 < 30:
                direction = SignalDirection.BULLISH
                confidence += 0.15
                reasons.append(f"RSI oversold ({tech.rsi_14:.0f})")
            elif tech.rsi_14 > 70:
                direction = SignalDirection.BEARISH
                confidence += 0.15
                reasons.append(f"RSI overbought ({tech.rsi_14:.0f})")

        if tech.price_vs_sma_200 == "above":
            if direction != SignalDirection.BEARISH:
                direction = SignalDirection.BULLISH
            confidence += 0.10
            reasons.append("price above SMA200")
        elif tech.price_vs_sma_200 == "below":
            if direction != SignalDirection.BULLISH:
                direction = SignalDirection.BEARISH
            confidence += 0.10
            reasons.append("price below SMA200")

        if tech.macd_crossover == "bullish":
            if direction != SignalDirection.BEARISH:
                direction = SignalDirection.BULLISH
            confidence += 0.10
            reasons.append("MACD bullish crossover")
        elif tech.macd_crossover == "bearish":
            if direction != SignalDirection.BULLISH:
                direction = SignalDirection.BEARISH
            confidence += 0.10
            reasons.append("MACD bearish crossover")

        confidence = min(1.0, confidence)
        return StrategySignal(
            strategy=StrategyType.MOMENTUM,
            ticker=tech.ticker,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons) or "no strong momentum signals",
            time_horizon="days",
            suggested_entry=tech.price,
        )

    @staticmethod
    def _sentiment_signal(ticker: str, extracted: list[ExtractedSignal]) -> StrategySignal | None:
        bullish = 0.0
        bearish = 0.0
        total_weight = 0.0
        for sig in extracted:
            for sent in sig.sentiments:
                weight = sent.source_credibility
                total_weight += weight
                if sent.direction == SignalDirection.BULLISH:
                    bullish += weight * sent.confidence
                elif sent.direction == SignalDirection.BEARISH:
                    bearish += weight * sent.confidence

        if total_weight == 0:
            return None

        if bullish > bearish:
            direction = SignalDirection.BULLISH
            confidence = min(1.0, bullish / total_weight)
        elif bearish > bullish:
            direction = SignalDirection.BEARISH
            confidence = min(1.0, bearish / total_weight)
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0.3

        return StrategySignal(
            strategy=StrategyType.SENTIMENT,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            reasoning=f"sentiment bullish={bullish:.2f} bearish={bearish:.2f}",
            time_horizon="days",
        )

    @staticmethod
    def _fundamental_signal(ticker: str, extracted: list[ExtractedSignal]) -> StrategySignal | None:
        positive_metrics = 0
        negative_metrics = 0
        for sig in extracted:
            for m in sig.metrics:
                if m.yoy_change is not None:
                    if m.yoy_change > 0:
                        positive_metrics += 1
                    else:
                        negative_metrics += 1
                if m.beat_estimate is True:
                    positive_metrics += 1
                elif m.beat_estimate is False:
                    negative_metrics += 1

        total = positive_metrics + negative_metrics
        if total == 0:
            return None

        ratio = positive_metrics / total
        if ratio > 0.6:
            direction = SignalDirection.BULLISH
        elif ratio < 0.4:
            direction = SignalDirection.BEARISH
        else:
            direction = SignalDirection.NEUTRAL

        confidence = min(1.0, 0.4 + 0.4 * abs(ratio - 0.5) * 2)
        return StrategySignal(
            strategy=StrategyType.FUNDAMENTAL,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            reasoning=f"positive={positive_metrics} negative={negative_metrics}",
            time_horizon="months",
        )

    @staticmethod
    def _mean_reversion_signal(tech: TechnicalSnapshot) -> StrategySignal | None:
        reasons: list[str] = []
        direction = SignalDirection.NEUTRAL
        confidence = 0.5

        if tech.rsi_14 is not None and tech.rsi_14 < 30:
            direction = SignalDirection.BULLISH
            confidence += 0.15
            reasons.append(f"RSI oversold reversal ({tech.rsi_14:.0f})")
        elif tech.rsi_14 is not None and tech.rsi_14 > 70:
            direction = SignalDirection.BEARISH
            confidence += 0.15
            reasons.append(f"RSI overbought reversal ({tech.rsi_14:.0f})")

        if tech.bbands_position == "below_lower":
            if direction != SignalDirection.BEARISH:
                direction = SignalDirection.BULLISH
            confidence += 0.15
            reasons.append("below lower Bollinger Band")
        elif tech.bbands_position == "above_upper":
            if direction != SignalDirection.BULLISH:
                direction = SignalDirection.BEARISH
            confidence += 0.15
            reasons.append("above upper Bollinger Band")

        if direction == SignalDirection.NEUTRAL:
            return None

        confidence = min(1.0, confidence)
        return StrategySignal(
            strategy=StrategyType.MEAN_REVERSION,
            ticker=tech.ticker,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            time_horizon="days",
            suggested_entry=tech.price,
        )

    @staticmethod
    def _event_driven_signal(ticker: str, extracted: list[ExtractedSignal]) -> StrategySignal | None:
        events: list[str] = []
        has_positive_guidance = False
        for sig in extracted:
            events.extend(sig.key_events)
            if sig.management_guidance and any(
                word in sig.management_guidance.lower()
                for word in ("raised", "increased", "positive", "strong", "beat")
            ):
                has_positive_guidance = True

        if not events:
            return None

        direction = SignalDirection.BULLISH if has_positive_guidance else SignalDirection.NEUTRAL
        confidence = min(1.0, 0.4 + 0.1 * len(events))
        if has_positive_guidance:
            confidence = min(1.0, confidence + 0.15)

        return StrategySignal(
            strategy=StrategyType.EVENT_DRIVEN,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            reasoning=f"{len(events)} events; guidance_positive={has_positive_guidance}",
            time_horizon="weeks",
        )

    async def _execute(self, state: AgentState) -> AgentState:
        signals: list[StrategySignal] = []

        tech_by_ticker: dict[str, TechnicalSnapshot] = {}
        for snap in state["technical_data"]:
            tech_by_ticker[snap.ticker] = snap

        extracted_by_ticker: dict[str, list[ExtractedSignal]] = defaultdict(list)
        for sig in state["extracted_signals"]:
            extracted_by_ticker[sig.ticker].append(sig)

        for ticker in state["metadata"].tickers:
            tech = tech_by_ticker.get(ticker)
            extracted = extracted_by_ticker.get(ticker, [])

            if tech:
                signals.append(self._momentum_signal(tech))
                mr = self._mean_reversion_signal(tech)
                if mr is not None:
                    signals.append(mr)

            if extracted:
                sent = self._sentiment_signal(ticker, extracted)
                if sent is not None:
                    signals.append(sent)

                fund = self._fundamental_signal(ticker, extracted)
                if fund is not None:
                    signals.append(fund)

                ev = self._event_driven_signal(ticker, extracted)
                if ev is not None:
                    signals.append(ev)

        state["strategy_signals"] = signals
        return state
