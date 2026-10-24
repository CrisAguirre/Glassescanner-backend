import io
import logging

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, ImageOps

from ..config import settings
from ..schemas import FaceMetrics, Ratios
from ..face.geometry import (
    detect_face_box_bgr,
    metrics_from_box,
    try_mediapipe_landmarks,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Evita bombas de descompresión antes de convertir la imagen a numpy.
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


@router.post("/analyze", response_model=FaceMetrics)
def analyze(photo: UploadFile = File(...)):
    """Analiza una foto. Es síncrono a propósito: FastAPI lo ejecuta en el
    threadpool y no bloquea el event loop durante PIL/MediaPipe/OpenCV.
    """
    ctype = (photo.content_type or "").lower()
    valid_types = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/pjpeg",
        "application/octet-stream",
    }
    fname = (photo.filename or "").lower()
    if ctype not in valid_types and not any(
        fname.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")
    ):
        raise HTTPException(400, "Formato válido: JPG/PNG/WebP")

    max_bytes = int(settings.MAX_PHOTO_MB * 1024 * 1024)
    try:
        photo.file.seek(0)
        data = photo.file.read(max_bytes + 1)
    except Exception as exc:
        logger.warning("No se pudo leer el upload: %s", exc)
        raise HTTPException(400, "No se pudo leer la imagen") from exc
    if not data:
        raise HTTPException(400, "La imagen está vacía")
    if len(data) > max_bytes:
        raise HTTPException(
            413,
            f"La imagen supera el límite de {settings.MAX_PHOTO_MB:g} MB",
        )

    img = None
    # 1) PIL primero (puro Python+numpy, no depende de cv2 ni de libs del sistema)
    try:
        pil_img = Image.open(io.BytesIO(data))
        if pil_img.width * pil_img.height > MAX_IMAGE_PIXELS:
            raise HTTPException(
                413,
                "La imagen tiene demasiados píxeles. Reduce su resolución.",
            )
        # Respetar la orientación EXIF de fotos tomadas con el móvil.
        pil_img = ImageOps.exif_transpose(pil_img).convert("RGB")
        img = np.array(pil_img)[:, :, ::-1].copy()  # RGB->BGR sin cv2
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            413,
            "La imagen tiene demasiados píxeles. Reduce su resolución.",
        ) from exc
    except Exception:
        img = None

    # 2) cv2.imdecode como respaldo
    if img is None:
        try:
            import cv2

            buf = np.frombuffer(data, dtype=np.uint8).copy()
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            img = None
    if img is None:
        raise HTTPException(400, "No se pudo decodificar la imagen")
    h, w = img.shape[:2]

    # 1. MediaPipe real (Render Python 3.11 sí lo tiene)
    try:
        m = try_mediapipe_landmarks(img)
    except Exception:
        logger.exception("MediaPipe falló; se usará el respaldo Haar")
        m = None
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
        return FaceMetrics(
            face_detected=False,
            warnings=[
                "No se detectó rostro frontal. Acércate a la luz y mira de frente."
            ],
        )
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
    return {
        "ok": True,
        "msg": "Foto descartada. No conservamos imágenes sin tu permiso (Ley 1581/2012).",
    }
