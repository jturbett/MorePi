from app import create_app


def test_health_endpoint():
    app = create_app()
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_actions_endpoint_includes_expected_action():
    app = create_app()
    client = app.test_client()

    response = client.get("/actions")

    assert response.status_code == 200
    assert "water_the_rock" in response.get_json()["actions"]


def test_unknown_action_returns_404():
    app = create_app()
    client = app.test_client()

    response = client.post("/trigger/not-real", json={})

    assert response.status_code == 404
