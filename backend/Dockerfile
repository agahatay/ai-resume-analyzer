# Phase 12: containerize the FastAPI backend. Current stable slim Python
# base (3.11) - compatible with the pinned FastAPI/SQLAlchemy/psycopg 3/
# sentence-transformers versions in requirements.txt without needing any
# extra system compiler toolchain, since all of those ship manylinux wheels.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/appuser/.cache/huggingface

# Non-root app user. Its home dir doubles as the sentence-transformers model
# cache location (see HF_HOME above and the hf_cache volume in
# docker-compose.yml) so the model survives container restarts instead of
# re-downloading every time.
RUN groupadd --system appuser && useradd --system --gid appuser --create-home appuser

# torch is installed first from the CPU-only wheel index. sentence-transformers
# pulls torch in transitively, and a plain "pip install" resolves to the default
# Linux build, which drags in several GB of CUDA libraries the container never
# uses. Installing torch here first means the requirements install below sees
# it as already satisfied and skips the CUDA build.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Installed as its own layer, keyed only on requirements.txt, so editing
# application code doesn't invalidate the (slow, ~GB-sized) dependency
# install layer on rebuild.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code and the Alembic migration history/config needed to run
# "alembic upgrade head" at startup. Deliberately no .env, no tests/ - see
# .dockerignore. Runtime configuration comes entirely from environment
# variables injected by docker-compose.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY docker-entrypoint.sh .

RUN chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app /home/appuser

USER appuser

# Bake the default semantic-matching model into the image so the first match
# after a cold start doesn't have to reach Hugging Face. It runs as appuser so
# the files are owned by the user that reads them at runtime. HF_HOME is set
# explicitly at the top of this file, so the download lands in the same cache
# path the app reads from.
ARG SEMANTIC_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${SEMANTIC_MODEL_NAME}')"

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
# Shell form so ${PORT} is expanded: hosts like Render inject $PORT and expect the
# app to bind to it. Locally PORT is unset and the default keeps 8000. exec keeps
# uvicorn as PID 1 so signals reach it directly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
