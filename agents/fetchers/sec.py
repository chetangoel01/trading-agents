from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class SECFetcherAgent(BaseAgent):
    name = "fetch_sec"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
