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

def test_geometry_pure():
    from app.face.geometry import symmetry_index, classify_face
    s = symmetry_index([((0.3, 0.5), (0.7, 0.5), 0.5)], 0.4)
    assert 90 <= s <= 100
    assert classify_face(170, 130, 125, 128, 110) == "oval"
    assert classify_face(150, 145, 140, 142, 140) in ("redondo", "cuadrado")

def test_analyze_rejects_bad_type():
    r = c.post("/analyze", files={"photo": ("x.txt", b"hola", "text/plain")})
    assert r.status_code == 400

def test_analyze_no_face_blank():
    import numpy as np
    blank = np.full((200, 200, 3), 255, np.uint8)
    import cv2
    _, buf = cv2.imencode(".jpg", blank)
    r = c.post("/analyze", files={"photo": ("blank.jpg", buf.tobytes(), "image/jpeg")})
    assert r.status_code == 200
    assert r.json()["face_detected"] is False

def test_delete_photo():
    r = c.delete("/analyze/photo")
    assert r.status_code == 200 and r.json()["ok"] is True
