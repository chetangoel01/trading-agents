from __future__ import annotations

from agents.base import BaseAgent
from state import AgentState


class TranscriptFetcherAgent(BaseAgent):
    name = "fetch_transcripts"

    async def _execute(self, state: AgentState) -> AgentState:
        return state
