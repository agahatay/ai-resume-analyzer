import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.services.semantic_matcher import preload_model

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Loading the sentence-transformers model takes seconds and can block on
    # the network. Doing it in a background thread lets uvicorn open the port
    # immediately; a match request that arrives first waits for that same load.
    threading.Thread(target=preload_model, name="semantic-model-preload", daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
