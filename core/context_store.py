"""
Context Store for Vera AI Assistant.

Manages in-memory state for all 4 context scopes (category, merchant, customer, trigger)
with version tracking and idempotent updates.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, Optional, Tuple


class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        # Key: (scope, context_id) -> {"version": int, "payload": dict, "updated_at": str}
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def push_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store context idempotently. Returns acceptance status.
        """
        with self._lock:
            key = (scope, context_id)
            existing = self._store.get(key)
            if existing and existing["version"] > version:
                return {
                    "accepted": False,
                    "reason": "stale_version",
                    "current_version": existing["version"]
                }
            
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            self._store[key] = {
                "version": version,
                "payload": payload,
                "updated_at": now_iso
            }
            return {
                "accepted": True,
                "ack_id": f"ack_{context_id}_v{version}",
                "stored_at": now_iso
            }

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payload for a specific scope and context_id."""
        with self._lock:
            entry = self._store.get((scope, context_id))
            return entry["payload"] if entry else None

    def get_all(self, scope: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve all payloads for a given scope."""
        with self._lock:
            results = {}
            for (s, cid), entry in self._store.items():
                if s == scope:
                    results[cid] = entry["payload"]
            return results

    def get_counts(self) -> Dict[str, int]:
        """Get counts of loaded contexts per scope."""
        with self._lock:
            counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
            for (scope, _), _ in self._store.items():
                counts[scope] = counts.get(scope, 0) + 1
            return counts

    def clear(self):
        """Wipe all stored contexts."""
        with self._lock:
            self._store.clear()
