import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
threads = int(os.getenv("GUNICORN_THREADS", "4"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
accesslog = "-"
errorlog = "-"


def when_ready(server):  # called once when the master process is ready
    try:
        from startup_notify import send_restart_notification

        result = send_restart_notification()
        server.log.info("Startup notify: %s (%s)", result.sent, result.reason)
    except Exception as exc:  # pragma: no cover - defensive logging
        server.log.warning("Startup notify failed: %s", exc)
