from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class StrategyEngine(BaseAgent):
    name = "strategize"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
