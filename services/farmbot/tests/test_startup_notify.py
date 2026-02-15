from startup_notify import send_restart_notification


class _Resp:
    def raise_for_status(self):
        return None


def test_send_restart_notification_posts_to_discord(monkeypatch):
    calls = {}

    def fake_post(url, json, timeout):
        calls["url"] = url
        calls["json"] = json
        calls["timeout"] = timeout
        return _Resp()

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setenv("STATUS_URL", "https://example.net/fbot/health")
    monkeypatch.setattr("startup_notify.requests.post", fake_post)

    result = send_restart_notification()

    assert result.sent is True
    assert calls["url"] == "https://discord.example/webhook"
    assert "Status: https://example.net/fbot/health" in calls["json"]["content"]


def test_send_restart_notification_no_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    result = send_restart_notification()
    assert result.sent is False
    assert result.reason == "missing_webhook"


def test_send_restart_notification_disabled(monkeypatch):
    monkeypatch.setenv("DISCORD_RESTART_NOTIFY", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    result = send_restart_notification()
    assert result.sent is False
    assert result.reason == "disabled"


def test_send_restart_notification_retries(monkeypatch):
    calls = {"count": 0}

    class Boom(Exception):
        pass

    def fake_post(url, json, timeout):
        calls["count"] += 1
        if calls["count"] < 3:
            raise Boom("temporary error")
        return _Resp()

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setenv("DISCORD_RESTART_RETRIES", "3")
    monkeypatch.setattr("startup_notify.requests.post", fake_post)
    monkeypatch.setattr("startup_notify.time.sleep", lambda *_: None)

    result = send_restart_notification()

    assert result.sent is True
    assert result.reason == "sent_attempt_3"
    assert calls["count"] == 3
