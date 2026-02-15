from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import time

import requests

from secret_loader import get_secret


@dataclass
class NotifyResult:
    sent: bool
    reason: str


def _enabled() -> bool:
    return os.getenv("DISCORD_RESTART_NOTIFY", "true").strip().lower() in {"1", "true", "yes", "on"}


def _status_url() -> str:
    return os.getenv("STATUS_URL", "http://192.168.1.55:7777/health")


def _retry_count() -> int:
    try:
        return max(1, int(os.getenv("DISCORD_RESTART_RETRIES", "3")))
    except ValueError:
        return 3


def send_restart_notification() -> NotifyResult:
    """Send a Discord restart notification with retry; includes UTC time and status URL."""
    if not _enabled():
        return NotifyResult(sent=False, reason="disabled")

    webhook = get_secret("DISCORD_WEBHOOK_URL")
    if not webhook:
        return NotifyResult(sent=False, reason="missing_webhook")

    status_url = _status_url()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    payload = {
        "content": f"🔁 Farmbot container restarted at {now}. Status: {status_url}",
    }

    last_error = None
    for attempt in range(1, _retry_count() + 1):
        try:
            requests.post(webhook, json=payload, timeout=10).raise_for_status()
            return NotifyResult(sent=True, reason=f"sent_attempt_{attempt}")
        except Exception as exc:  # pragma: no cover - defensive network retries
            last_error = exc
            if attempt < _retry_count():
                time.sleep(1)

    return NotifyResult(sent=False, reason=f"post_failed:{last_error}")
