import asyncio
import logging
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import get_settings

_log = logging.getLogger(__name__)


async def _background_boot(app: FastAPI, collection, settings) -> None:
    """
    Non-blocking post-startup work: ChromaDB auto-seed + DB table creation.
    Runs AFTER the server binds the port so Railway's healthcheck passes
    immediately and users never hit the 502 window during deploys.
    """
    # Auto-seed content if collection is empty (first deploy / fresh environment)
    if collection.count() == 0:
        _log.info("ChromaDB is empty — seeding mock clinical data and T&F journals in background…")
        try:
            from app.ingestion.pipeline import seed_mock, seed_taylor_francis
            loop = asyncio.get_running_loop()
            n_mock = await seed_mock(collection, settings)
            _log.info("Seeded %d mock clinical chunks.", n_mock)
            n_tf = await loop.run_in_executor(None, seed_taylor_francis, collection, settings.embedding_model)
            _log.info("Seeded %d Taylor & Francis journal entries.", n_tf)
        except Exception as exc:
            _log.warning("Background auto-seed failed (service still healthy): %s", exc)
    else:
        _log.info("ChromaDB has %d documents — skipping seed.", collection.count())

    # Initialise PostgreSQL if DATABASE_URL is configured
    if settings.database_url:
        from app.database import create_tables, init_db
        init_db(settings.database_url)
        try:
            await create_tables()
            _log.info("Database tables ready.")
        except Exception as exc:
            _log.warning("DB table creation failed (app still healthy): %s", exc)
    else:
        _log.info("DATABASE_URL not set — auth and chat history disabled.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Fast path: only chroma client init here — must complete before serving
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_or_create_collection(
        name="vet_literature",
        metadata={"hnsw:space": "cosine"},
    )
    app.state.chroma_client = client
    app.state.chroma_collection = collection

    # Kick off slow boot work (auto-seed, DB migrations) in the background —
    # the server binds the port and answers /health immediately
    boot_task = asyncio.create_task(_background_boot(app, collection, settings))
    app.state.boot_task = boot_task

    yield

    # Cleanup: ensure background boot task finishes or is cancelled cleanly
    if not boot_task.done():
        boot_task.cancel()
        try:
            await boot_task
        except (asyncio.CancelledError, Exception):
            pass


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Arlo",
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
