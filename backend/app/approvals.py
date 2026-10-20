import hashlib
import json
import secrets
import time
from typing import Any


class ApprovalStore:
    def __init__(self) -> None:
        self._pending: dict[str, tuple[str, float]] = {}

    @staticmethod
    def _fingerprint(action: str, target_id: int | None, payload: Any) -> str:
        payload = json.dumps(
            {"action": action, "target_id": target_id, "payload": payload},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def issue(self, action: str, target_id: int | None, payload: Any) -> str:
        self._prune_expired()
        token = secrets.token_urlsafe(32)
        self._pending[token] = (self._fingerprint(action, target_id, payload), time.time() + 300)
        return token

    def consume(self, token: str, action: str, target_id: int | None, payload: Any) -> bool:
        pending = self._pending.pop(token, None)
        return bool(
            pending
            and pending[1] >= time.time()
            and pending[0] == self._fingerprint(action, target_id, payload)
        )

    def _prune_expired(self) -> None:
        now = time.time()
        self._pending = {token: item for token, item in self._pending.items() if item[1] >= now}
