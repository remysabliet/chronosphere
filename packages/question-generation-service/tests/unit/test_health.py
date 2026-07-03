def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "question-generation"


def test_root_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


def test_openapi_schema_is_available(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
