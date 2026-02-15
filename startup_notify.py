from __future__ import annotations

from datetime import datetime, timezone
import os

import requests

from secret_loader import get_secret


def _enabled() -> bool:
    return os.getenv("DISCORD_RESTART_NOTIFY", "true").strip().lower() in {"1", "true", "yes", "on"}


def send_restart_notification() -> bool:
    """Send a Discord restart notification; returns True when sent."""
    if not _enabled():
        return False

    webhook = get_secret("DISCORD_WEBHOOK_URL")
    if not webhook:
        return False

    status_url = os.getenv("STATUS_URL", "http://localhost:7777/health")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    payload = {
        "content": f"🔁 Farmbot container restarted at {now}. Status: {status_url}",
    }
    requests.post(webhook, json=payload, timeout=10).raise_for_status()
    return True
