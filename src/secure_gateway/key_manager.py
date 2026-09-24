"""
Enterprise key management for the secure gateway.

Responsibilities:
- key rotation (based on config)
- key archival (keys_archive.json)
- audit logging
- generating new keys (delegated to algorithm classes)
- independent of specific crypto algorithms
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import aiofiles
import json   # <-- import adăugat

from secure_gateway.exceptions import HMACError
from secure_gateway.key_loader import KeyFileStore
from secure_gateway.algorithms import ALGORITHM_REGISTRY


class KeyManager:
    """
    Class-based enterprise key manager.

    Handles:
    - loading keys.json
    - archiving old keys
    - generating new keys via AlgorithmRegistry
    - writing updated keys.json
    - writing audit logs
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config

        self.keys_file = Path(config["crypto"]["keys_file"])
        self.archive_file = Path(config["crypto"]["keys_archive"])
        self.audit_path = Path(config["audit"]["path"])

        self.env = config["environment"]
        self.key_name = f"{self.env}_key"

        self.algo_name = config["crypto"]["algorithm"]
        self.min_len = config["crypto"]["min_key_length"]

    # ---------------------------------------------------------
    # Rotation interval check
    # ---------------------------------------------------------
    @staticmethod
    def rotation_needed(config: Dict[str, Any], last_rotation: datetime) -> bool:
        interval = config["crypto"]["rotation_interval_days"]
        return datetime.now(timezone.utc) >= last_rotation + timedelta(days=interval)

    # ---------------------------------------------------------
    # Generate new key via algorithm registry
    # ---------------------------------------------------------
    def _generate_new_key(self) -> str:
        try:
            algorithm = ALGORITHM_REGISTRY.get(self.algo_name)
        except HMACError as exc:
            raise HMACError(f"Algorithm '{self.algo_name}' not found") from exc

        return algorithm.generate_key(self.min_len)

    # ---------------------------------------------------------
    # Async key rotation
    # ---------------------------------------------------------
    async def rotate_async(self) -> None:
        """
        Enterprise key rotation:
        - load keys.json
        - archive old key
        - generate new key
        - write updated keys.json
        - write audit entry
        """

        # Load keys.json
        keys = await KeyFileStore.load_async(self.keys_file)

        # Load archive (if exists)
        archive: Dict[str, Any] = {}
        if self.archive_file.exists():
            archive = await KeyFileStore.load_async(self.archive_file)

        # Archive old key
        timestamp = datetime.now(timezone.utc).isoformat()
        archive_key_name = f"{self.key_name}_archived_{timestamp}"
        old_key = keys.get(self.key_name)
        if old_key is None:
            raise HMACError(f"Missing key '{self.key_name}' in keys.json")

        archive[archive_key_name] = old_key

        await KeyFileStore.write_async(self.archive_file, archive)

        # Generate new key
        new_key = self._generate_new_key()
        keys[self.key_name] = new_key

        # Write updated keys.json
        await KeyFileStore.write_async(self.keys_file, keys)

