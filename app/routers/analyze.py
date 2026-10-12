from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
from ..config import settings
from ..schemas import FaceMetrics, Ratios
from ..face.geometry import (
    detect_face_box_bgr, metrics_from_box, try_mediapipe_landmarks,
)

router = APIRouter()

@router.post("/analyze", response_model=FaceMetrics)
async def analyze(photo: UploadFile = File(...)):
    data = await photo.read()
    ctype = (photo.content_type or "").lower()
    valid_types = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/pjpeg", "application/octet-stream"}
    fname = (photo.filename or "").lower()
    if ctype not in valid_types and not any(fname.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        raise HTTPException(400, "Formato válido: JPG/PNG/WebP")
    cv2_ver, pil_ver, cv2_err, pil_err, step = "missing", "missing", "", "", ""
    img = None
    # 1) PIL primero (puro Python+numpy, no depende de cv2 ni de libs del sistema)
    try:
        from PIL import Image
        import io
        pil_ver = getattr(Image, "__version__", "?")
        pil_img = Image.open(io.BytesIO(data)).convert("RGB")
        img = np.array(pil_img)[:, :, ::-1].copy()  # RGB->BGR sin cv2
        step = "pil ok"
    except Exception as e:
        pil_err = f"{type(e).__name__}: {e}"[:160]
        step = "pil fail"
    # 2) cv2.imdecode como respaldo
    if img is None:
        try:
            import cv2
            cv2_ver = getattr(cv2, "__version__", "?")
            buf = np.frombuffer(data, dtype=np.uint8).copy()
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            step += "+cv2 tried"
        except Exception as e:
            cv2_err = f"{type(e).__name__}: {e}"[:200]
            step += "+cv2 fail"
    if img is None:
        raise HTTPException(400, "No se pudo decodificar la imagen")
    h, w = img.shape[:2]

    # 1. MediaPipe real (Render Python 3.11 sí lo tiene)
    m = try_mediapipe_landmarks(img)
    if m:
        return FaceMetrics(
            face_detected=True,
            face_shape=m["face_shape"],
            symmetry_index=m["symmetry_index"],
            ratios=Ratios(
                largo_ancho=m["largo_ancho"],
                frente_pomulo=m["frente_pomulo"],
                mandibula_frente=m["mandibula_frente"],
            ),
            ipd_mm_est=m["ipd_mm_est"],
            nose_bridge_mm_est=m["nose_bridge_mm_est"],
            temporal_est=m["temporal_est"],
            eyebrow_in_frame_zone=m["eyebrow_in_frame_zone"],
            warnings=m["warnings"],
        )
    # 2. Fallback OpenCV (dev local sin MediaPipe)
    box = detect_face_box_bgr(img)
    if box is None:
        return FaceMetrics(face_detected=False, warnings=["No se detectó rostro frontal. Acércate a la luz y mira de frente."])
    g = metrics_from_box(box, w, h)
    return FaceMetrics(
        face_detected=True,
        face_shape=g["face_shape"],
        symmetry_index=g["symmetry_index"],
        ratios=Ratios(
            largo_ancho=g["largo_ancho"],
            frente_pomulo=g["frente_pomulo"],
            mandibula_frente=g["mandibula_frente"],
        ),
        ipd_mm_est=g["ipd_mm_est"],
        nose_bridge_mm_est=g["nose_bridge_mm_est"],
        temporal_est=g["temporal_est"],
        eyebrow_in_frame_zone=g["eyebrow_in_frame_zone"],
        warnings=g["warnings"],
    )

@router.delete("/analyze/photo")
def delete_photo():
    # STORE_PHOTOS=false: nada persiste; el borrado es local + confirmación legal.
    return {"ok": True, "msg": "Foto descartada. No conservamos imágenes sin tu permiso (Ley 1581/2012)."}
