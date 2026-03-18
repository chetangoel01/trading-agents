"""Base agent abstraction with retries, timing, and error capture."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from state import AgentState
from utils.logger import get_logger
from utils.retry import retry_async


@dataclass
class AgentRunStats:
    latency_ms: int
    success: bool
    error: str | None = None


class BaseAgent:
    name: str = "base"
    max_retries: int = 3
    base_delay_seconds: float = 1.0

    def __init__(self) -> None:
        self.logger = get_logger(f"agent.{self.name}")

    async def run(self, state: AgentState) -> AgentState:
        start = perf_counter()
        try:
            result = await retry_async(
                lambda: self._execute(state),
                retries=self.max_retries,
                base_delay_seconds=self.base_delay_seconds,
            )
            latency_ms = int((perf_counter() - start) * 1000)
            state["metadata"].completed_nodes.append(self.name)
            self.logger.info("agent_success", extra={"extra": {"agent": self.name, "latency_ms": latency_ms}})
            return result
        except Exception as exc:
            latency_ms = int((perf_counter() - start) * 1000)
            state["metadata"].errors.append(
                {"agent": self.name, "error": str(exc), "latency_ms": latency_ms}
            )
            self.logger.error(
                "agent_error",
                extra={"extra": {"agent": self.name, "error": str(exc), "latency_ms": latency_ms}},
            )
            return state

    async def _execute(self, state: AgentState) -> AgentState:
        raise NotImplementedError

    def metadata(self) -> dict[str, Any]:
        return {"name": self.name, "max_retries": self.max_retries}
