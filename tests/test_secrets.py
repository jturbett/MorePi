from pathlib import Path

from secret_loader import get_secret


def test_get_secret_reads_file_first(tmp_path, monkeypatch):
    secret_file = tmp_path / "discord.txt"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "env-secret")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL_FILE", str(secret_file))

    assert get_secret("DISCORD_WEBHOOK_URL") == "file-secret"


def test_get_secret_falls_back_to_env(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL_FILE", raising=False)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "env-secret")

    assert get_secret("DISCORD_WEBHOOK_URL") == "env-secret"
