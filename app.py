import logging
import os
from flask import Flask, jsonify, request

from farmbot_actions import ActionRunner, build_default_actions


def create_app() -> Flask:
    app = Flask(__name__)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("farmbot-web")

    runner = ActionRunner(build_default_actions(), logger=logger)

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

    @app.get("/actions")
    def list_actions() -> tuple:
        return jsonify({"actions": sorted(runner.available_actions())}), 200

    return app


app = create_app()


if __name__ == "__main__":
    # Local debug only. Production should run with Gunicorn.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
