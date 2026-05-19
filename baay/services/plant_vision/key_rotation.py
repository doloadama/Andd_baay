import itertools
import logging
from typing import List

logger = logging.getLogger(__name__)


class GeminiKeyRotator:
    """Rotation synchrone des clés Gemini en cas de quota dépassé."""

    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("Au moins une clé Gemini est requise.")
        self.keys = keys
        self._cycle = itertools.cycle(keys)
        self._current = next(self._cycle)

    @property
    def current_key(self) -> str:
        return self._current

    def rotate(self) -> str:
        previous = self._current
        self._current = next(self._cycle)
        if previous != self._current:
            logger.warning("Quota Gemini — bascule vers une autre clé.")
        return self._current
