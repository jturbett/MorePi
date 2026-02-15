import sys
import types


class _DummyFarmbot:
    pass


sys.modules.setdefault("farmbot", types.SimpleNamespace(Farmbot=_DummyFarmbot))

from app import create_app



class _Resp:
    def raise_for_status(self):
        return None


def test_unifi_motion_triggers_demo_url(monkeypatch):
    called = {}

    def fake_get(url, timeout):
        called["url"] = url
        called["timeout"] = timeout
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_MOTION_COOLDOWN_SECONDS", "1200")
    monkeypatch.setenv(
        "UNIFI_MOTION_TRIGGER_URL",
        "http://192.168.1.55:7777/trigger/demo_move_home?x=600&y=400&z=0",
    )
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert called["url"].endswith("demo_move_home?x=600&y=400&z=0")


def test_unifi_motion_respects_cooldown(monkeypatch):
    call_count = {"value": 0}

    def fake_get(url, timeout):
        call_count["value"] += 1
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_MOTION_COOLDOWN_SECONDS", "1200")
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    first = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
    )
    second = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
    )

    assert first.status_code == 200
    assert second.status_code == 202
    assert second.get_json()["reason"] == "cooldown"
    assert call_count["value"] == 1


def test_unifi_motion_ignores_other_camera(monkeypatch):
    called = {"value": False}

    def fake_get(url, timeout):
        called["value"] = True
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "Front Door", "motion": True},
    )

    assert response.status_code == 202
    assert response.get_json()["reason"] == "camera_mismatch"
    assert called["value"] is False


def test_unifi_motion_failed_trigger_does_not_start_cooldown(monkeypatch):
    class _BoomResp:
        def raise_for_status(self):
            raise Exception("boom")

    calls = {"value": 0}

    def fake_get(url, timeout):
        calls["value"] += 1
        return _BoomResp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    first = client.post("/webhooks/unifi-protect-motion", json={"camera_name": "G4 Pro", "motion": True})
    second = client.post("/webhooks/unifi-protect-motion", json={"camera_name": "G4 Pro", "motion": True})

    assert first.status_code == 500 or first.status_code == 502
    assert second.status_code == 500 or second.status_code == 502
    assert calls["value"] == 2


def test_unifi_motion_uses_post_when_configured(monkeypatch):
    called = {"method": None}

    def fake_post(url, timeout):
        called["method"] = "POST"
        return _Resp()

    def fake_get(url, timeout):
        called["method"] = "GET"
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_MOTION_TRIGGER_METHOD", "POST")
    monkeypatch.setattr("app.requests.post", fake_post)
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    response = client.post("/webhooks/unifi-protect-motion", json={"camera_name": "G4 Pro", "motion": True})

    assert response.status_code == 200
    assert called["method"] == "POST"


def test_unifi_motion_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_PROTECT_API_KEY", "super-secret")

    app = create_app()
    client = app.test_client()

    response = client.post("/webhooks/unifi-protect-motion", json={"camera_name": "G4 Pro", "motion": True})

    assert response.status_code == 401


def test_unifi_motion_accepts_x_api_key_header(monkeypatch):
    called = {"value": 0}

    def fake_get(url, timeout):
        called["value"] += 1
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_PROTECT_API_KEY", "super-secret")
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
        headers={"X-API-Key": "super-secret"},
    )

    assert response.status_code == 200
    assert called["value"] == 1


def test_unifi_motion_accepts_repo_local_unifi_key_file(monkeypatch, tmp_path):
    called = {"value": 0}

    def fake_get(url, timeout):
        called["value"] += 1
        return _Resp()

    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    (secrets_dir / "unifi_key").write_text("local-secret\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.delenv("UNIFI_PROTECT_API_KEY", raising=False)
    monkeypatch.delenv("UNIFI_PROTECT_API_KEY_FILE", raising=False)
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    unauthorized = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
    )
    authorized = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
        headers={"X-API-Key": "local-secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert called["value"] == 1


def test_unifi_motion_rejects_unexpected_source_host(monkeypatch):
    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_PROTECT_HOST", "192.168.1.59")

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
        environ_base={"REMOTE_ADDR": "192.168.1.42"},
    )

    assert response.status_code == 403


def test_unifi_motion_accepts_expected_forwarded_host(monkeypatch):
    called = {"value": 0}

    def fake_get(url, timeout):
        called["value"] += 1
        return _Resp()

    monkeypatch.setenv("UNIFI_MOTION_CAMERA_NAME", "G4 Pro")
    monkeypatch.setenv("UNIFI_PROTECT_HOST", "192.168.1.59")
    monkeypatch.setattr("app.requests.get", fake_get)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/webhooks/unifi-protect-motion",
        json={"camera_name": "G4 Pro", "motion": True},
        environ_base={"REMOTE_ADDR": "172.20.0.4"},
        headers={"X-Forwarded-For": "192.168.1.59"},
    )

    assert response.status_code == 200
    assert called["value"] == 1
