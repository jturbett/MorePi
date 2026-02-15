import logging
import os

from startup_notify import send_restart_notification

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
accesslog = "-"
errorlog = "-"


def on_starting(server):
    """Gunicorn hook: runs once in master process on startup/restart."""
    try:
        sent = send_restart_notification()
        if sent:
            server.log.info("Sent Discord restart notification")
        else:
            server.log.info("Discord restart notification skipped (disabled or no webhook)")
    except Exception as exc:  # pragma: no cover
        logging.getLogger("gunicorn.error").warning("Restart notification failed: %s", exc)
