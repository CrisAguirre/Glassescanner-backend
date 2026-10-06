from fastapi import APIRouter
from ..schemas import FeedbackIn
from ..db import get_db
from collections import Counter

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
            pass
    return {"ok": True}

@router.get("/feedback/stats")
async def feedback_stats():
    docs = list(MEM)
    db = get_db()
    if db is not None:
        try:
            docs = await db["feedback"].find({}, {"_id": 0}).to_list(1000) or docs
        except Exception:
            pass
    n = len(docs)
    if not n:
        return {"n": 0, "avg_helpful": None, "verdicts": {}, "sugerencia": "Sin datos aún (meta piloto: 30)."}
    avg = round(sum(d["helpful"] for d in docs) / n, 2)
    verdicts = dict(Counter(d["verdict"] for d in docs))
    parcial_rate = verdicts.get("parcial", 0) / n
    sug = "Umbrales OK."
    if parcial_rate > 0.4:
        sug = "Parcial >40%: sube contraste a 35 pts o baja umbral compatible a 70."
    elif avg < 4:
        sug = "Ayuda <4/5: revisa razones (lenguaje óptico) antes de tocar scoring."
    return {"n": n, "avg_helpful": avg, "verdicts": verdicts, "parcial_rate": round(parcial_rate, 2), "sugerencia": sug}
