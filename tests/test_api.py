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

def test_crud_frames():
    H = {"X-Admin-Key": "cambia-esta-clave"}
    f = {"id": "FT99", "nombre": "Test", "forma": "oval", "A_mm": 50, "B_mm": 34, "D_mm": 18, "ancho_total_mm": 139}
    assert c.post("/frames", json=f).status_code == 401  # sin key
    assert c.post("/frames", json=f, headers=H).status_code == 201
    assert c.post("/frames", json=f, headers=H).status_code == 409
    f["nombre"] = "Test 2"
    assert c.put("/frames/FT99", json=f, headers=H).status_code == 200
    assert c.delete("/frames/FT99", headers=H).status_code == 200
    assert c.delete("/frames/FT99", headers=H).status_code == 404

def test_feedback_stats():
    assert c.post("/feedback", json={"face_shape": "oval", "frame_id": "F01", "verdict": "compatible", "helpful": 5}).status_code == 201
    s = c.get("/feedback/stats").json()
    assert s["n"] >= 1 and s["avg_helpful"] >= 1
