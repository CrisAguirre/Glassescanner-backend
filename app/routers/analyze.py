from fastapi import APIRouter, UploadFile, File, HTTPException
import os
from ..schemas import FaceMetrics, Ratios

router = APIRouter()

MAX_MB = float(os.getenv("MAX_PHOTO_MB", "5"))

@router.post("/analyze", response_model=FaceMetrics)
async def analyze(photo: UploadFile = File(...)):
    data = await photo.read()
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, f"Foto supera {MAX_MB} MB")
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Formato válido: JPG/PNG/WebP")
    # TODO S2: MediaPipe Python real (landmarks 468) + geometría en app/face/geometry.py.
    # Stub con valores plausibles para no bloquear al front.
    return FaceMetrics(
        face_detected=True,
        face_shape="oval",
        symmetry_index=87.5,
        ratios=Ratios(largo_ancho=1.32, frente_pomulo=0.96, mandibula_frente=0.9),
        ipd_mm_est=63.0,
        nose_bridge_mm_est=18.0,
        eyebrow_in_frame_zone=True,
        warnings=["stub: conectar MediaPipe en S2"],
    )
