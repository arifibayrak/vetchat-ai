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

    NOTE: init_db() is NOT here — it's initialized synchronously in lifespan
    so auth endpoints don't get "Database not configured" during the boot
    window. Only the slower create_tables() lives here.
    """
    # Yield the event loop so uvicorn can finish startup BEFORE we start
    # blocking work. Without this, sync embedder/model-load calls inside
    # the first seeding step can stall the lifespan yield → 502 window.
    await asyncio.sleep(2)
    _log.info("Background boot starting…")

    loop = asyncio.get_running_loop()

    def _sync_seed() -> None:
        """All the blocking seed work runs in a worker thread with its own loop."""
        try:
            if collection.count() == 0:
                _log.info("ChromaDB is empty — seeding mock clinical data and T&F journals…")
                from app.ingestion.pipeline import seed_mock, seed_taylor_francis
                # seed_mock is async-declared but all internal work is sync;
                # a fresh event loop in this worker thread runs it safely.
                n_mock = asyncio.run(seed_mock(collection, settings))
                _log.info("Seeded %d mock clinical chunks.", n_mock)
                n_tf = seed_taylor_francis(collection, settings.embedding_model)
                _log.info("Seeded %d Taylor & Francis journal entries.", n_tf)
            else:
                _log.info("ChromaDB has %d documents — skipping seed.", collection.count())
        except Exception as exc:
            _log.warning("Background auto-seed failed (service still healthy): %s", exc)

    await loop.run_in_executor(None, _sync_seed)

    # Database table creation (migrations). init_db already ran in lifespan;
    # this just ensures the schema exists — safe to run on every boot.
    if settings.database_url:
        try:
            from app.database import create_tables
            await create_tables()
            _log.info("Database tables ready.")
        except Exception as exc:
            _log.warning("DB table creation failed (app still healthy): %s", exc)

    _log.info("Background boot complete.")


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

    # DB session factory must be ready BEFORE serving requests — auth/conversations
    # endpoints depend on it. init_db() is fast (no connection, no query) — just
    # creates the engine + sessionmaker. The slow schema migration lives in the
    # background boot task instead.
    if settings.database_url:
        from app.database import init_db
        init_db(settings.database_url)
        _log.info("Database session factory initialised.")
    else:
        _log.info("DATABASE_URL not set — auth and chat history disabled.")

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
