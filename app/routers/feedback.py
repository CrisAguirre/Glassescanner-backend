import logging
from collections import Counter, defaultdict

from fastapi import APIRouter

from ..db import get_db
from ..schemas import FeedbackIn

logger = logging.getLogger(__name__)

router = APIRouter()
MEM: list[dict] = []  # fallback sin Mongo


@router.post("/feedback", status_code=201)
async def save_feedback(fb: FeedbackIn):
    doc = fb.model_dump()
    MEM.append(doc)
    db = get_db()
    if db is not None:
        try:
            await db["feedback"].insert_one(doc)
        except Exception:
            # Se conserva el feedback en memoria; perder el voto sin rastro sí duele.
            logger.warning("No se pudo guardar feedback en Mongo; queda en memoria", exc_info=True)
    return {"ok": True}


@router.get("/feedback/stats")
async def feedback_stats():
    docs = list(MEM)
    db = get_db()
    if db is not None:
        try:
            docs = await db["feedback"].find({}, {"_id": 0}).to_list(1000) or docs
        except Exception:
            logger.warning("Mongo no respondió en /feedback/stats; se usa memoria", exc_info=True)
    n = len(docs)
    if not n:
        return {
            "n": 0,
            "avg_helpful": None,
            "verdicts": {},
            "parcial_rate": None,
            "fit_rate": None,
            "fit_n": 0,
            "shape_accuracy": None,
            "shape_n": 0,
            "helpful_dist": {},
            "by_face_shape": {},
            "sugerencia": "Sin datos aún (meta piloto: 30).",
        }

    avg = round(sum(d.get("helpful", 5) for d in docs) / n, 2)
    verdicts = dict(Counter(d.get("verdict", "compatible") for d in docs))
    parcial_rate = round(verdicts.get("parcial", 0) / n, 2)
    helpful_dist = {
        str(k): v for k, v in sorted(Counter(str(d.get("helpful", 5)) for d in docs).items())
    }

    # Ajuste real: solo cuenta casos donde el óptico marcó sí/no.
    fit_docs = [d for d in docs if d.get("va_bien") in ("si", "no")]
    fit_n = len(fit_docs)
    fit_rate = (
        round(sum(1 for d in fit_docs if d["va_bien"] == "si") / len(fit_docs), 2)
        if fit_docs
        else None
    )

    # Acierto de la forma detectada vs forma real corregida por el óptico.
    shape_docs = [
        d
        for d in docs
        if d.get("face_shape_detected") and d.get("face_shape")
    ]
    shape_n = len(shape_docs)
    shape_accuracy = (
        round(
            sum(
                1
                for d in shape_docs
                if d["face_shape_detected"] == d["face_shape"]
            )
            / len(shape_docs),
            2,
        )
        if shape_docs
        else None
    )

    by_shape: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "helpful_sum": 0, "verdicts": Counter()}
    )
    for d in docs:
        s = by_shape[d.get("face_shape", "oval")]
        s["n"] += 1
        s["helpful_sum"] += d.get("helpful", 5)
        s["verdicts"][d.get("verdict", "compatible")] += 1
    by_face_shape = {
        k: {
            "n": v["n"],
            "avg_helpful": round(v["helpful_sum"] / v["n"], 2),
            "verdicts": dict(v["verdicts"]),
        }
        for k, v in sorted(by_shape.items())
    }

    faltantes = []
    if fit_n < 30:
        faltantes.append(f"fit_n={fit_n}/30 (ajuste real sí/no)")
    if shape_n < 30:
        faltantes.append(f"shape_n={shape_n}/30 (forma detectada vs real)")
    if n < 30:
        faltantes.append(f"n={n}/30 (feedback total)")
    if faltantes:
        sug = "Seguir piloteando: faltan " + ", ".join(faltantes) + "."
        if avg < 4:
            sug += " Ayuda <4/5: revisar el lenguaje de las razones."
    elif avg < 4:
        sug = "Ayuda <4/5: revisar el lenguaje de las razones antes de tocar scoring."
    elif parcial_rate > 0.40:
        sug = (
            "Parcial >40%: revisar contraste/proporción en rules.py; "
            "no bajar el umbral 'compatible' (haría el sistema más permisivo)."
        )
    else:
        sug = "Umbrales OK."

    return {
        "n": n,
        "avg_helpful": avg,
        "verdicts": verdicts,
        "parcial_rate": parcial_rate,
        "fit_rate": fit_rate,
        "fit_n": fit_n,
        "shape_accuracy": shape_accuracy,
        "shape_n": shape_n,
        "helpful_dist": helpful_dist,
        "by_face_shape": by_face_shape,
        "sugerencia": sug,
    }
