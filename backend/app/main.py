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

    def _collect_mock_ids() -> list[str]:
        """Read the mock JSONL files shipped in the repo and return the exact
        ids they use. Deleting by explicit id list is deterministic and avoids
        any quirks with Chroma metadata filtering."""
        import json as _json
        from pathlib import Path as _Path
        mock_dir = _Path(__file__).parent.parent / "data" / "mock"
        ids: list[str] = []
        if not mock_dir.exists():
            return ids
        for jsonl_file in mock_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file) as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        rec = _json.loads(line)
                        rid = rec.get("id")
                        if rid:
                            ids.append(rid)
            except Exception as exc:
                _log.warning("Failed to read mock ids from %s: %s", jsonl_file, exc)
        return ids

    def _sync_seed() -> None:
        """All the blocking seed work runs in a worker thread with its own loop."""
        try:
            # Purge mock chunks by explicit id list (from the JSONL files in
            # the repo). Mock DOIs like "10.1016/mock.2019.xylitol.001" must
            # never be cited to real users. Runs on every boot.
            try:
                mock_ids = _collect_mock_ids()
                if mock_ids:
                    collection.delete(ids=mock_ids)
                    _log.info("Purged %d mock chunks by id list.", len(mock_ids))
                else:
                    _log.info("No mock id list available — skipping explicit purge.")

                # Defense-in-depth: also scan for any chunk whose DOI still
                # contains "mock" (in case ids drifted from what JSONL ships).
                try:
                    hits = collection.get(
                        where={"doi": {"$ne": ""}},
                        include=["metadatas"],
                    )
                    bad_ids = [
                        i for i, m in zip(hits.get("ids", []) or [], hits.get("metadatas", []) or [])
                        if m and "mock" in str(m.get("doi", "")).lower()
                    ]
                    if bad_ids:
                        collection.delete(ids=bad_ids)
                        _log.info("Purged %d additional chunks with mock DOIs.", len(bad_ids))
                except Exception as exc:
                    _log.warning("Secondary mock DOI scan failed (non-fatal): %s", exc)
            except Exception as exc:
                _log.warning("Mock purge failed (non-fatal): %s", exc)

            if collection.count() == 0:
                from app.ingestion.pipeline import seed_taylor_francis
                # Hard gate: seed_mock only runs in local dev. Even if Railway
                # has USE_MOCK_DATA=true leftover in env vars, we require a
                # second explicit signal. Prevents accidental re-seed on prod.
                if settings.use_mock_data and settings.frontend_origin.startswith("http://localhost"):
                    _log.info("USE_MOCK_DATA=true on localhost — seeding mock clinical data (dev only)…")
                    from app.ingestion.pipeline import seed_mock
                    n_mock = asyncio.run(seed_mock(collection, settings))
                    _log.info("Seeded %d mock clinical chunks.", n_mock)
                elif settings.use_mock_data:
                    _log.warning("USE_MOCK_DATA=true but frontend_origin is not localhost — refusing to seed mock data to avoid polluting prod Chroma.")
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
