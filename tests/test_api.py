from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)


def test_health():
    assert c.get("/health").status_code == 200


def test_frames_seed():
    r = c.get("/frames")
    assert r.status_code == 200
    frames = r.json()
    assert len(frames) >= 64
    f0 = frames[0]
    assert "genero" in f0 and "precio_rango" in f0 and "marca" in f0
    assert "tipo_lente" in f0 and "estilo" in f0 and "talla" in f0


def test_recommend_scores_range():
    r = c.post(
        "/recommend",
        json={
            "metrics": {"face_detected": True, "temporal_est": 140.0},
            "frame_ids": ["F01"],
        },
    )
    assert r.status_code == 200
    res = r.json()
    assert len(res) == 1
    assert 0 <= res[0]["score"] <= 100
    assert res[0]["verdict"] in ("compatible", "parcial", "incompatible")


def test_geometry_pure():
    from app.face.geometry import symmetry_index, classify_face

    s = symmetry_index([((0.3, 0.5), (0.7, 0.5), 0.5)], 0.4)
    assert 90 <= s <= 100
    assert classify_face(190, 125, 120, 125, 115) == "oblongo"
    assert classify_face(140, 135, 130, 135, 110) == "redondo"
    assert classify_face(142, 138, 134, 138, 130) == "cuadrado"
    assert classify_face(170, 130, 100, 128, 120) == "triangular"
    assert classify_face(165, 130, 135, 128, 98) == "corazon"
    assert classify_face(170, 140, 105, 140, 105) == "diamante"
    assert classify_face(175, 132, 112, 132, 118) == "oval"


def test_metrics_aspect_invariant():
    """El mismo rostro en píxeles debe dar las mismas métricas aunque cambie
    el aspecto de la imagen (regresión del sesgo cuadrado/oblongo)."""
    from app.face.geometry import metrics_from_landmarks

    pixels = {
        168: (100, 120),
        234: (50, 120),
        454: (150, 120),
        33: (70, 100),
        263: (130, 100),
        133: (85, 105),
        362: (115, 105),
        93: (60, 120),
        323: (140, 120),
        61: (80, 160),
        291: (120, 160),
        10: (100, 45),
        152: (100, 225),
        103: (70, 70),
        332: (130, 70),
        123: (55, 120),
        352: (145, 120),
        172: (65, 170),
        397: (135, 170),
        468: (85, 100),
        473: (115, 100),
        105: (70, 65),
        334: (130, 65),
    }
    base = [(0.5, 0.5)] * 478
    for i, (x, y) in pixels.items():
        base[i] = (x, y)

    lm_a = [(x / 200, y / 300) for x, y in base]
    lm_b = [(x / 400, y / 300) for x, y in base]  # mismo rostro, otro aspecto
    a = metrics_from_landmarks(lm_a, 200, 300)
    b = metrics_from_landmarks(lm_b, 400, 300)
    assert a == b
    # With ML classifier the shape may differ from the old rules-based "oblongo";
    # the critical invariant is that both aspect ratios yield the SAME shape.
    assert a["face_shape"] == b["face_shape"]
    assert a["face_shape"] in ("oval", "redondo", "cuadrado", "corazon", "diamante", "oblongo", "triangular")


def test_recommend_sorted():
    r = c.post(
        "/recommend",
        json={
            "metrics": {"face_detected": True, "temporal_est": 140.0},
            "frame_ids": ["F01", "F02", "F03", "F04", "F05"],
        },
    )
    assert r.status_code == 200
    scores = [x["score"] for x in r.json()]
    assert scores == sorted(scores, reverse=True)


def test_scoring_rules():
    from app.expert.rules import score_frame
    from app.schemas import FaceMetrics, Frame

    m = FaceMetrics(
        face_shape="cuadrado",
        temporal_est=140,
        ipd_mm_est=64,
        nose_bridge_mm_est=18,
        eyebrow_in_frame_zone=True,
    )
    base = dict(
        nombre="Test",
        B_mm=35,
        D_mm=18,
        ancho_total_mm=140,
        A_mm=50,
    )
    perfect = Frame(id="TP1", forma="redondo", **base)
    avoid = Frame(id="TP2", forma="cuadrado", **base)
    bad = Frame(
        id="TP3",
        forma="redondo",
        nombre="Test",
        A_mm=60,
        B_mm=35,
        D_mm=24,
        ancho_total_mm=170,
    )
    assert score_frame(m, perfect).verdict == "compatible"
    assert score_frame(m, avoid).verdict == "parcial"
    assert score_frame(m, bad).verdict == "incompatible"
    assert len(score_frame(m, perfect).reasons) == 3


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
    f = {
        "id": "FT99",
        "nombre": "Test",
        "forma": "oval",
        "A_mm": 50,
        "B_mm": 34,
        "D_mm": 18,
        "ancho_total_mm": 139,
    }
    assert c.post("/frames", json=f).status_code == 401  # sin key
    assert c.post("/frames", json=f, headers=H).status_code == 201
    assert c.post("/frames", json=f, headers=H).status_code == 409
    f["nombre"] = "Test 2"
    assert c.put("/frames/FT99", json=f, headers=H).status_code == 200
    assert c.delete("/frames/FT99", headers=H).status_code == 200
    assert c.delete("/frames/FT99", headers=H).status_code == 404


def test_feedback_stats():
    assert (
        c.post(
            "/feedback",
            json={
                "face_shape": "oval",
                "face_shape_detected": "cuadrado",
                "frame_id": "F01",
                "recommended_frame_id": "F01",
                "verdict": "compatible",
                "helpful": 5,
                "marco_lleva": "F04",
                "va_bien": "si",
            },
        ).status_code
        == 201
    )
    s = c.get("/feedback/stats").json()
    assert s["n"] >= 1 and s["avg_helpful"] >= 1
    assert s["fit_rate"] == 1.0
    assert s["shape_accuracy"] == 0.0
    assert s["fit_n"] >= 1 and s["shape_n"] >= 1
    assert "fit_n=" in s["sugerencia"] and "shape_n=" in s["sugerencia"]
    assert s["helpful_dist"]["5"] >= 1
    assert s["by_face_shape"]["oval"]["n"] >= 1
