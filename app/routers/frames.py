from fastapi import APIRouter
from ..schemas import Frame, RecommendRequest, Recommendation
from ..expert.rules import score_frame
from ..expert.catalog import FRAMES
from ..db import get_db

router = APIRouter()

@router.get("/frames", response_model=list[Frame])
async def list_frames():
    db = get_db()
    if db is not None:
        try:
            docs = await db["frames"].find({}, {"_id": 0}).to_list(100)
            if docs:
                return [Frame(**d) for d in docs]
        except Exception:
            pass
    return FRAMES

@router.post("/recommend", response_model=list[Recommendation])
def recommend(req: RecommendRequest):
    targets = [f for f in FRAMES if not req.frame_ids or f.id in req.frame_ids]
    return [score_frame(req.metrics, f) for f in targets]

@router.post("/frames/seed")
async def seed_frames():
    """Carga frames_seed.json a Mongo (requiere MONGODB_URI)."""
    import json, pathlib
    db = get_db()
    if db is None:
        return {"ok": False, "msg": "Sin MONGODB_URI"}
    seed = json.loads(pathlib.Path("app/data/frames_seed.json").read_text(encoding="utf-8"))
    await db["frames"].delete_many({})
    await db["frames"].insert_many(seed)
    return {"ok": True, "n": len(seed)}
