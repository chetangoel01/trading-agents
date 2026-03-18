from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class DecisionAgent(BaseAgent):
    name = "decide"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
