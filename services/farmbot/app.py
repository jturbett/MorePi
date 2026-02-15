import logging
import os
import threading
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request

from farmbot_actions import ActionRunner, build_default_actions
from secret_loader import get_secret


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def _extract_camera_name(payload: dict) -> str | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}

    candidates = [
        payload.get("camera_name"),
        payload.get("camera"),
        payload.get("deviceName"),
        payload.get("name"),
        event.get("camera_name"),
        event.get("cameraName"),
        event.get("camera"),
        event.get("deviceName"),
    ]

    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("name")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_motion_detected(payload: dict) -> bool:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}

    bool_candidates = [
        payload.get("motion"),
        payload.get("isMotionDetected"),
        payload.get("has_motion"),
        event.get("motion"),
        event.get("isMotionDetected"),
        event.get("has_motion"),
    ]

    for candidate in bool_candidates:
        as_bool = _coerce_bool(candidate)
        if as_bool is not None:
            return as_bool

    type_candidates = [payload.get("type"), event.get("type"), event.get("eventType")]
    for event_type in type_candidates:
        if isinstance(event_type, str):
            normalized = event_type.lower()
            if "motion" in normalized:
                return True

    # If no explicit motion field is provided, assume motion webhook semantics.
    return True


class MotionCooldown:
    def __init__(self, cooldown_seconds: int):
        self.cooldown_seconds = cooldown_seconds
        self._last_trigger: float | None = None
        self._in_flight = False
        self._lock = threading.Lock()

    def begin(self) -> tuple[bool, int, str | None]:
        now = time.monotonic()
        with self._lock:
            if self._in_flight:
                return False, 0, "in_flight"
            if self._last_trigger is not None:
                elapsed = now - self._last_trigger
                if elapsed < self.cooldown_seconds:
                    remaining = int(self.cooldown_seconds - elapsed)
                    return False, remaining, "cooldown"
            self._in_flight = True
            return True, 0, None

    def finish(self, success: bool) -> None:
        with self._lock:
            if success:
                self._last_trigger = time.monotonic()
            self._in_flight = False


def _has_unifi_api_key_access(request_obj, expected_key: str) -> bool:
    header_key = request_obj.headers.get("X-API-Key", "").strip()
    if header_key and header_key == expected_key:
        return True

    auth_header = request_obj.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header[7:].strip()
        if bearer_token == expected_key:
            return True

    return False





def _request_origin_matches_unifi_host(request_obj, expected_host: str | None) -> bool:
    if not expected_host:
        return True

    expected_host = expected_host.strip()
    if not expected_host:
        return True

    forwarded_for = request_obj.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first == expected_host:
            return True

    remote_addr = (request_obj.remote_addr or "").strip()
    if remote_addr in {"127.0.0.1", "::1"}:
        return True
    return remote_addr == expected_host

def _load_unifi_api_key() -> str | None:
    configured_secret = get_secret("UNIFI_PROTECT_API_KEY")
    if configured_secret:
        return configured_secret

    default_secret_file = Path("secrets/unifi_key")
    if default_secret_file.exists():
        value = default_secret_file.read_text(encoding="utf-8").strip()
        if value:
            return value

    return None


def _load_discord_unifi_webhook() -> str | None:
    return get_secret("DISCORD_UNIFI_WEBHOOK_URL")


def _extract_event_type(payload: dict) -> str | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    for candidate in (payload.get("type"), event.get("type"), event.get("eventType")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _extract_event_time(payload: dict) -> str | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    for candidate in (payload.get("time"), payload.get("timestamp"), event.get("time"), event.get("timestamp")):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None

def create_app() -> Flask:
    app = Flask(__name__)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("farmbot-web")

    runner = ActionRunner(build_default_actions(), logger=logger)
    target_camera_name = os.getenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    require_camera_match = _coerce_bool(os.getenv("UNIFI_MOTION_REQUIRE_CAMERA", "true"))
    require_motion_flag = _coerce_bool(os.getenv("UNIFI_MOTION_REQUIRE_MOTION", "true"))
    motion_trigger_url = os.getenv(
        "UNIFI_MOTION_TRIGGER_URL",
        "http://192.168.1.55:7777/trigger/demo_move_home?x=600&y=400&z=0",
    )
    cooldown_seconds = int(os.getenv("UNIFI_MOTION_COOLDOWN_SECONDS", "1200"))
    cooldown = MotionCooldown(cooldown_seconds)
    trigger_method = os.getenv("UNIFI_MOTION_TRIGGER_METHOD", "GET").upper()
    trigger_timeout = int(os.getenv("UNIFI_MOTION_TRIGGER_TIMEOUT", "60"))
    unifi_api_key = _load_unifi_api_key()
    unifi_protect_host = os.getenv("UNIFI_PROTECT_HOST", "192.168.1.59").strip()
    discord_unifi_webhook = _load_discord_unifi_webhook()

    @app.get("/health")
    def health() -> tuple:
        return jsonify({"status": "ok"}), 200

    @app.post("/trigger/<action_name>")
    def trigger_action(action_name: str) -> tuple:
        payload = request.get_json(silent=True) or {}
        try:
            result = runner.run(action_name, payload)
            return jsonify({"status": "ok", "action": action_name, "result": result}), 200
        except KeyError:
            return jsonify({"status": "error", "message": f"Unknown action: {action_name}"}), 404
        except Exception as exc:  # pragma: no cover - defensive handler for runtime integrations
            logger.exception("Failed to execute action '%s'", action_name)
            return jsonify({"status": "error", "message": str(exc)}), 500

    @app.get("/trigger/<action_name>")
    def trigger_action_get(action_name: str) -> tuple:
        payload = dict(request.args)
        try:
            result = runner.run(action_name, payload)
            return jsonify({"status": "ok", "action": action_name, "result": result}), 200
        except KeyError:
            return jsonify({"status": "error", "message": f"Unknown action: {action_name}"}), 404
        except Exception as exc:  # pragma: no cover - defensive handler for runtime integrations
            logger.exception("Failed to execute action '%s'", action_name)
            return jsonify({"status": "error", "message": str(exc)}), 500

    @app.get("/actions")
    def list_actions() -> tuple:
        return jsonify({"actions": sorted(runner.available_actions())}), 200

    @app.post("/webhooks/unifi-protect-motion")
    def unifi_protect_motion() -> tuple:
        payload = request.get_json(silent=True) or {}
        if not _request_origin_matches_unifi_host(request, unifi_protect_host):
            logger.warning("Rejected UniFi webhook request from unexpected host: %s", request.remote_addr)
            return jsonify({"status": "error", "message": "Forbidden source"}), 403

        if unifi_api_key and not _has_unifi_api_key_access(request, unifi_api_key):
            logger.warning("Rejected UniFi webhook request due to invalid API key")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        camera_name = _extract_camera_name(payload)
        motion_detected = _extract_motion_detected(payload)

        if require_camera_match and camera_name != target_camera_name:
            logger.info(
                "Ignoring motion event for camera '%s' (target='%s')",
                camera_name,
                target_camera_name,
            )
            return jsonify({"status": "ignored", "reason": "camera_mismatch"}), 202

        if require_motion_flag and not motion_detected:
            logger.info("Ignoring non-motion event for camera '%s'", camera_name)
            return jsonify({"status": "ignored", "reason": "no_motion"}), 202

        allowed, remaining, reason = cooldown.begin()
        if not allowed:
            if reason == "in_flight":
                logger.info("Motion ignored while prior trigger is still running for camera '%s'", camera_name)
                return jsonify({"status": "ignored", "reason": "in_flight"}), 202

            logger.info(
                "Motion ignored due to cooldown for camera '%s' (%ss remaining)",
                camera_name,
                remaining,
            )
            return (
                jsonify(
                    {
                        "status": "ignored",
                        "reason": "cooldown",
                        "remaining_seconds": remaining,
                    }
                ),
                202,
            )

        try:
            if trigger_method == "POST":
                response = requests.post(motion_trigger_url, timeout=trigger_timeout)
            else:
                response = requests.get(motion_trigger_url, timeout=trigger_timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            cooldown.finish(success=False)
            logger.exception("Failed to trigger farmbot demo URL")
            return jsonify({"status": "error", "message": str(exc)}), 502
        except Exception as exc:  # pragma: no cover - defensive unlock path
            cooldown.finish(success=False)
            logger.exception("Unexpected error while triggering farmbot demo URL")
            return jsonify({"status": "error", "message": str(exc)}), 500

        cooldown.finish(success=True)

        logger.info("Motion trigger fired for camera '%s'", camera_name)
        return jsonify({"status": "ok", "camera": camera_name, "trigger_url": motion_trigger_url}), 200

    @app.post("/webhooks/unifi-protect-discord")
    def unifi_protect_discord() -> tuple:
        payload = request.get_json(silent=True) or {}
        if not _request_origin_matches_unifi_host(request, unifi_protect_host):
            logger.warning("Rejected UniFi webhook request from unexpected host: %s", request.remote_addr)
            return jsonify({"status": "error", "message": "Forbidden source"}), 403

        if unifi_api_key and not _has_unifi_api_key_access(request, unifi_api_key):
            logger.warning("Rejected UniFi webhook request due to invalid API key")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        if not discord_unifi_webhook:
            return jsonify({"status": "error", "message": "Discord webhook not configured"}), 500

        alarm = payload.get("alarm") if isinstance(payload.get("alarm"), dict) else {}
        triggers = alarm.get("triggers") if isinstance(alarm.get("triggers"), list) else []
        first_trigger = triggers[0] if triggers else {}

        camera_name = _extract_camera_name(payload) or alarm.get("name") or "Unknown source"
        motion_detected = _extract_motion_detected(payload)
        event_type = _extract_event_type(payload) or first_trigger.get("key") or "event"
        event_value = first_trigger.get("value")
        event_time = _extract_event_time(payload)
        event_link = alarm.get("eventLocalLink")

        status = "motion detected" if motion_detected else "event received"
        content = f"UniFi Protect: {camera_name} — {status} ({event_type})"
        if event_value:
            content = f"{content}: {event_value}"
        if event_time:
            content = f"{content} @ {event_time}"
        if event_link:
            content = f"{content}\n{event_link}"

        try:
            requests.post(discord_unifi_webhook, json={"content": content}, timeout=10).raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Failed to post UniFi event to Discord")
            return jsonify({"status": "error", "message": str(exc)}), 502

        return jsonify({"status": "ok", "camera": camera_name, "event": event_type}), 200

    @app.post("/webhooks/unifi-protect-dump")
    def unifi_protect_dump() -> tuple:
        payload = request.get_json(silent=True) or {}

        logger.info("=== UNIFI PROTECT DUMP START ===")
        logger.info("Remote addr: %s", request.remote_addr)
        logger.info("Headers: %s", dict(request.headers))
        logger.info("Payload: %s", payload)
        logger.info("=== UNIFI PROTECT DUMP END ===")

        return (
            jsonify(
                {
                    "status": "ok",
                    "remote_addr": request.remote_addr,
                    "payload_keys": sorted(payload.keys()),
                }
            ),
            200,
        )

    return app


app = create_app()


if __name__ == "__main__":
    # Local debug only. Production should run with Gunicorn.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
