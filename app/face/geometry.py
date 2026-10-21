"""Geometría facial S2.
- Funciones puras (testeables sin MediaPipe): simetría, ratios, clasificación.
- Clasificación: ML (joblib) como primario, reglas como fallback.
- Detección: MediaPipe FaceMesh si está instalado (Render: Python 3.11 sí),
  si no OpenCV Haar como fallback (dev local en Python 3.14 sin wheel de MediaPipe).
Índices MediaPipe FaceMesh (468): ojos 33/133/263/362, nariz 1/168, mentón 152,
frente 10, sienes 234/454, pómulos 93/323.
"""

import logging
import math
import os

logger = logging.getLogger(__name__)

# ── ML classifier (loaded once at module level) ──
_ML_MODEL = None
_ML_FEATURES = ["largo_ancho", "frente_pomulo", "mandibula_frente", "symmetry_index"]


def _load_ml_model():
    """Intenta cargar el modelo ML de forma facial. Retorna pipeline o None."""
    model_path = os.path.join(
        os.path.dirname(__file__), "..", "models", "face_classifier.joblib"
    )
    if not os.path.exists(model_path):
        return None
    try:
        import joblib

        model = joblib.load(model_path)
        logger.info("ML face classifier loaded from %s", model_path)
        return model
    except Exception as e:
        logger.warning("Could not load ML face classifier: %s", e)
        return None


try:
    _ML_MODEL = _load_ml_model()
except Exception:
    _ML_MODEL = None


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def symmetry_index(pairs, width):
    """pairs: lista de ((x1,y1),(x2,y2)) espejados respecto a línea media x_mid.
    Devuelve 0-100."""
    if not pairs or width <= 0:
        return 80.0
    errs = []
    for (x1, y1), (x2, y2), x_mid in pairs:
        d1, d2 = abs(x1 - x_mid), abs(x2 - x_mid)
        errs.append(abs(d1 - d2) / width + abs(y1 - y2) / width * 0.5)
    return round(max(0, 100 - sum(errs) / len(errs) * 220), 1)


def classify_face(largo, ancho, frente, pomulo, mandibula):
    """Clasificación facial morfométrica (7 formas clásicas).

    IMPORTANTE (2026-10-20): los ratios 2D no separan con fiabilidad las 7
    clases en todos los rostros; esta versión reduce los sesgos históricos
    (cuadrado/diamante) y es PROVISIONAL hasta tener etiquetas de óptico.
    El frontend permite corregir la forma manualmente y esa corrección se
    registra en /feedback para recalibrar en la siguiente iteración.

    largo: altura facial (trichion a menton)
    ancho: ancho temporal (sien a sien)
    frente: anchura a nivel de cejas/frente
    pomulo: anchura bizigomática (pómulos)
    mandibula: anchura gonial (mandíbula)
    """
    ratio_la = largo / max(ancho, 1e-6)
    r_frente_pom = frente / max(pomulo, 1e-6)
    r_mand_frente = mandibula / max(frente, 1e-6)
    r_mand_pom = mandibula / max(pomulo, 1e-6)

    # 1. Rostro marcadamente alargado
    if ratio_la > 1.45:
        return "oblongo"

    # 2. Rostros anchos / cortos (largo similar a ancho)
    if ratio_la < 1.18:
        # Mandíbula ancha y angular respecto a pómulos/frente -> cuadrado
        if r_mand_pom > 0.90 or r_mand_frente > 0.95:
            return "cuadrado"
        return "redondo"

    # 3. Base ancha: mandíbula claramente más ancha que la frente
    if r_mand_frente > 1.15:
        return "triangular"

    # 4. Corazón: frente amplia y mandíbula estrecha
    if r_mand_frente < 0.91 and r_frente_pom >= 0.88:
        return "corazon"

    # 5. Diamante: pómulos dominan claramente frente y mandíbula
    if r_frente_pom < 0.80 and r_mand_pom < 0.80:
        return "diamante"

    # 6. Oval: proporciones armónicas y equilibradas
    return "oval"


def classify_face_ml(largo_ancho, frente_pomulo, mandibula_frente, symmetry_index, fallback="oval"):
    """Clasificación facial con modelo ML (scikit-learn).

    Usa el pipeline cargado al iniciar el módulo (_ML_MODEL). Si el modelo no
    está disponible o falla, retorna `fallback` (clasificación por reglas).

    Args:
        largo_ancho: ratio largo / ancho facial
        frente_pomulo: ratio frente / pómulo
        mandibula_frente: ratio mandíbula / frente
        symmetry_index: índice de simetría (0-100)
        fallback: forma a retornar si el modelo ML no está disponible
    """
    if _ML_MODEL is None:
        return fallback
    try:
        import numpy as np

        X = np.array([[largo_ancho, frente_pomulo, mandibula_frente, symmetry_index]])
        prediction = _ML_MODEL.predict(X)[0]
        # Asegurar que la predicción es un string válido
        valid = {"oval", "redondo", "cuadrado", "corazon", "diamante", "oblongo", "triangular"}
        return str(prediction) if str(prediction) in valid else fallback
    except Exception as e:
        logger.warning("ML classify_face failed, using rules fallback: %s", e)
        return fallback


def detect_face_box_bgr(img_bgr):
    """Fallback OpenCV Haar. Retorna (x,y,w,h) o None. No requiere MediaPipe."""
    try:
        import cv2
    except ImportError:
        return None
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    try:
        clf = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = clf.detectMultiScale(gray, 1.15, 4, minSize=(90, 90))
    except Exception:
        return None  # cv2 sin cascadas (ej. build mínimo): sin detección = sin rostro
    if len(faces) == 0:
        return None
    return max(faces, key=lambda b: b[2] * b[3])


def metrics_from_box(box, img_w, img_h):
    """Estimación gruesa desde bounding box (fallback). S2-real usa malla en Render."""
    _x, _y, w, h = [float(v) for v in box]
    shape = classify_face(h, w, w * 0.92, w, w * 0.86)
    return {
        "face_shape": shape,
        "symmetry_index": 82.0,
        "largo_ancho": round(h / max(w, 1e-6), 2),
        "frente_pomulo": 0.92,
        "mandibula_frente": 0.93,
        "temporal_est": 138.0,
        "ipd_mm_est": 63.0,
        "nose_bridge_mm_est": 18.0,
        "eyebrow_in_frame_zone": True,
        "warnings": [
            "modo fallback (sin MediaPipe local): métricas gruesas; en Render se usa malla 478 pts"
        ],
    }


def metrics_from_landmarks(lm, img_w, img_h):
    """Calcula métricas desde landmarks normalizados (0-1) en píxeles.

    Los landmarks de MediaPipe vienen normalizados por eje (x/w, y/h). Si se
    calculan distancias directamente sobre ellos, un rostro en una foto vertical
    parece "cuadrado" y en una horizontal "oblongo": la forma detectada termina
    dependiendo del aspecto de la imagen. Por eso P() devuelve píxeles.
    """

    def P(i):
        p = lm[i]
        if hasattr(p, "x"):
            return (p.x * img_w, p.y * img_h)
        return (p[0] * img_w, p[1] * img_h)

    x_mid = P(168)[0]
    W = _dist(P(234), P(454)) or 1e-6  # ancho temporal en px
    pairs = [
        (P(33), P(263), x_mid),
        (P(133), P(362), x_mid),
        (P(93), P(323), x_mid),
        (P(61), P(291), x_mid),
    ]
    sym = symmetry_index([(a, b, m) for a, b, m in pairs], W)
    largo = _dist(P(10), P(152))
    frente = _dist(P(103), P(332)) if len(lm) > 334 else W * 0.90
    pom = _dist(P(123), P(352)) if len(lm) > 352 else W
    man = _dist(P(172), P(397)) if len(lm) > 397 else pom * 0.85
    shape = classify_face(largo, W, frente, pom, man)

    # Intentar ML si el modelo está disponible (override reglas)
    shape = classify_face_ml(
        largo / max(W, 1e-6),
        frente / max(pom, 1e-6),
        man / max(frente, 1e-6),
        sym,
        fallback=shape,
    )

    # Medición de IPD
    if len(lm) > 473:
        ipd_px = _dist(P(468), P(473))
    else:
        ipd_px = _dist(P(33), P(263)) * 0.5

    px2mm = 63.0 / ipd_px if ipd_px > 15 else (142.0 / max(W, 1.0))

    temporal_est = round(max(122.0, min(156.0, W * px2mm)), 1)
    ipd_mm_est = round(max(58.0, min(72.0, 63.0 * (temporal_est / 138.0))), 1)

    # Puente nasal (cantos internos 133 a 362)
    canthi_px = _dist(P(133), P(362))
    bridge_mm = round(max(15.0, min(22.0, canthi_px * px2mm * 0.52)), 1)

    # Cejas vs Ojos
    y_brow = (P(105)[1] + P(334)[1]) / 2.0
    y_eye = (P(468)[1] + P(473)[1]) / 2.0 if len(lm) > 473 else P(168)[1]
    brow_clearance_mm = max(0.0, (y_eye - y_brow) * px2mm)
    eyebrow_in_zone = 8.0 <= brow_clearance_mm <= 26.0

    return {
        "face_shape": shape,
        "symmetry_index": sym,
        "largo_ancho": round(largo / max(W, 1e-6), 2),
        "frente_pomulo": round(frente / max(pom, 1e-6), 2),
        "mandibula_frente": round(man / max(frente, 1e-6), 2),
        "temporal_est": temporal_est,
        "ipd_mm_est": ipd_mm_est,
        "nose_bridge_mm_est": bridge_mm,
        "eyebrow_in_frame_zone": eyebrow_in_zone,
        "warnings": [],
    }


def try_mediapipe_landmarks(img_bgr):
    """Retorna dict de métricas o None si no hay MediaPipe/rostro."""
    try:
        import mediapipe as mp
    except ImportError:
        return None
    # Conversión BGR->RGB sin cv2 (numpy puro) para no depender de sysdeps.
    # img_bgr viene de PIL (RGB->BGR manual) o de cv2.imdecode; en ambos casos es ndarray HxWx3.
    try:
        import numpy as np

        rgb = img_bgr[:, :, ::-1]
        if not rgb.flags["C_CONTIGUOUS"]:
            rgb = np.ascontiguousarray(rgb)
    except Exception:
        return None
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as fm:
        res = fm.process(rgb)
    if not res.multi_face_landmarks:
        return None
    lm = res.multi_face_landmarks[0].landmark
    h, w = img_bgr.shape[:2]

    return metrics_from_landmarks(lm, w, h)
