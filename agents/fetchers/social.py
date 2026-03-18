from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class SocialFetcherAgent(BaseAgent):
    name = "fetch_social"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
