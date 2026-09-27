"""
@summary
Enterprise key management subsystem for the secure‑message‑gateway.

Responsibilities:
- deterministic key rotation (based on config)
- archival of old keys into keys_archive.json
- generation of new keys via algorithm registry
- writing updated keys.json
- audit logging (performed by the gateway)

KeyManager is algorithm‑agnostic and delegates key generation to the selected
crypto backend via AlgorithmRegistry.
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import aiofiles
import json

from secure_gateway.exceptions import HMACError
from secure_gateway.key_loader import KeyFileStore
from secure_gateway.algorithms import ALGORITHM_REGISTRY


class KeyManager:
    """
    @summary
    Class‑based enterprise key manager responsible for loading, rotating,
    archiving, and updating cryptographic keys used by the gateway.

    Responsibilities:
    - load keys.json
    - archive old keys deterministically
    - generate new keys via AlgorithmRegistry
    - write updated keys.json
    - support audit logging (performed externally)

    @parameters
    config : dict
        Parsed gateway configuration containing crypto, audit, and environment
        settings.

    @examples
    >>> km = KeyManager(config)
    >>> await km.rotate_async()
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

    @staticmethod
    def rotation_needed(config: Dict[str, Any], last_rotation: datetime) -> bool:
        """
        @summary
        Determine whether key rotation is required based on the configured
        rotation interval.

        @parameters
        config : dict
            Gateway configuration containing crypto settings.
        last_rotation : datetime
            Timestamp of the last key rotation.

        @returns
        bool
            True if rotation interval has expired, False otherwise.

        @examples
        >>> KeyManager.rotation_needed(config, last_rotation)
        """
        interval = config["crypto"]["rotation_interval_days"]
        return datetime.now(timezone.utc) >= last_rotation + timedelta(days=interval)

    def _generate_new_key(self) -> str:
        """
        @summary
        Generate a new cryptographic key using the configured algorithm backend.

        @returns
        str
            Hex‑encoded key material.

        @raises
        HMACError
            If the configured algorithm is not found in the registry.

        @examples
        >>> new_key = km._generate_new_key()
        """
        try:
            algorithm = ALGORITHM_REGISTRY.get(self.algo_name)
        except HMACError as exc:
            raise HMACError(f"Algorithm '{self.algo_name}' not found") from exc

        return algorithm.generate_key(self.min_len)

    async def rotate_async(self) -> None:
        """
        @summary
        Perform enterprise key rotation:
        - load keys.json
        - archive old key with timestamp
        - generate new key
        - update keys.json
        - write archive file

        @returns
        None

        @raises
        HMACError
            If keys.json is missing, corrupted, or key archival fails.

        @examples
        >>> await km.rotate_async()
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
