from typing import Literal

from pydantic import BaseModel, Field

FaceShape = Literal[
    "oval", "redondo", "cuadrado", "corazon", "diamante", "oblongo", "triangular"
]
Verdict = Literal["compatible", "parcial", "incompatible"]


class Ratios(BaseModel):
    largo_ancho: float
    frente_pomulo: float
    mandibula_frente: float


class FaceMetrics(BaseModel):
    face_detected: bool = True
    face_shape: FaceShape = "oval"
    symmetry_index: float = Field(ge=0, le=100, default=85.0)
    ratios: Ratios = Field(
        default_factory=lambda: Ratios(
            largo_ancho=1.3, frente_pomulo=0.95, mandibula_frente=0.9
        )
    )
    ipd_mm_est: float = 63.0
    nose_bridge_mm_est: float = 18.0
    temporal_est: float = 138.0
    eyebrow_in_frame_zone: bool = True
    warnings: list[str] = Field(default_factory=list)


class Frame(BaseModel):
    id: str
    nombre: str
    forma: Literal[
        "rectangular",
        "cuadrado",
        "redondo",
        "oval",
        "aviador",
        "wayfarer",
        "cat-eye",
        "rimless",
    ]
    A_mm: float  # ancho lente
    B_mm: float  # alto lente
    D_mm: float  # puente
    patilla_mm: float = 140
    ancho_total_mm: float
    material: Literal["acetato", "metal", "mixto"] = "acetato"
    color: str = "negro"
    genero: Literal["unisex", "hombre", "mujer"] = "unisex"
    precio_rango: Literal["economico", "medio", "premium"] = "medio"
    marca: str = "OptiVision"
    imagen_url: str | None = None
    tipo_lente: list[str] = Field(
        default_factory=lambda: [
            "monofocal",
            "bifocal",
            "progresivo",
            "blue-cut",
            "fotocromático",
        ]
    )
    estilo: Literal["casual", "formal", "vintage", "sport"] = "casual"
    talla: Literal["S", "M", "L"] = "M"
    optica_id: str | None = "seed"


class Recommendation(BaseModel):
    frame_id: str
    score: float
    verdict: Verdict
    reasons: list[str]


class RecommendRequest(BaseModel):
    metrics: FaceMetrics
    frame_ids: list[str] | None = None
    optica_id: str | None = None


class FeedbackIn(BaseModel):
    face_shape: FaceShape = "oval"
    face_shape_detected: FaceShape | None = None
    frame_id: str = "F01"
    recommended_frame_id: str | None = None
    verdict: Verdict = "compatible"
    helpful: int = Field(ge=1, le=5, default=5)
    comment: str | None = None
    optica_id: str | None = None
    caso_n: int | None = None
    marco_lleva: str | None = None
    va_bien: Literal["si", "no", "no_aplica"] | None = None
