"""Matriz experta 7 rostros x 6(+2) formas + scoring ponderado.
Ponderación: proporción 40, contraste 30, cejas/IPD 20, puente 10.
Umbrales: >=75 compatible, 55-74 parcial, <55 incompatible.
"""
from ..schemas import FaceMetrics, Frame, Recommendation

# contraste: qué formas favorecen a cada rostro
CONTRASTE = {
    "redondo": {"rectangular", "cuadrado", "wayfarer"},
    "cuadrado": {"redondo", "oval", "aviador"},
    "corazon": {"oval", "rimless", "redondo"},
    "diamante": {"oval", "cat-eye", "rimless"},
    "oblongo": {"cuadrado", "wayfarer", "redondo"},
    "triangular": {"cat-eye", "aviador", "rectangular"},
    "oval": {"rectangular", "redondo", "cuadrado", "oval", "aviador", "wayfarer", "cat-eye", "rimless"},
}

def score_frame(m: FaceMetrics, f: Frame) -> Recommendation:
    reasons = []
    # 1. Proporción (40): ancho marco vs temporal estimado (temporal ≈ 138 mm stub; S2 lo deriva de landmarks)
    temporal_est = 138.0
    diff = abs(f.ancho_total_mm - temporal_est)
    prop = max(0, 40 - diff * 2)  # -2 pts por mm
    reasons.append(
        f"Ancho marco {f.ancho_total_mm:.0f} mm vs rostro ~{temporal_est:.0f} mm (dif {diff:.0f} mm): "
        + ("proporción ideal." if diff <= 10 else "aceptable." if diff <= 20 else "desproporcionado.")
    )
    # 2. Contraste (30)
    cont = 30 if f.forma in CONTRASTE.get(m.face_shape, set()) else 12
    reasons.append(
        f"Rostro {m.face_shape} + marco {f.forma}: "
        + ("contraste que equilibra facciones." if cont == 30 else "repite la geometría del rostro; buscar contraste.")
    )
    # 3. Cejas/IPD (20)
    ci = 20 if m.eyebrow_in_frame_zone else 8
    if not m.eyebrow_in_frame_zone:
        reasons.append("Ceja fuera de la zona del marco: ajustar altura (B) o posición.")
    else:
        reasons.append(f"IPD estimado {m.ipd_mm_est:.0f} mm con pupilas centradas: buena fijación óptica.")
    # 4. Puente (10)
    pdiff = abs(f.D_mm - m.nose_bridge_mm_est)
    pue = max(0, 10 - pdiff * 2)
    if pdiff > 2:
        reasons.append(f"Puente {f.D_mm:.0f} mm vs nasal ~{m.nose_bridge_mm_est:.0f} mm: riesgo de presión/deslizamiento.")
    else:
        reasons.append(f"Puente {f.D_mm:.0f} mm compatible con nariz: apoyo estable.")
    score = round(prop + cont + ci + pue, 1)
    verdict = "compatible" if score >= 75 else "parcial" if score >= 55 else "incompatible"
    return Recommendation(frame_id=f.id, score=score, verdict=verdict, reasons=reasons[:3])
