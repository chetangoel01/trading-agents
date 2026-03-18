"""Token counting helpers."""

from __future__ import annotations


class TokenCounter:
    """Lightweight token estimator with optional tiktoken backend."""

    def __init__(self, encoding: str = "cl100k_base") -> None:
        self.encoding_name = encoding
        self._encoder = None
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding(encoding)
        except Exception:
            self._encoder = None

    def count(self, text: str) -> int:
        if self._encoder is not None:
            return len(self._encoder.encode(text))
        # fallback heuristic: ~4 chars/token average
        return max(1, len(text) // 4)

    def truncate(self, text: str, max_tokens: int) -> tuple[str, bool]:
        if self.count(text) <= max_tokens:
            return text, False
        if self._encoder is not None:
            tokens = self._encoder.encode(text)[:max_tokens]
            return self._encoder.decode(tokens), True
        max_chars = max_tokens * 4
        return text[:max_chars], True
