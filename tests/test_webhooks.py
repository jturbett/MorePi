from farmbot_actions import _send_chat_message


class _Resp:
    def raise_for_status(self):
        return None


def test_discord_payload_sent(monkeypatch):
    calls = {}

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["timeout"] = timeout
        return _Resp()

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setattr("farmbot_actions.requests.post", fake_post)

    _send_chat_message("hello")

    assert calls["url"] == "https://discord.example/webhook"
    assert calls["json"] == {"content": "hello"}


def test_no_discord_webhook_no_request(monkeypatch):
    called = {"value": False}

    def fake_post(url, json, timeout):
        called["value"] = True
        return _Resp()

    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setattr("farmbot_actions.requests.post", fake_post)

    _send_chat_message("hello")

    assert called["value"] is False
