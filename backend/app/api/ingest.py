from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.ingestion.pipeline import run_ingestion
from app.models.ingest import IngestRequest, IngestResult

router = APIRouter()


@router.post("/ingest", response_model=IngestResult)
async def ingest(request: Request, body: IngestRequest) -> IngestResult | JSONResponse:
    settings = get_settings()

    has_sd = bool(settings.sciencedirect_api_key)
    has_sn = bool(settings.springer_nature_api_key)

    if not has_sd and not has_sn:
        return JSONResponse(
            status_code=503,
            content={
                "error": (
                    "No ingestion API keys configured. "
                    "Set SCIENCEDIRECT_API_KEY and/or SPRINGER_NATURE_API_KEY in .env, "
                    "or run 'python scripts/seed_mock_data.py' for offline testing."
                )
            },
        )

    collection = request.app.state.chroma_collection
    result = run_ingestion(
        body.queries,
        collection,
        settings,
        count=body.count,
        sources=body.sources,
    )

    return IngestResult(
        articles_fetched=result["articles_fetched"],
        chunks_upserted=result["chunks_upserted"],
        queries_processed=body.queries,
        errors=result["errors"],
    )
