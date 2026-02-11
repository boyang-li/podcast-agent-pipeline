from fastapi.testclient import TestClient

from ear.api import create_app


def test_health_endpoint():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_transcribe_endpoint(tmp_path):
    app = create_app()
    client = TestClient(app)
    audio_file = tmp_path / "episode.mp3"
    audio_file.write_text("audio")
    payload = {"episode_id": "ep1", "audio_path": str(audio_file)}
    response = client.post("/transcribe", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["episode_id"] == "ep1"
    assert data["segments"]
