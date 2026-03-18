from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import numpy as np

from agents.base import BaseAgent
from config import CACHE_TTL_MARKET_DATA, FINNHUB_API_KEY, TECHNICAL_LOOKBACK_DAYS
from state import AgentState, TechnicalSnapshot
from utils.cache import Cache


class MarketDataFetcherAgent(BaseAgent):
    name = "fetch_market_data"

    def __init__(self) -> None:
        super().__init__()
        self.cache = Cache()

    @staticmethod
    def _sma(values: list[float], window: int) -> float | None:
        if len(values) < window:
            return None
        return float(np.mean(values[-window:]))

    @staticmethod
    def _rsi(values: list[float], window: int = 14) -> float | None:
        if len(values) <= window:
            return None
        deltas = np.diff(values[-(window + 1) :])
        gains = np.maximum(deltas, 0)
        losses = -np.minimum(deltas, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    @staticmethod
    def _macd(values: list[float]) -> tuple[float | None, float | None, float | None]:
        if len(values) < 35:
            return None, None, None
        series = np.array(values, dtype=float)
        ema12 = _ema(series, 12)
        ema26 = _ema(series, 26)
        if ema12 is None or ema26 is None:
            return None, None, None
        macd_line = ema12 - ema26
        macd_hist = _ema(np.array([macd_line]), 9)
        signal = macd_hist if macd_hist is not None else macd_line
        histogram = macd_line - signal
        return float(macd_line), float(signal), float(histogram)

    @staticmethod
    def _bbands(values: list[float], window: int = 20) -> tuple[float | None, float | None, float | None]:
        if len(values) < window:
            return None, None, None
        arr = np.array(values[-window:], dtype=float)
        mean = float(np.mean(arr))
        std = float(np.std(arr))
        upper = mean + (2 * std)
        lower = mean - (2 * std)
        return upper, mean, lower

    @staticmethod
    def _obv(closes: list[float], volumes: list[int]) -> float | None:
        if len(closes) < 2 or len(closes) != len(volumes):
            return None
        obv = 0.0
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv += volumes[i]
            elif closes[i] < closes[i - 1]:
                obv -= volumes[i]
        return obv

    @classmethod
    def _snapshot_from_bars(
        cls, *, ticker: str, closes: list[float], volumes: list[int], as_of: datetime
    ) -> TechnicalSnapshot:
        price = closes[-1]
        sma_20 = cls._sma(closes, 20)
        sma_50 = cls._sma(closes, 50)
        sma_200 = cls._sma(closes, 200)
        rsi_14 = cls._rsi(closes, 14)
        macd, macd_signal, macd_histogram = cls._macd(closes)
        bb_upper, bb_middle, bb_lower = cls._bbands(closes, 20)
        obv = cls._obv(closes, volumes)

        price_vs_sma_200 = None
        if sma_200 is not None:
            price_vs_sma_200 = "above" if price > sma_200 else "below"
        rsi_zone = None
        if rsi_14 is not None:
            if rsi_14 < 30:
                rsi_zone = "oversold"
            elif rsi_14 > 70:
                rsi_zone = "overbought"
            else:
                rsi_zone = "neutral"
        bbands_position = None
        if bb_upper is not None and bb_lower is not None and bb_middle is not None:
            if price > bb_upper:
                bbands_position = "above_upper"
            elif price < bb_lower:
                bbands_position = "below_lower"
            else:
                bbands_position = "middle"

        return TechnicalSnapshot(
            ticker=ticker,
            timestamp=as_of,
            price=price,
            volume=volumes[-1],
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            rsi_14=rsi_14,
            macd=macd,
            macd_signal=macd_signal,
            macd_histogram=macd_histogram,
            bbands_upper=bb_upper,
            bbands_middle=bb_middle,
            bbands_lower=bb_lower,
            vwap=float(np.average(closes, weights=volumes)),
            atr_14=None,
            obv=obv,
            price_vs_sma_200=price_vs_sma_200,
            rsi_zone=rsi_zone,
            macd_crossover=(
                "bullish"
                if macd is not None and macd_signal is not None and macd > macd_signal
                else "bearish"
                if macd is not None and macd_signal is not None and macd < macd_signal
                else "none"
            ),
            bbands_position=bbands_position,
        )

    async def _fetch_bars(
        self, client: httpx.AsyncClient, ticker: str
    ) -> tuple[list[float], list[int]]:
        if not FINNHUB_API_KEY:
            return [], []
        cache_key = f"technicals:{ticker}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached.get("closes", []), cached.get("volumes", [])

        end = datetime.now(UTC)
        start = end - timedelta(days=TECHNICAL_LOOKBACK_DAYS)
        params = {
            "symbol": ticker,
            "resolution": "D",
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
            "token": FINNHUB_API_KEY,
        }
        response = await client.get("https://finnhub.io/api/v1/stock/candle", params=params)
        if response.status_code >= 400:
            return [], []
        payload = response.json()
        closes = payload.get("c", [])
        volumes = payload.get("v", [])
        if not isinstance(closes, list) or not isinstance(volumes, list):
            return [], []
        await self.cache.set(
            cache_key,
            {"closes": closes, "volumes": volumes},
            ttl=CACHE_TTL_MARKET_DATA,
        )
        return [float(c) for c in closes], [int(v) for v in volumes]

    async def _execute(self, state: AgentState) -> AgentState:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for ticker in state["metadata"].tickers:
                closes, volumes = await self._fetch_bars(client, ticker)
                if not closes or not volumes or len(closes) != len(volumes):
                    state["metadata"].warnings.append(
                        {
                            "agent": self.name,
                            "ticker": ticker,
                            "warning": "insufficient market data for indicators",
                        }
                    )
                    continue
                state["technical_data"].append(
                    self._snapshot_from_bars(
                        ticker=ticker, closes=closes, volumes=volumes, as_of=datetime.now(UTC)
                    )
                )
        return state


def _ema(values: np.ndarray, period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = float(np.mean(values[:period]))
    for v in values[period:]:
        ema = (float(v) * k) + (ema * (1 - k))
    return ema
