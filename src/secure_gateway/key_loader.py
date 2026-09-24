"""
Async key file loader for the secure gateway.

This module handles ONLY key-related JSON files:
- keys.json
- keys_archive.json

It provides:
- KeyFileStore (class with async load/write operations)
"""

import json
from pathlib import Path
from typing import Dict, Any
import aiofiles

from secure_gateway.exceptions import HMACError


class KeyFileStore:
    """
    Async loader/writer for key-related JSON files.
    This class is intentionally NOT a generic JSON loader.
    It is specialized for:
    - keys.json
    - keys_archive.json
    """

    @staticmethod
    async def load_async(path: Path) -> Dict[str, Any]:
        """
        Load and parse keys.json or keys_archive.json asynchronously.
        """
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                raw = await f.read()
                return json.loads(raw)
        except Exception as exc:
            raise HMACError(f"Failed to load key file: {path}") from exc

    @staticmethod
    async def write_async(path: Path, content: Dict[str, Any]) -> None:
        """
        Write keys.json or keys_archive.json asynchronously.
        """
        try:
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(content, indent=2))
        except Exception as exc:
            raise HMACError(f"Failed to write key file: {path}") from exc
