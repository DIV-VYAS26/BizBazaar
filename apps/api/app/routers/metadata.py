from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import Actor, authenticate
from app.db.session import get_db
from app.schemas.analytics import CoverageBatch, CoverageDeclaration, PromotionSettings
from app.services.metadata import declare_coverage, read_coverage, read_settings, update_settings

router = APIRouter(tags=["analytics inputs"])
Db = Annotated[Session, Depends(get_db)]
CurrentActor = Annotated[Actor, Depends(authenticate)]
ReportDate = Annotated[date, Query(ge=date(2000, 1, 1), le=date(2100, 12, 31))]


@router.get("/coverage", response_model=list[CoverageDeclaration])
def coverage(
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
):
    return read_coverage(db, actor, start_date, end_date, includes_simulated)


@router.post("/coverage", response_model=CoverageBatch)
def coverage_declare(payload: CoverageBatch, actor: CurrentActor, db: Db):
    return declare_coverage(db, actor, payload)


@router.get("/settings/promotion", response_model=PromotionSettings | None)
def promotion_settings(actor: CurrentActor, db: Db):
    return read_settings(db, actor)


@router.post("/settings/promotion", response_model=PromotionSettings)
def promotion_settings_update(payload: PromotionSettings, actor: CurrentActor, db: Db):
    return update_settings(db, actor, payload)
