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

    # Auto-seed content if collection is empty (first deploy / fresh environment)
    if collection.count() == 0:
        _log.info("ChromaDB is empty — seeding mock clinical data and T&F journals…")
        try:
            from app.ingestion.pipeline import seed_mock, seed_taylor_francis
            import asyncio
            loop = asyncio.get_event_loop()
            n_mock = await seed_mock(collection, settings)
            _log.info("Seeded %d mock clinical chunks.", n_mock)
            n_tf = await loop.run_in_executor(None, seed_taylor_francis, collection, settings.embedding_model)
            _log.info("Seeded %d Taylor & Francis journal entries.", n_tf)
        except Exception as exc:
            _log.warning("Auto-seed failed (app still starts): %s", exc)
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
