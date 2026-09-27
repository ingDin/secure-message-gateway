"""
@summary
Asynchronous loader and writer for key‑related JSON files used by the
secure‑message‑gateway. This module is intentionally specialized and handles
ONLY the following files:

- keys.json
- keys_archive.json

It provides deterministic loading and storage of key material and raises
`HMACError` for any failure to ensure predictable and auditable behavior.
"""

import json
from pathlib import Path
from typing import Dict, Any
import aiofiles

from secure_gateway.exceptions import HMACError


class KeyFileStore:
    """
    @summary
    Async loader/writer for key‑related JSON files. This class is NOT a generic
    JSON loader — it is strictly dedicated to key storage files used by the
    gateway.

    Supported files:
    - keys.json
    - keys_archive.json

    @examples
    >>> keys = await KeyFileStore.load_async(Path("keys.json"))
    >>> await KeyFileStore.write_async(Path("keys_archive.json"), keys)
    """

    @staticmethod
    async def load_async(path: Path) -> Dict[str, Any]:
        """
        @summary
        Asynchronously load and parse a key JSON file.

        @parameters
        path : Path
            Path to the JSON file (keys.json or keys_archive.json).

        @returns
        dict
            Parsed JSON content containing key material.

        @raises
        HMACError
            If the file cannot be opened, read, or parsed.

        @examples
        >>> keys = await KeyFileStore.load_async(Path("keys.json"))
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
        @summary
        Asynchronously write key material to a JSON file.

        @parameters
        path : Path
            Path to the JSON file to write.
        content : dict
            Key material to persist.

        @returns
        None

        @raises
        HMACError
            If the file cannot be written.

        @examples
        >>> await KeyFileStore.write_async(Path("keys_archive.json"), {"prod_key": "abcd"})
        """
        try:
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(content, indent=2))
        except Exception as exc:
            raise HMACError(f"Failed to write key file: {path}") from exc
