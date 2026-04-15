import logging
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import get_settings

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Initialise Chroma and store on app state
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    app.state.chroma_client = client
    app.state.chroma_collection = collection

    # Initialise PostgreSQL if DATABASE_URL is configured
    if settings.database_url:
        from app.database import create_tables, init_db
        init_db(settings.database_url)
        try:
            await create_tables()
            _log.info("Database tables ready.")
        except Exception as exc:
            _log.warning("DB table creation failed (app still starts): %s", exc)
    else:
        _log.info("DATABASE_URL not set — auth and chat history disabled.")

    yield

    # Cleanup (Chroma PersistentClient handles its own flush)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Lenny",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)

    # Import routers here to avoid circular imports at module level
    from app.api import chat, ingest
    from app.api.auth import router as auth_router
    from app.api.conversations import router as conv_router

    app.include_router(chat.router)
    app.include_router(ingest.router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(conv_router, tags=["conversations"])

    return app


app = create_app()
