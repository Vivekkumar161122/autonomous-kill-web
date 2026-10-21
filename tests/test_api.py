import pytest
from starlette.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "tracks" in data
    assert "assets" in data
    assert "scenario" in data

def test_api_model_info_endpoint(client):
    response = client.get("/api/model_info")
    assert response.status_code == 200
    data = response.json()
    assert "roc_auc" in data
    assert "feature_importances" in data

def test_scenario_switch_endpoint(client):
    payload = {"scenario": "multi_axis_swarm"}
    response = client.post("/api/scenario", json=payload)
    assert response.status_code == 200
    assert response.json()["current_scenario"] == "multi_axis_swarm"

def test_mode_toggle_endpoint(client):
    payload = {"autonomous": False}
    response = client.post("/api/mode", json=payload)
    assert response.status_code == 200
    assert response.json()["autonomous_mode"] is False
