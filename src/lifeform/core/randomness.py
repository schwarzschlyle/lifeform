from __future__ import annotations

import hashlib
from typing import Any

import numpy as np


class RandomStreams:
    """Independent, reproducible random generators, one per named subsystem."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._streams: dict[str, np.random.Generator] = {}

    def stream(self, name: str) -> np.random.Generator:
        if name not in self._streams:
            self._streams[name] = np.random.default_rng(np.random.SeedSequence([self.seed, self._name_key(name)]))
        return self._streams[name]

    def states(self) -> dict[str, dict[str, Any]]:
        return {name: dict(generator.bit_generator.state) for name, generator in self._streams.items()}

    def restore(self, states: dict[str, dict[str, Any]]) -> None:
        for name, state in states.items():
            self.stream(name).bit_generator.state = state

    @staticmethod
    def _name_key(name: str) -> int:
        return int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "little")
