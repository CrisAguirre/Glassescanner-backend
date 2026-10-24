# Glassescanner Backend (FastAPI + MediaPipe Python)
Microservicio de análisis facial y recomendación de marcos. Ver planeación maestra en `../GLASSESCANNER_PLAN.md`.

## Correr en 3 comandos
Requiere Python 3.11/3.12 (MediaPipe no publica ruedas para 3.14).
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- `GET /health` → estado.
- `POST /analyze` (multipart `photo: jpg/png/webp ≤5MB`) → métricas + forma de rostro.
- `GET /frames` → catálogo (seed 64). `POST /recommend` → veredictos.

## Env
Copia `.env.example` a `.env` (no se versiona):
```
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,https://tu-front.vercel.app
MAX_PHOTO_MB=5
RATE_LIMIT_PER_MINUTE=60
STORE_PHOTOS=false
ADMIN_KEY=<clave larga y aleatoria de al menos 16 caracteres>
```
`ADMIN_KEY` protege las mutaciones del catálogo con `X-Admin-Key`. Si queda vacía o usa un placeholder, el CRUD se deshabilita; en `ENVIRONMENT=production` (o al detectar `RENDER=true`) el arranque falla para evitar desplegar sin clave.
