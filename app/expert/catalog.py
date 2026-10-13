import json
from pathlib import Path
from ..schemas import Frame

_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "frames_seed.json"


def _load_frames() -> list[Frame]:
    if _SEED_PATH.exists():
        try:
            raw = json.loads(_SEED_PATH.read_text(encoding="utf-8"))
            return [Frame(**item) for item in raw]
        except Exception:
            pass
    return []


FRAMES: list[Frame] = _load_frames()
