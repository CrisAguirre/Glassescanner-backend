"""Matriz experta 7 rostros x 8 formas + scoring ponderado.

Pesos (2026-10-20): proporción 35, contraste 25, IPD 20, puente 10, cejas 10.
Umbrales: >=80 compatible, 60-79 parcial, <60 incompatible.

Cambios frente a la versión anterior:
- Se incorpora el centrado óptico real (PD montura ≈ A + D vs IPD estimado),
  que antes solo se mencionaba en las razones y no puntuaba.
- El contraste pasa a 3 niveles (recomendado / neutro / evitar) en vez de 2.
- La proporción usa diferencia relativa (%), no milímetros absolutos.
- Un marco con puente muy desajustado o pupila muy descentrada no puede ser
  "compatible" aunque sume puntos por otras vías.
"""

from ..schemas import FaceMetrics, Frame, Recommendation

# Formas que favorecen a cada rostro (contraste recomendado).
CONTRASTE = {
    "redondo": {"rectangular", "cuadrado", "wayfarer"},
    "cuadrado": {"redondo", "oval", "aviador", "cat-eye"},
    "corazon": {"oval", "rimless", "redondo", "aviador"},
    "diamante": {"oval", "cat-eye", "rimless", "redondo"},
    "oblongo": {"cuadrado", "wayfarer", "redondo", "aviador"},
    "triangular": {"cat-eye", "aviador", "rectangular", "wayfarer"},
    "oval": {
        "rectangular",
        "cuadrado",
        "redondo",
        "oval",
        "aviador",
        "wayfarer",
        "cat-eye",
        "rimless",
    },
}

# Formas que repiten la geometría del rostro y conviene evitar por estética.
EVITAR = {
    "redondo": {"redondo"},
    "cuadrado": {"cuadrado", "rectangular"},
    "corazon": {"cat-eye"},
    "diamante": {"cuadrado", "rectangular"},
    "oblongo": {"rectangular"},
    "triangular": {"redondo"},
    "oval": set(),
}


def _proportion(m: FaceMetrics, f: Frame):
    temp = getattr(m, "temporal_est", 138.0) or 138.0
    diff = abs(f.ancho_total_mm - temp)
    rel = diff / max(temp, 1e-6)
    if rel <= 0.02:
        pts = 35
    elif rel <= 0.04:
        pts = 28
    elif rel <= 0.07:
        pts = 18
    elif rel <= 0.10:
        pts = 8
    else:
        pts = 0
    sentido = "amplio" if f.ancho_total_mm > temp else "estrecho"
    if rel <= 0.02:
        txt = (
            f"Ancho marco {f.ancho_total_mm:.0f} mm vs rostro ~{temp:.0f} mm "
            f"(dif {diff:.0f} mm): proporción ideal."
        )
    elif rel <= 0.04:
        txt = (
            f"Ancho marco {f.ancho_total_mm:.0f} mm vs rostro ~{temp:.0f} mm "
            f"(dif {diff:.0f} mm): ajuste adecuado."
        )
    elif rel <= 0.10:
        txt = (
            f"Ancho marco {f.ancho_total_mm:.0f} mm vs rostro ~{temp:.0f} mm "
            f"(dif {diff:.0f} mm): algo {sentido}; probar otra talla."
        )
    else:
        txt = (
            f"Ancho marco {f.ancho_total_mm:.0f} mm vs rostro ~{temp:.0f} mm "
            f"(dif {diff:.0f} mm): desproporcionado."
        )
    return pts, txt


def _contrast(m: FaceMetrics, f: Frame):
    if f.forma in CONTRASTE.get(m.face_shape, set()):
        return 25, f"Rostro {m.face_shape} + marco {f.forma}: contraste recomendado."
    if f.forma in EVITAR.get(m.face_shape, set()):
        return (
            0,
            f"Rostro {m.face_shape} + marco {f.forma}: repite la geometría; buscar contraste.",
        )
    return 12, f"Rostro {m.face_shape} + marco {f.forma}: combinación neutra."


def _optical(m: FaceMetrics, f: Frame):
    ipd = getattr(m, "ipd_mm_est", 63.0) or 63.0
    nose = getattr(m, "nose_bridge_mm_est", 18.0) or 18.0
    frame_pd = f.A_mm + f.D_mm
    pd_diff = abs(frame_pd - ipd)
    if pd_diff <= 4:
        ipd_pts, ipd_txt = 20, "centrado óptico"
    elif pd_diff <= 7:
        ipd_pts, ipd_txt = 15, "centrado aceptable"
    elif pd_diff <= 10:
        ipd_pts, ipd_txt = 8, "decentrado moderado"
    else:
        ipd_pts, ipd_txt = 0, "pupila muy descentrada; puede causar fatiga"

    bridge_diff = abs(f.D_mm - nose)
    if bridge_diff <= 1:
        bridge_pts, bridge_txt = 10, "apoyo nasal estable"
    elif bridge_diff <= 2:
        bridge_pts, bridge_txt = 7, "apoyo nasal adecuado"
    elif bridge_diff <= 3:
        bridge_pts, bridge_txt = 4, "apoyo nasal justo"
    else:
        bridge_pts, bridge_txt = 0, "riesgo de presión/deslizamiento"

    txt = (
        f"PD montura {frame_pd:.0f} mm vs IPD {ipd:.0f} mm (dif {pd_diff:.0f}): {ipd_txt}. "
        f"Puente {f.D_mm:.0f} vs nasal {nose:.0f} mm (dif {bridge_diff:.0f}): {bridge_txt}."
    )
    return ipd_pts + bridge_pts, txt, pd_diff, bridge_diff


def score_frame(m: FaceMetrics, f: Frame) -> Recommendation:
    prop_pts, prop_txt = _proportion(m, f)
    cont_pts, cont_txt = _contrast(m, f)
    opt_pts, opt_txt, pd_diff, bridge_diff = _optical(m, f)
    brow_pts = 10 if getattr(m, "eyebrow_in_frame_zone", True) else 3
    brow_txt = (
        "Ceja dentro de la zona del marco."
        if brow_pts == 10
        else "Ceja fuera de la zona: ajustar altura o posición del marco."
    )

    score = round(prop_pts + cont_pts + opt_pts + brow_pts, 1)
    verdict = "compatible" if score >= 80 else "parcial" if score >= 60 else "incompatible"

    # Un puente muy desajustado o una pupila muy descentrada impiden catalogar
    # el marco como compatible, aunque la estética y el ancho sumen puntos.
    if verdict == "compatible" and (bridge_diff > 3 or pd_diff > 10):
        verdict = "parcial"

    reasons = [prop_txt, cont_txt, brow_txt if (brow_pts < 10 and bridge_diff <= 3) else opt_txt]
    return Recommendation(
        frame_id=f.id, score=score, verdict=verdict, reasons=reasons[:3]
    )
