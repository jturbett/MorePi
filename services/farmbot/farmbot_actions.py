from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict

import requests
from farmbot import Farmbot

from secret_loader import get_secret

ActionCallable = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class ActionRunner:
    actions: Dict[str, ActionCallable]
    logger: logging.Logger

    def run(self, action_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action_name not in self.actions:
            raise KeyError(action_name)
        self.logger.info("Running action '%s' with payload=%s", action_name, payload)
        return self.actions[action_name](payload)

    def available_actions(self) -> set[str]:
        return set(self.actions)


def build_default_actions() -> Dict[str, ActionCallable]:
    return {
        "water_the_rock": water_the_rock,
        "lights_on": lights_on,
        "lights_off": lights_off,
        "vacuum_on": vacuum_on,
        "vacuum_off": vacuum_off,
        "rpi_on": rpi_on,
        "rpi_off": rpi_off,
        "rotary_forward": rotary_forward,
        "rotary_reverse": rotary_reverse,
        "rotary_stop": rotary_stop,
        "demo_move_home": demo_move_home,
        "demo_the_bot": demo_the_bot,
        "exercise_the_farmbot": exercise_the_farmbot,
        "yard_irrigation": yard_irrigation,
    }


def _post_webhook(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    requests.post(url, json=payload, timeout=10).raise_for_status()


def _send_teams_message(text: str) -> None:
    webhook = os.getenv("TEAMS_WEBHOOK_URL")
    _post_webhook(webhook, {"text": text})


def _send_discord_message(text: str) -> None:
    webhook = get_secret("DISCORD_WEBHOOK_URL")
    _post_webhook(webhook, {"content": text})


def _mock_farmbot_step(message: str, seconds: float = 0.2) -> None:
    logging.getLogger("farmbot-web").info(message)
    time.sleep(seconds)


def _load_farmbot_token() -> dict[str, Any]:
    token_json = get_secret("FARMBOT_TOKEN_JSON")
    if not token_json:
        raise RuntimeError("Missing FARMBOT_TOKEN_JSON (or FARMBOT_TOKEN_JSON_FILE)")
    try:
        return json.loads(token_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid FARMBOT_TOKEN_JSON contents") from exc


def _get_farmbot_client() -> Farmbot:
    token = _load_farmbot_token()
    fb = Farmbot()
    fb.set_token(token)
    return fb


def _pin_from_env(name: str) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}")
    return int(value)


def _toggle_pin(fb: Farmbot, pin: int, value: int) -> dict[str, Any]:
    if value:
        fb.on(pin)
    else:
        fb.off(pin)
    readback = fb.read_pin(pin, "digital")
    return {"pin": pin, "readback": readback, "verified": bool(readback == value)}


def water_the_rock(payload: dict[str, Any]) -> dict[str, Any]:
    x = payload.get("x", 200)
    y = payload.get("y", 200)
    water_seconds = payload.get("water_seconds", 1)

    message = f"Water the rock: ({x}, {y}) for {water_seconds}s"
    _send_teams_message(message)
    _send_discord_message(message)

    fb = _get_farmbot_client()
    lights_pin = _pin_from_env("LIGHTS_PIN")
    water_pin = _pin_from_env("WATER_PIN")
    lights_state = _toggle_pin(fb, lights_pin, 1)
    _mock_farmbot_step(f"Moving to ({x}, {y}, 0)")
    water_on = _toggle_pin(fb, water_pin, 1)
    _mock_farmbot_step(f"Watering for {water_seconds}s")
    water_off = _toggle_pin(fb, water_pin, 0)
    _mock_farmbot_step("Returning to home (0,0,0)")

    return {
        "x": x,
        "y": y,
        "water_seconds": water_seconds,
        "lights": lights_state,
        "water_on": water_on,
        "water_off": water_off,
    }


def lights_on(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")

    message = f"Lights on (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()

    pin = _pin_from_env("LIGHTS_PIN")
    pin_state = _toggle_pin(fb, pin, 1)

    return {
        "zone": zone,
        "status": "on",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def lights_off(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Lights off (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    pin = _pin_from_env("LIGHTS_PIN")
    pin_state = _toggle_pin(fb, pin, 0)
    return {
        "zone": zone,
        "status": "off",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def vacuum_on(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Vacuum on (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    pin = _pin_from_env("VACUUM_PIN")
    pin_state = _toggle_pin(fb, pin, 1)
    return {
        "zone": zone,
        "status": "on",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def vacuum_off(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Vacuum off (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    pin = _pin_from_env("VACUUM_PIN")
    pin_state = _toggle_pin(fb, pin, 0)
    return {
        "zone": zone,
        "status": "off",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def rpi_on(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Raspberry Pi on (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    pin = _pin_from_env("RPI_PIN")
    pin_state = _toggle_pin(fb, pin, 1)
    return {
        "zone": zone,
        "status": "on",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def rpi_off(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Raspberry Pi off (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    pin = _pin_from_env("RPI_PIN")
    pin_state = _toggle_pin(fb, pin, 0)
    return {
        "zone": zone,
        "status": "off",
        "action": f"pin:{pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def rotary_forward(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Rotary tool forward (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    fwd_pin = _pin_from_env("ROTARY_FWD_PIN")
    rev_pin = _pin_from_env("ROTARY_REV_PIN")
    _toggle_pin(fb, rev_pin, 0)
    pin_state = _toggle_pin(fb, fwd_pin, 1)
    return {
        "zone": zone,
        "status": "forward",
        "action": f"pin:{fwd_pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def rotary_reverse(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Rotary tool reverse (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    fwd_pin = _pin_from_env("ROTARY_FWD_PIN")
    rev_pin = _pin_from_env("ROTARY_REV_PIN")
    _toggle_pin(fb, fwd_pin, 0)
    pin_state = _toggle_pin(fb, rev_pin, 1)
    return {
        "zone": zone,
        "status": "reverse",
        "action": f"pin:{rev_pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def rotary_stop(payload: dict[str, Any]) -> dict[str, Any]:
    zone = payload.get("zone", "default")
    message = f"Rotary tool stop (zone={zone})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    fwd_pin = _pin_from_env("ROTARY_FWD_PIN")
    rev_pin = _pin_from_env("ROTARY_REV_PIN")
    _toggle_pin(fb, fwd_pin, 0)
    pin_state = _toggle_pin(fb, rev_pin, 0)
    return {
        "zone": zone,
        "status": "stopped",
        "action": f"pins:{fwd_pin},{rev_pin}",
        "readback": pin_state["readback"],
        "verified": pin_state["verified"],
    }


def demo_move_home(payload: dict[str, Any]) -> dict[str, Any]:
    x = int(payload.get("x", 400))
    y = int(payload.get("y", 300))
    z = int(payload.get("z", 0))
    speed = payload.get("speed")

    fb = _get_farmbot_client()
    lights_pin = _pin_from_env("LIGHTS_PIN")
    lights_on = _toggle_pin(fb, lights_pin, 1)
    _send_discord_message("Demo move: lights on")

    message = f"Demo move: going to ({x}, {y}, {z})"
    _send_teams_message(message)
    _send_discord_message(message)
    fb.move(x=x, y=y, z=z, speed=speed)
    at_target = fb.get_xyz()
    _send_discord_message(f"At target: {at_target}")

    message = "Demo move: returning to home (0, 0, 0)"
    _send_teams_message(message)
    _send_discord_message(message)
    fb.move(x=0, y=0, z=0, speed=speed)
    at_home = fb.get_xyz()
    _send_discord_message(f"At home: {at_home}")

    lights_off = _toggle_pin(fb, lights_pin, 0)
    _send_discord_message("Demo move: lights off")

    return {
        "target": {"x": x, "y": y, "z": z},
        "at_target": at_target,
        "at_home": at_home,
        "lights_on": lights_on,
        "lights_off": lights_off,
    }


def demo_the_bot(payload: dict[str, Any]) -> dict[str, Any]:
    message = "Demo requested"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    lights_pin = _pin_from_env("LIGHTS_PIN")
    lights_on = _toggle_pin(fb, lights_pin, 1)
    _send_discord_message("Demo: lights on")
    _mock_farmbot_step("Performing demo sequence")
    lights_off = _toggle_pin(fb, lights_pin, 0)
    _send_discord_message("Demo: lights off")
    return {"message": "demo sequence complete", "lights_on": lights_on, "lights_off": lights_off}


def exercise_the_farmbot(payload: dict[str, Any]) -> dict[str, Any]:
    loops = int(payload.get("loops", 3))
    message = f"Exercise requested for {loops} loops"
    _send_teams_message(message)
    _send_discord_message(message)
    for loop in range(loops):
        _mock_farmbot_step(f"Exercise loop {loop + 1}/{loops}")
    return {"loops": loops}


def yard_irrigation(payload: dict[str, Any]) -> dict[str, Any]:
    minutes = int(payload.get("minutes", 10))
    message = f"Yard irrigation started for {minutes} minutes"
    _send_teams_message(message)
    _send_discord_message(message)
    fb = _get_farmbot_client()
    irrigation_pin = _pin_from_env("IRRIGATION_PIN")
    irrigation_on = _toggle_pin(fb, irrigation_pin, 1)
    _mock_farmbot_step("Closing solenoid")
    irrigation_off = _toggle_pin(fb, irrigation_pin, 0)
    return {"minutes": minutes, "irrigation_on": irrigation_on, "irrigation_off": irrigation_off}
