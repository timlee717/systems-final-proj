from src.app import app


def test_health_ok():
    client = app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_valid_submission_created():
    client = app.test_client()
    resp = client.post(
        "/v1/survey",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "age": 21,
            "consent": True,
            "rating": 5,
            "comments": "Nice product!",
            "source": "web",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "request_id" in data


def test_rejects_non_json():
    client = app.test_client()
    resp = client.post("/v1/survey", data="not-json", headers={"Content-Type": "text/plain"})
    assert resp.status_code == 400
