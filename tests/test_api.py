from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)

def test_health():
    assert c.get("/health").status_code == 200

def test_frames_seed():
    r = c.get("/frames")
    assert r.status_code == 200 and len(r.json()) == 12

def test_recommend_scores_range():
    r = c.post("/recommend", json={"metrics": {"face_detected": True}, "frame_ids": ["F01"]})
    assert r.status_code == 200
    assert 0 <= r.json()[0]["score"] <= 100
