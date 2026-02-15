from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict

import requests

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
        "demo_the_bot": demo_the_bot,
        "exercise_the_farmbot": exercise_the_farmbot,
        "yard_irrigation": yard_irrigation,
        "light_on": light_on,
        "light_off": light_off,
    }


def _send_chat_message(text: str) -> None:
    discord_webhook = get_secret("DISCORD_WEBHOOK_URL")
    if not discord_webhook:
        return

    requests.post(discord_webhook, json={"content": text}, timeout=10).raise_for_status()


def _mock_farmbot_step(message: str, seconds: float = 0.2) -> None:
    logging.getLogger("farmbot-web").info(message)
    time.sleep(seconds)


def water_the_rock(payload: dict[str, Any]) -> dict[str, Any]:
    x = payload.get("x", 200)
    y = payload.get("y", 200)
    water_seconds = payload.get("water_seconds", 1)

    _send_chat_message(f"Starting water_the_rock at ({x}, {y})")

    _mock_farmbot_step("Turning on lights")
    _mock_farmbot_step(f"Moving to ({x}, {y}, 0)")
    _mock_farmbot_step(f"Watering for {water_seconds}s")
    _mock_farmbot_step("Returning to home (0,0,0)")

    return {"x": x, "y": y, "water_seconds": water_seconds}


def demo_the_bot(payload: dict[str, Any]) -> dict[str, Any]:
    _send_chat_message("Demo requested")
    _mock_farmbot_step("Performing demo sequence")
    return {"message": "demo sequence complete"}


def exercise_the_farmbot(payload: dict[str, Any]) -> dict[str, Any]:
    loops = int(payload.get("loops", 3))
    _send_chat_message(f"Exercise requested for {loops} loops")
    for loop in range(loops):
        _mock_farmbot_step(f"Exercise loop {loop + 1}/{loops}")
    return {"loops": loops}




def _set_peripheral(pin_number: int, state: int) -> None:
    """Placeholder for Farmbot peripheral control integration.

    Replace this stub with your Farmbot MQTT/API command call.
    """
    state_label = "ON" if state else "OFF"
    _mock_farmbot_step(f"Setting peripheral {pin_number} to {state_label}")


def light_on(payload: dict[str, Any]) -> dict[str, Any]:
    peripheral = int(payload.get("peripheral", 7))
    _send_chat_message(f"Turning on Farmbot light (peripheral {peripheral})")
    _set_peripheral(peripheral, 1)
    return {"peripheral": peripheral, "state": "on"}


def light_off(payload: dict[str, Any]) -> dict[str, Any]:
    peripheral = int(payload.get("peripheral", 7))
    _send_chat_message(f"Turning off Farmbot light (peripheral {peripheral})")
    _set_peripheral(peripheral, 0)
    return {"peripheral": peripheral, "state": "off"}

def yard_irrigation(payload: dict[str, Any]) -> dict[str, Any]:
    minutes = int(payload.get("minutes", 10))
    _send_chat_message(f"Yard irrigation started for {minutes} minutes")
    _mock_farmbot_step("Opening solenoid")
    _mock_farmbot_step("Closing solenoid")
    return {"minutes": minutes}
