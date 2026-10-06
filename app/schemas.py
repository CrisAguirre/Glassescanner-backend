from pydantic import BaseModel, Field
from typing import List, Literal, Optional

FaceShape = Literal["oval", "redondo", "cuadrado", "corazon", "diamante", "oblongo", "triangular"]
Verdict = Literal["compatible", "parcial", "incompatible"]

class Ratios(BaseModel):
    largo_ancho: float
    frente_pomulo: float
    mandibula_frente: float

class FaceMetrics(BaseModel):
    face_detected: bool = True
    face_shape: FaceShape = "oval"
    symmetry_index: float = Field(ge=0, le=100, default=85.0)
    ratios: Ratios = Ratios(largo_ancho=1.3, frente_pomulo=0.95, mandibula_frente=0.9)
    ipd_mm_est: float = 63.0
    nose_bridge_mm_est: float = 18.0
    eyebrow_in_frame_zone: bool = True
    warnings: List[str] = []

class Frame(BaseModel):
    id: str
    nombre: str
    forma: Literal["rectangular", "cuadrado", "redondo", "oval", "aviador", "wayfarer", "cat-eye", "rimless"]
    A_mm: float  # ancho lente
    B_mm: float  # alto lente
    D_mm: float  # puente
    patilla_mm: float = 140
    ancho_total_mm: float
    material: Literal["acetato", "metal", "mixto"] = "acetato"
    color: str = "negro"
    optica_id: Optional[str] = "seed"

class Recommendation(BaseModel):
    frame_id: str
    score: float
    verdict: Verdict
    reasons: List[str]

class RecommendRequest(BaseModel):
    metrics: FaceMetrics
    frame_ids: Optional[List[str]] = None
    optica_id: Optional[str] = None

class FeedbackIn(BaseModel):
    face_shape: FaceShape = "oval"
    frame_id: str = "F01"
    verdict: Verdict = "compatible"
    helpful: int = Field(ge=1, le=5, default=5)
    comment: Optional[str] = None
    optica_id: Optional[str] = None
    caso_n: Optional[int] = None
