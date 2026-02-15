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

    sent = send_restart_notification()

    assert sent is True
    assert calls["url"] == "https://discord.example/webhook"
    assert "Status: https://example.net/fbot/health" in calls["json"]["content"]


def test_send_restart_notification_no_webhook(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    sent = send_restart_notification()
    assert sent is False


def test_send_restart_notification_disabled(monkeypatch):
    monkeypatch.setenv("DISCORD_RESTART_NOTIFY", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    sent = send_restart_notification()
    assert sent is False
