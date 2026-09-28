from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
from typing import Any

import msgpack

COMPRESSION_LEVEL = 6


class ChunkWriter:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def write_packed(self, relative: str, payload: Any) -> int:
        data = gzip.compress(msgpack.packb(payload, use_bin_type=True), compresslevel=COMPRESSION_LEVEL)
        return self._atomic_write(relative, data)

    def write_json(self, relative: str, payload: Any) -> int:
        data = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        return self._atomic_write(relative, data)

    def _atomic_write(self, relative: str, data: bytes) -> int:
        target = self.directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_bytes(data)
        os.replace(temporary, target)
        return len(data)


def read_packed(path: Path) -> Any:
    return msgpack.unpackb(gzip.decompress(path.read_bytes()), raw=False, strict_map_key=False)
