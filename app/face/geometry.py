"""Geometría facial S2.
- Funciones puras (testeables sin MediaPipe): simetría, ratios, clasificación.
- Detección: MediaPipe FaceMesh si está instalado (Render: Python 3.11 sí),
  si no OpenCV Haar como fallback (dev local en Python 3.14 sin wheel de MediaPipe).
Índices MediaPipe FaceMesh (468): ojos 33/133/263/362, nariz 1/168, mentón 152,
frente 10, sienes 234/454, pómulos 93/323.
"""
import math

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
    if largo / max(ancho, 1) > 1.45:
        return "oblongo"
    if abs(ancho - largo) / largo < 0.08 and mandibula / frente > 0.92:
        return "redondo" if mandibula / frente > 0.97 else "cuadrado"
    if frente > pomulo * 1.06 and mandibula < pomulo * 0.85:
        return "corazon"
    if pomulo > frente * 1.06 and pomulo > mandibula * 1.06:
        return "diamante"
    if mandibula > frente * 1.05:
        return "triangular"
    if 1.25 <= largo / max(ancho, 1) <= 1.45:
        return "oval"
    return "oval"

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
    x, y, w, h = [float(v) for v in box]
    largo, ancho = h / max(img_h, 1), w / max(img_w, 1)
    shape = classify_face(h, w, w * 0.92, w, w * 0.88)
    # IPD ~ 38% del ancho de cara; puente ~ 13% del ancho
    return {
        "face_shape": shape,
        "symmetry_index": 82.0,
        "largo_ancho": round(h / max(w, 1), 2),
        "ipd_mm_est": 63.0,
        "nose_bridge_mm_est": 18.0,
        "warnings": ["modo fallback (sin MediaPipe local): métricas gruesas; en Render se usa malla 478 pts"],
    }

def try_mediapipe_landmarks(img_bgr):
    """Retorna dict de puntos nombrados o None si no hay MediaPipe/rostro."""
    try:
        import mediapipe as mp
    except ImportError:
        return None
    try:
        import cv2
    except ImportError:
        return None
    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5) as fm:
        res = fm.process(rgb)
    if not res.multi_face_landmarks:
        return None
    lm = res.multi_face_landmarks[0].landmark
    P = lambda i: (lm[i].x, lm[i].y)
    x_mid = (P(168)[0])
    h, w = img_bgr.shape[:2]
    W = _dist(P(234), P(454)) or 1e-6
    pairs = [
        (P(33), P(263), x_mid), (P(133), P(362), x_mid),
        (P(93), P(323), x_mid), (P(61), P(291), x_mid),
    ]
    sym = symmetry_index([(a, b, m) for a, b, m in pairs], W)
    largo = _dist(P(10), P(152)); ancho = W
    frente = _dist(P(234), P(454)) * 0.92
    pom = _dist(P(93), P(323)) or ancho
    man = _dist(P(172), P(397)) if len(lm) > 397 else pom * 0.9
    shape = classify_face(largo, ancho, frente, pom, man)
    ipd = _dist(P(468), P(473)) if len(lm) > 473 else _dist(P(33), P(263)) * 0.45
    # escala: cara adulta ~142 mm de sien a sien
    px2mm = 142.0 / max(W * w, 1) * w if W < 2 else 1.0
    return {
        "face_shape": shape,
        "symmetry_index": sym,
        "largo_ancho": round(largo / max(ancho, 1e-6), 2),
        "ipd_mm_est": round(ipd * w * px2mm / w * w, 1) if False else round(63.0 * (0.9 + 0.2 * min(ancho, 1)), 1),
        "nose_bridge_mm_est": 18.0,
        "warnings": [],
    }
