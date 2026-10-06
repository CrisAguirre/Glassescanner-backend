# Glassescanner Backend (FastAPI + MediaPipe Python)
Microservicio de análisis facial y recomendación de marcos. Ver planeación maestra en `../GLASSESCANNER_PLAN.md`.

## Correr en 3 comandos
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- `GET /health` → estado.
- `POST /analyze` (multipart `photo: jpg/png/webp ≤5MB`) → métricas + forma de rostro.
- `GET /frames` → catálogo (seed 12). `POST /recommend` → veredictos.

## Env
```
CORS_ORIGINS=http://localhost:5173,https://tu-front.vercel.app
MAX_PHOTO_MB=5
STORE_PHOTOS=false
```
