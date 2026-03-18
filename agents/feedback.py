from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class FeedbackAgent(BaseAgent):
    name = "feedback"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
