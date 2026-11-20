import secrets
from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    Actor,
    authenticate,
    digest,
    lock_merchant,
)
from app.db.models import Campaign, DemoSession, Merchant, Reward, Transaction
from app.db.session import get_db
from app.schemas.analytics import (
    DashboardEnvelope,
    EvaluationEnvelope,
    ForecastEnvelope,
    RecommendationEnvelope,
    SummaryEnvelope,
    TrendsEnvelope,
)
from app.schemas.api import (
    CampaignCreate,
    CampaignView,
    DemoLogin,
    HealthView,
    ImportReport,
    MessageView,
    Page,
    PaymentDecision,
    PaymentStatus,
    ReportView,
    RewardView,
    SessionView,
    SimulationPayment,
    TransactionView,
)
from app.services.analytics_adapter import analytics_response
from app.services.campaigns import create_campaign, owned_campaign, transition_campaign
from app.services.csv_import import import_csv
from app.services.rewards import simulate_payment, simulate_refund
from app.services.transactions import audit

router = APIRouter()
Db = Annotated[Session, Depends(get_db)]
CurrentActor = Annotated[Actor, Depends(authenticate)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
ReportDate = Annotated[date, Query(ge=date(2000, 1, 1), le=date(2100, 12, 31))]


def require_demo(request):
    if not request.app.state.settings.demo_enabled:
        raise ApiError(404, "NOT_FOUND", "Endpoint not available")


@router.get("/health", response_model=HealthView, tags=["health"])
def health():
    return HealthView()


@router.post("/demo/session", response_model=SessionView, tags=["session"])
def demo_login(payload: DemoLogin, request: Request, response: Response, db: Db):
    require_demo(request)
    settings = request.app.state.settings
    if request.headers.get("origin") not in settings.allowed_origins:
        raise ApiError(403, "ORIGIN_REJECTED", "Browser origin is not permitted")
    row = db.scalar(
        select(DemoSession).where(DemoSession.token_hash == digest(payload.token)).with_for_update()
    )
    now = datetime.now(UTC)
    if row is None or row.kind != "DEMO" or row.revoked or row.expires_at <= now:
        raise ApiError(401, "UNAUTHENTICATED", "Demo credential is invalid or expired")
    # Consume the CLI credential by rotating to a fresh browser-only session token.
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    row.token_hash, row.csrf_hash = digest(token), digest(csrf)
    merchant = db.get(Merchant, row.merchant_id)
    result = SessionView(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        timezone=merchant.timezone,
        expires_at=row.expires_at,
    )
    audit(db, Actor(row.merchant_id, row.id), "SESSION_EXCHANGED", row.id)
    db.commit()
    max_age = int((row.expires_at - now).total_seconds())
    for name, value, http_only in [(SESSION_COOKIE, token, True), (CSRF_COOKIE, csrf, False)]:
        response.set_cookie(
            name,
            value,
            httponly=http_only,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=max_age,
            path="/",
        )
    return result


@router.get("/session", response_model=SessionView, tags=["session"])
def current_session(actor: CurrentActor, db: Db):
    row = db.get(DemoSession, actor.session_id)
    merchant = db.get(Merchant, actor.merchant_id)
    return SessionView(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        timezone=merchant.timezone,
        expires_at=row.expires_at,
        is_demo=row.kind == "DEMO",
    )


@router.post("/session/logout", response_model=MessageView, tags=["session"])
def logout(response: Response, actor: CurrentActor, db: Db):
    lock_merchant(db, actor)
    db.get(DemoSession, actor.session_id).revoked = True
    audit(db, actor, "SESSION_REVOKED", actor.session_id)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    return MessageView(message="Session revoked")


@router.post("/transactions/import", response_model=ImportReport, tags=["transactions"])
def upload_transactions(
    request: Request, actor: CurrentActor, db: Db, file: Annotated[UploadFile, File()]
):
    try:
        content = file.file.read(request.app.state.settings.max_body_bytes + 1)
        if len(content) > request.app.state.settings.max_body_bytes:
            raise ApiError(413, "BODY_TOO_LARGE", "CSV exceeds the upload limit")
        return import_csv(db, actor, content, request.app.state.settings)
    finally:
        file.file.close()


def page(db, model, actor, limit, offset, schema, *filters):
    predicates = (model.merchant_id == actor.merchant_id, *filters)
    total = db.scalar(select(func.count()).select_from(model).where(*predicates))
    rows = db.scalars(
        select(model).where(*predicates).order_by(model.id).limit(limit).offset(offset)
    ).all()
    return {
        "items": [schema.model_validate(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/transactions", response_model=Page[TransactionView], tags=["transactions"])
def transactions(
    actor: CurrentActor,
    db: Db,
    limit: Limit = 20,
    offset: Offset = 0,
    status: PaymentStatus | None = None,
):
    filters = [Transaction.status == status.value] if status else []
    return page(db, Transaction, actor, limit, offset, TransactionView, *filters)


@router.post("/campaigns", response_model=CampaignView, status_code=201, tags=["campaigns"])
def campaign_create(payload: CampaignCreate, actor: CurrentActor, db: Db):
    return create_campaign(db, actor, payload)


@router.get("/campaigns", response_model=Page[CampaignView], tags=["campaigns"])
def campaigns(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, Campaign, actor, limit, offset, CampaignView)


@router.get("/campaigns/{campaign_id}", response_model=CampaignView, tags=["campaigns"])
def campaign_detail(campaign_id: UUID, actor: CurrentActor, db: Db):
    return CampaignView.model_validate(owned_campaign(db, actor, campaign_id))


@router.post("/campaigns/{campaign_id}/approve", response_model=CampaignView, tags=["campaigns"])
def campaign_approve(campaign_id: UUID, actor: CurrentActor, db: Db):
    return transition_campaign(db, actor, campaign_id, "approve")


@router.post("/campaigns/{campaign_id}/activate", response_model=CampaignView, tags=["campaigns"])
def campaign_activate(campaign_id: UUID, actor: CurrentActor, db: Db):
    return transition_campaign(db, actor, campaign_id, "activate")


@router.post("/campaigns/{campaign_id}/complete", response_model=CampaignView, tags=["campaigns"])
def campaign_complete(campaign_id: UUID, actor: CurrentActor, db: Db):
    return transition_campaign(db, actor, campaign_id, "complete")


@router.post("/simulations/payments", response_model=PaymentDecision, tags=["simulations"])
def payment_simulate(payload: SimulationPayment, request: Request, actor: CurrentActor, db: Db):
    require_demo(request)
    return simulate_payment(db, actor, payload)


@router.post(
    "/simulations/transactions/{transaction_id}/refund",
    response_model=TransactionView,
    tags=["simulations"],
)
def refund_simulate(transaction_id: UUID, request: Request, actor: CurrentActor, db: Db):
    require_demo(request)
    return simulate_refund(db, actor, transaction_id)


@router.get("/rewards", response_model=Page[RewardView], tags=["rewards"])
def rewards(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    total = db.scalar(
        select(func.count()).select_from(Reward).where(Reward.merchant_id == actor.merchant_id)
    )
    rows = db.execute(
        select(Reward, Transaction.transaction_id)
        .join(
            Transaction,
            (Transaction.id == Reward.transaction_pk)
            & (Transaction.merchant_id == Reward.merchant_id),
        )
        .where(Reward.merchant_id == actor.merchant_id)
        .order_by(Reward.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "items": [
            RewardView.model_validate(row).model_copy(update={"transaction_id": txn_id})
            for row, txn_id in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/campaigns/{campaign_id}/report", response_model=ReportView, tags=["reports"])
def campaign_report(campaign_id: UUID, actor: CurrentActor, db: Db):
    # One repeatable-read snapshot keeps campaign budget and reward totals coherent.
    from sqlalchemy import text

    db.rollback()
    db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
    campaign = owned_campaign(db, actor, campaign_id)
    count, cost = db.execute(
        select(func.count(Reward.id), func.coalesce(func.sum(Reward.cost_paise), 0)).where(
            Reward.merchant_id == actor.merchant_id, Reward.campaign_id == campaign_id
        )
    ).one()
    return ReportView(
        campaign=CampaignView.model_validate(campaign),
        issued_count=count,
        issued_cost_paise=cost,
        remaining_budget_paise=(
            campaign.budget_cap_paise - campaign.consumed_paise - campaign.reserved_paise
        ),
        observed_accepted_collections_paise=campaign.cumulative_paise,
        limitations=[
            "Accepted campaign collections are historical counters, not current net sales.",
            "Refunds do not revoke rewards or historical campaign counters.",
            "No causal sales uplift or profit is established.",
        ],
    )


def analytical(
    operation,
    request,
    actor,
    db,
    start_date,
    end_date,
    includes_simulated,
    horizon=7,
    locale="en-IN",
    decline_threshold_percent=10,
):
    return analytics_response(
        db,
        actor,
        request.app.state.analytics_provider,
        operation,
        start_date,
        end_date,
        includes_simulated,
        request.app.state.settings.max_report_days,
        horizon,
        locale,
        decline_threshold_percent,
    )


@router.get("/dashboard", response_model=DashboardEnvelope, tags=["analytics"])
def dashboard(
    request: Request,
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
):
    return analytical("dashboard", request, actor, db, start_date, end_date, includes_simulated)


@router.get("/analytics", response_model=TrendsEnvelope, tags=["analytics"])
def analytics(
    request: Request,
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
    decline_threshold_percent: Annotated[int, Query(ge=1, le=100)] = 10,
):
    return analytical(
        "analytics",
        request,
        actor,
        db,
        start_date,
        end_date,
        includes_simulated,
        decline_threshold_percent=decline_threshold_percent,
    )


@router.get("/forecast", response_model=ForecastEnvelope, tags=["analytics"])
def forecast(
    request: Request,
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
    horizon_days: Annotated[int, Query(ge=1, le=14)] = 7,
):
    return analytical(
        "forecast", request, actor, db, start_date, end_date, includes_simulated, horizon_days
    )


@router.get("/recommendations/current", response_model=RecommendationEnvelope, tags=["analytics"])
def recommendation(
    request: Request,
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
):
    return analytical(
        "recommendation", request, actor, db, start_date, end_date, includes_simulated
    )


@router.get("/forecast/evaluation", response_model=EvaluationEnvelope, tags=["analytics"])
def forecast_evaluation(
    request: Request,
    actor: CurrentActor,
    db: Db,
    start_date: ReportDate,
    end_date: ReportDate,
    includes_simulated: bool = True,
):
    return analytical("evaluation", request, actor, db, start_date, end_date, includes_simulated)


@router.get("/summaries/daily", response_model=SummaryEnvelope, tags=["analytics"])
def summary(
    request: Request,
    actor: CurrentActor,
    db: Db,
    report_date: ReportDate,
    includes_simulated: bool = True,
    locale: Literal["en-IN", "hi-IN"] = "en-IN",
):
    return analytical(
        "summary", request, actor, db, report_date, report_date, includes_simulated, locale=locale
    )
