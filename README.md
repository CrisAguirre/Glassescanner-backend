# Glassescanner Backend (FastAPI + MediaPipe Python)
Microservicio de análisis facial y recomendación de marcos. Ver planeación maestra en `../GLASSESCANNER_PLAN.md`.

## Correr en 3 comandos
Requiere Python 3.11/3.12 (MediaPipe no publica ruedas para 3.14).
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt   # incluye requirements.txt + herramientas de test
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

## Rate limit y proxy
El límite por IP usa `request.client.host`; la app **no** lee `X-Forwarded-For` por su cuenta para que un cliente no pueda elegir su cupo. Detrás de Render, el contenedor arranca con `--proxy-headers --forwarded-allow-ips=*` (ver `Dockerfile`) y uvicorn reescribe la IP desde el header solo en ese escenario. Si expones el contenedor directamente a internet, quita `--forwarded-allow-ips=*`.

## Tests y calidad
```bash
.\.venv\Scripts\python.exe -m pytest -q --cov=app --cov-report=term-missing
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m bandit -r app -q
.\.venv\Scripts\python.exe -m pip_audit --local
```
Los tests no necesitan Mongo ni MediaPipe: las rutas de fallo se cubren con dobles
(`tests/test_failures.py`). Único riesgo aceptado de `pip-audit`: `protobuf 4.25.9`
por `mediapipe 0.10.14`.

## Docker
La imagen usa `python:3.12-slim`, instala solo `requirements.txt` y corre como
usuario `appuser` sin privilegios. Incluye `HEALTHCHECK` contra `/health`:
```bash
docker build -t glassescanner-api .
docker run -p 8000:8000 --env-file .env glassescanner-api
```
