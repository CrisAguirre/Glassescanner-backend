import json
import logging
from pathlib import Path

from ..schemas import Frame

logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "frames_seed.json"


def _load_frames() -> list[Frame]:
    if not _SEED_PATH.exists():
        logger.warning("No existe %s; el catálogo en memoria queda vacío", _SEED_PATH)
        return []
    try:
        raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
        return [Frame(**item) for item in raw]
    except Exception:
        # Un seed corrupto no debe tumbar la API: se sirve vacío y queda en logs.
        logger.exception("No se pudo leer %s; catálogo vacío", _SEED_PATH)
        return []


FRAMES: list[Frame] = _load_frames()
