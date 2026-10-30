import json
import logging
import pathlib

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_admin
from ..db import get_db
from ..expert.catalog import FRAMES
from ..expert.rules import score_frame
from ..schemas import Frame, Recommendation, RecommendRequest

logger = logging.getLogger(__name__)

router = APIRouter()


async def _db_frames(optica_id: str | None = None):
    """Lee Mongo si responde; si no, None (el caller usa fallback en memoria)."""
    db = get_db()
    if db is None:
        return None
    try:
        q = {"optica_id": optica_id} if optica_id else {}
        docs = await db["frames"].find(q, {"_id": 0}).to_list(200)
        return [Frame(**d) for d in docs] or None
    except Exception:
        logger.warning("Mongo no respondió al listar frames; se usa el seed", exc_info=True)
        return None


def _mem_frames(optica_id: str | None = None):
    return [f for f in FRAMES if not optica_id or f.optica_id == optica_id]


@router.get("/frames", response_model=list[Frame])
async def list_frames(optica_id: str | None = None):
    return await _db_frames(optica_id) or _mem_frames(optica_id)


@router.post(
    "/frames",
    response_model=Frame,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
async def create_frame(f: Frame):
    if any(x.id == f.id for x in FRAMES):
        raise HTTPException(409, f"Ya existe frame {f.id}")
    FRAMES.append(f)
    db = get_db()
    if db is not None:
        try:
            await db["frames"].insert_one(f.model_dump())
        except Exception:
            logger.warning("Frame %s creado solo en memoria (Mongo falló)", f.id, exc_info=True)
    return f


@router.put(
    "/frames/{fid}", response_model=Frame, dependencies=[Depends(require_admin)]
)
async def update_frame(fid: str, f: Frame):
    for i, x in enumerate(FRAMES):
        if x.id == fid:
            FRAMES[i] = f
            db = get_db()
            if db is not None:
                try:
                    await db["frames"].replace_one(
                        {"id": fid}, f.model_dump(), upsert=True
                    )
                except Exception:
                    logger.warning(
                        "Frame %s actualizado solo en memoria (Mongo falló)", fid, exc_info=True
                    )
            return f
    raise HTTPException(404, f"Frame {fid} no existe")


@router.delete("/frames/{fid}", dependencies=[Depends(require_admin)])
async def delete_frame(fid: str):
    global FRAMES
    if not any(x.id == fid for x in FRAMES):
        raise HTTPException(404, f"Frame {fid} no existe")
    FRAMES[:] = [x for x in FRAMES if x.id != fid]
    db = get_db()
    if db is not None:
        try:
            await db["frames"].delete_one({"id": fid})
        except Exception:
            logger.warning("Frame %s borrado solo en memoria (Mongo falló)", fid, exc_info=True)
    return {"ok": True, "id": fid}


@router.post("/recommend", response_model=list[Recommendation])
async def recommend(req: RecommendRequest):
    pool = await _db_frames(req.optica_id) or _mem_frames(req.optica_id)
    targets = [f for f in pool if not req.frame_ids or f.id in req.frame_ids]
    recs = [score_frame(req.metrics, f) for f in targets]
    # Orden estable: score desc, id asc. Evita que el top-1 dependa del orden
    # del catálogo cuando hay empates.
    return sorted(recs, key=lambda r: (-r.score, r.frame_id))


@router.post("/frames/seed", dependencies=[Depends(require_admin)])
async def seed_frames():
    """Carga frames_seed.json a Mongo (requiere MONGODB_URI)."""
    db = get_db()
    if db is None:
        return {"ok": False, "msg": "Sin MONGODB_URI"}
    seed = json.loads(
        pathlib.Path("app/data/frames_seed.json").read_text(encoding="utf-8")
    )
    await db["frames"].delete_many({})
    await db["frames"].insert_many(seed)
    return {"ok": True, "n": len(seed)}
