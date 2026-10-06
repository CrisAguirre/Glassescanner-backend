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
    if len(data) > settings.MAX_PHOTO_MB * 1024 * 1024:
        raise HTTPException(400, f"Foto supera {settings.MAX_PHOTO_MB} MB")
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Formato válido: JPG/PNG/WebP")
    try:
        import cv2
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except ImportError:
        img = None
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
            ratios=Ratios(largo_ancho=m["largo_ancho"], frente_pomulo=0.95, mandibula_frente=0.9),
            ipd_mm_est=m["ipd_mm_est"],
            nose_bridge_mm_est=m["nose_bridge_mm_est"],
            eyebrow_in_frame_zone=True,
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
        ratios=Ratios(largo_ancho=g["largo_ancho"], frente_pomulo=0.95, mandibula_frente=0.9),
        ipd_mm_est=g["ipd_mm_est"],
        nose_bridge_mm_est=g["nose_bridge_mm_est"],
        eyebrow_in_frame_zone=True,
        warnings=g["warnings"],
    )

@router.delete("/analyze/photo")
def delete_photo():
    # STORE_PHOTOS=false: nada persiste; el borrado es local + confirmación legal.
    return {"ok": True, "msg": "Foto descartada. No conservamos imágenes sin tu permiso (Ley 1581/2012)."}
