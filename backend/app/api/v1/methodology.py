from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.http_cache import set_public_cache
from app.schemas.api import MetricDefinitionOut, MethodologyOut
from app.services import metrics as metric_service

router = APIRouter()


@router.get("/methodology", response_model=MethodologyOut)
async def methodology(response: Response, db: AsyncSession = Depends(get_db)) -> MethodologyOut:
    set_public_cache(response)
    defs = await metric_service.list_metric_definitions(db)
    return MethodologyOut(
        timezone="UTC",
        intervals={
            "day": "UTC calendar day [00:00, 24:00)",
            "week": "ISO week starting Monday 00:00 UTC",
            "month": "Calendar month starting on the 1st 00:00 UTC",
            "quarter": "Calendar quarter (Jan/Apr/Jul/Oct) 00:00 UTC",
            "year": "Calendar year starting 1 January 00:00 UTC",
        },
        privacy_summary=(
            "WikiSignals emphasizes aggregate community-health analytics from public "
            "Wikimedia data. It does not rank individual volunteers, infer protected "
            "characteristics, or present surveillance-oriented behavioral profiles."
        ),
        metrics=[MetricDefinitionOut.model_validate(d) for d in defs],
    )
