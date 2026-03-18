from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class NewsFetcherAgent(BaseAgent):
    name = "fetch_news"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
