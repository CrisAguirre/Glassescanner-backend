"""Rutas de fallo: Mongo caído, MediaPipe caído, imágenes inválidas.

Todo se aísla con dobles de prueba para que los tests no dependan de una base
de datos ni de los modelos reales (que no están en CI).
"""

import os

os.environ["ENVIRONMENT"] = "test"
os.environ["ADMIN_KEY"] = "test-admin-key-123456"
os.environ["MONGODB_URI"] = ""
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ.pop("RENDER", None)

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.routers import analyze as analyze_mod
from app.routers import feedback as feedback_mod
from app.routers import frames as frames_mod

c = TestClient(app)
ADMIN = {"X-Admin-Key": os.environ["ADMIN_KEY"]}

FRAME_DICT = {
    "id": "FDB1",
    "nombre": "Mongo",
    "forma": "oval",
    "A_mm": 52,
    "B_mm": 36,
    "D_mm": 18,
    "ancho_total_mm": 142,
}

METRICS = {
    "face_shape": "oval",
    "symmetry_index": 91.5,
    "largo_ancho": 1.32,
    "frente_pomulo": 0.96,
    "mandibula_frente": 0.88,
    "ipd_mm_est": 64.0,
    "nose_bridge_mm_est": 18.5,
    "temporal_est": 141.0,
    "eyebrow_in_frame_zone": True,
    "warnings": [],
}


def jpg_bytes(width: int = 120, height: int = 120) -> bytes:
    img = np.full((height, width, 3), 200, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def post_photo(data: bytes, name: str = "foto.jpg"):
    return c.post("/analyze", files={"photo": (name, data, "image/jpeg")})


class FakeCollection:
    """Colección mínima: find/to_list e inserciones, con interruptor de fallo."""

    def __init__(self):
        self.docs: list[dict] = []
        self.fail = False

    def _raise(self):
        raise RuntimeError("Mongo caído (test)")

    def find(self, *_args, **_kwargs):
        return self

    def to_list(self, _limit):
        async def _run():
            if self.fail:
                self._raise()
            return list(self.docs)

        return _run()

    async def insert_one(self, doc):
        if self.fail:
            self._raise()
        self.docs.append(doc)

    async def replace_one(self, *_args, **_kwargs):
        if self.fail:
            self._raise()

    async def delete_one(self, query):
        if self.fail:
            self._raise()
        self.docs = [
            d for d in self.docs if not all(d.get(k) == v for k, v in query.items())
        ]

    async def delete_many(self, *_args, **_kwargs):
        if self.fail:
            self._raise()

    async def insert_many(self, docs):
        if self.fail:
            self._raise()
        self.docs.extend(docs)


class FakeDB:
    def __init__(self):
        self.coll = FakeCollection()

    def __getitem__(self, _name):
        return self.coll


# --- /analyze -------------------------------------------------------------


def test_analyze_rechaza_demasiados_pixeles(monkeypatch):
    monkeypatch.setattr(analyze_mod, "MAX_IMAGE_PIXELS", 100)
    r = post_photo(jpg_bytes())
    assert r.status_code == 413


def test_analyze_rechaza_imagen_vacia():
    r = post_photo(b"")
    assert r.status_code == 400
    assert "vacía" in r.json()["detail"]


def test_analyze_bomba_de_descompresion(monkeypatch):
    def _bomb(*_args, **_kwargs):
        raise analyze_mod.Image.DecompressionBombError("bomba (test)")

    monkeypatch.setattr(analyze_mod.Image, "open", _bomb)
    r = post_photo(jpg_bytes())
    assert r.status_code == 413


def test_analyze_rechaza_imagen_indecodificable():
    r = post_photo(b"esto no es una imagen")
    assert r.status_code == 400
    assert "decodificar" in r.json()["detail"]


def test_analyze_usa_mediapipe(monkeypatch):
    monkeypatch.setattr(analyze_mod, "try_mediapipe_landmarks", lambda _img: dict(METRICS))
    r = post_photo(jpg_bytes())
    assert r.status_code == 200
    body = r.json()
    assert body["face_detected"] is True
    assert body["face_shape"] == "oval"
    assert body["ipd_mm_est"] == 64.0


def test_analyze_mediapipe_caido_usa_haar(monkeypatch):
    def _boom(_img):
        raise RuntimeError("MediaPipe caído (test)")

    monkeypatch.setattr(analyze_mod, "try_mediapipe_landmarks", _boom)
    monkeypatch.setattr(analyze_mod, "detect_face_box_bgr", lambda _img: (10, 10, 90, 90))
    monkeypatch.setattr(analyze_mod, "metrics_from_box", lambda _box, _w, _h: dict(METRICS))
    r = post_photo(jpg_bytes())
    assert r.status_code == 200
    assert r.json()["face_detected"] is True


def test_analyze_sin_rostro(monkeypatch):
    monkeypatch.setattr(analyze_mod, "try_mediapipe_landmarks", lambda _img: None)
    monkeypatch.setattr(analyze_mod, "detect_face_box_bgr", lambda _img: None)
    r = post_photo(jpg_bytes())
    assert r.status_code == 200
    body = r.json()
    assert body["face_detected"] is False
    assert body["warnings"]


def test_analyze_pil_caido_usa_cv2(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise ValueError("PIL caído (test)")

    monkeypatch.setattr(analyze_mod.Image, "open", _boom)
    monkeypatch.setattr(analyze_mod, "try_mediapipe_landmarks", lambda _img: None)
    monkeypatch.setattr(analyze_mod, "detect_face_box_bgr", lambda _img: None)
    r = post_photo(jpg_bytes())
    assert r.status_code == 200
    assert r.json()["face_detected"] is False


def test_analyze_pil_y_cv2_caidos(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise ValueError("decodificador caído (test)")

    monkeypatch.setattr(analyze_mod.Image, "open", _boom)
    monkeypatch.setattr(cv2, "imdecode", _boom)
    r = post_photo(jpg_bytes())
    assert r.status_code == 400


# --- catálogo -------------------------------------------------------------


def test_catalog_seed_inexistente(tmp_path, monkeypatch):
    from app.expert import catalog

    monkeypatch.setattr(catalog, "_SEED_PATH", tmp_path / "no-existe.json")
    assert catalog._load_frames() == []


def test_catalog_seed_corrupto(tmp_path, monkeypatch):
    from app.expert import catalog

    p = tmp_path / "roto.json"
    p.write_text("{esto no es json", encoding="utf-8")
    monkeypatch.setattr(catalog, "_SEED_PATH", p)
    assert catalog._load_frames() == []


# --- /frames --------------------------------------------------------------


def test_list_frames_lee_mongo(monkeypatch):
    db = FakeDB()
    db.coll.docs = [dict(FRAME_DICT)]
    monkeypatch.setattr(frames_mod, "get_db", lambda: db)
    r = c.get("/frames")
    assert r.status_code == 200
    assert [f["id"] for f in r.json()] == ["FDB1"]


def test_list_frames_mongo_caido_usa_seed(monkeypatch):
    db = FakeDB()
    db.coll.fail = True
    monkeypatch.setattr(frames_mod, "get_db", lambda: db)
    r = c.get("/frames")
    assert r.status_code == 200
    assert len(r.json()) >= 64


def test_crud_frames_escribe_mongo(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(frames_mod, "get_db", lambda: db)
    frame = dict(FRAME_DICT, id="FDB2")

    assert c.post("/frames", json=frame, headers=ADMIN).status_code == 201
    assert any(d["id"] == "FDB2" for d in db.coll.docs)

    frame["nombre"] = "Mongo editado"
    assert c.put("/frames/FDB2", json=frame, headers=ADMIN).status_code == 200
    assert c.delete("/frames/FDB2", headers=ADMIN).status_code == 200
    assert all(d["id"] != "FDB2" for d in db.coll.docs)


def test_crud_frames_mongo_caido_no_rompe(monkeypatch):
    db = FakeDB()
    db.coll.fail = True
    monkeypatch.setattr(frames_mod, "get_db", lambda: db)
    frame = dict(FRAME_DICT, id="FDB3")

    assert c.post("/frames", json=frame, headers=ADMIN).status_code == 201
    frame["nombre"] = "Solo memoria"
    assert c.put("/frames/FDB3", json=frame, headers=ADMIN).status_code == 200
    assert c.delete("/frames/FDB3", headers=ADMIN).status_code == 200


def test_seed_sin_mongo(monkeypatch):
    monkeypatch.setattr(frames_mod, "get_db", lambda: None)
    r = c.post("/frames/seed", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["ok"] is False


def test_seed_con_mongo(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(frames_mod, "get_db", lambda: db)
    r = c.post("/frames/seed", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["n"] >= 64
    assert len(db.coll.docs) == body["n"]


# --- /feedback ------------------------------------------------------------


def test_feedback_escribe_mongo(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(feedback_mod, "get_db", lambda: db)
    feedback_mod.MEM.clear()

    r = c.post("/feedback", json={"helpful": 3, "verdict": "parcial"})
    assert r.status_code == 201
    assert db.coll.docs[-1]["helpful"] == 3

    stats = c.get("/feedback/stats").json()
    assert stats["n"] == 1
    assert stats["avg_helpful"] == 3.0
    assert stats["parcial_rate"] == 1.0


def test_feedback_mongo_caido_usa_memoria(monkeypatch):
    db = FakeDB()
    db.coll.fail = True
    monkeypatch.setattr(feedback_mod, "get_db", lambda: db)
    feedback_mod.MEM.clear()

    assert c.post("/feedback", json={"helpful": 5}).status_code == 201
    stats = c.get("/feedback/stats").json()
    assert stats["n"] == 1
    assert stats["avg_helpful"] == 5.0


def test_feedback_sin_datos(monkeypatch):
    monkeypatch.setattr(feedback_mod, "get_db", lambda: None)
    feedback_mod.MEM.clear()
    stats = c.get("/feedback/stats").json()
    assert stats["n"] == 0
    assert stats["avg_helpful"] is None
    assert stats["fit_rate"] is None
    assert stats["shape_accuracy"] is None
    assert "Sin datos" in stats["sugerencia"]


def test_feedback_sugerencias(monkeypatch):
    monkeypatch.setattr(feedback_mod, "get_db", lambda: None)
    feedback_mod.MEM[:] = [
        {
            "face_shape": "oval",
            "face_shape_detected": "oval",
            "verdict": "parcial",
            "helpful": 2,
            "va_bien": "no",
        }
    ]
    stats = c.get("/feedback/stats").json()
    assert stats["avg_helpful"] == 2.0
    assert "faltan" in stats["sugerencia"]
    assert "revisar el lenguaje" in stats["sugerencia"]
    feedback_mod.MEM.clear()
