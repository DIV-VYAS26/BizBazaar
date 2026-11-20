from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request

from app.core.errors import ApiError
from app.db.commerce import Customer, EmailOutbox, Product, ProfitOffer, RetentionCampaign, Sale
from app.routers.accounts import origin_guard
from app.routers.api import CurrentActor, Db, Limit, Offset, page
from app.schemas.accounts import ConsentInput
from app.schemas.api import MessageView, Page
from app.schemas.commerce import (
    CreditLedgerView,
    CreditPost,
    CustomerCreate,
    CustomerView,
    LoyaltyBalance,
    LoyaltySettings,
    OfferCreate,
    OfferEvaluate,
    OfferQuote,
    OfferView,
    OutboxView,
    PortalDecision,
    ProductCreate,
    ProductUpdate,
    ProductView,
    RetentionCreate,
    RetentionView,
    ReversalInput,
    SaleCreate,
    SaleView,
)
from app.services import catalog, credit, customers, loyalty, offers, retention, sales

router = APIRouter(tags=["merchant business"])


@router.get("/customers", response_model=Page[CustomerView])
def customer_list(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, Customer, actor, limit, offset, CustomerView)


@router.post("/customers", response_model=CustomerView, status_code=201)
def customer_create(payload: CustomerCreate, request: Request, actor: CurrentActor, db: Db):
    return customers.create_customer(db, actor, payload, request.app.state.settings)


@router.post("/customers/{customer_id}", response_model=CustomerView)
def customer_update(
    customer_id: UUID, payload: CustomerCreate, request: Request, actor: CurrentActor, db: Db
):
    return customers.update_customer(db, actor, customer_id, payload, request.app.state.settings)


@router.post("/customers/{customer_id}/portal-link", response_model=MessageView)
def portal_link(customer_id: UUID, request: Request, actor: CurrentActor, db: Db):
    return customers.customer_link(db, actor, customer_id, "PORTAL", request.app.state.settings)


@router.post("/customers/{customer_id}/consent-link", response_model=MessageView)
def consent_link(customer_id: UUID, request: Request, actor: CurrentActor, db: Db):
    return customers.customer_link(db, actor, customer_id, "CONSENT", request.app.state.settings)


@router.post("/customers/{customer_id}/marketing-revoke", response_model=CustomerView)
def revoke(customer_id: UUID, actor: CurrentActor, db: Db):
    return customers.revoke_consent(db, actor, customer_id)


@router.get("/products", response_model=Page[ProductView])
def product_list(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, Product, actor, limit, offset, ProductView)


@router.post("/products", response_model=ProductView, status_code=201)
def product_create(payload: ProductCreate, actor: CurrentActor, db: Db):
    return catalog.create_product(db, actor, payload)


@router.post("/products/{product_id}", response_model=ProductView)
def product_update(product_id: UUID, payload: ProductUpdate, actor: CurrentActor, db: Db):
    return catalog.update_product(db, actor, product_id, payload)


@router.get("/credit/{customer_id}", response_model=CreditLedgerView)
def credit_ledger(customer_id: UUID, actor: CurrentActor, db: Db):
    return credit.ledger(db, actor.merchant_id, customer_id)


@router.post("/credit/{customer_id}/charges", response_model=CreditLedgerView)
def charge(customer_id: UUID, payload: CreditPost, actor: CurrentActor, db: Db):
    return credit.post_credit(db, actor, customer_id, payload, "CHARGE")


@router.post("/credit/{customer_id}/repayments", response_model=CreditLedgerView)
def repayment(customer_id: UUID, payload: CreditPost, actor: CurrentActor, db: Db):
    return credit.post_credit(db, actor, customer_id, payload, "REPAYMENT")


@router.post("/credit/events/{event_id}/reverse", response_model=CreditLedgerView)
def reverse(event_id: UUID, payload: ReversalInput, actor: CurrentActor, db: Db):
    return credit.reverse_credit(db, actor, event_id, payload)


def bearer(authorization):
    if (
        not authorization
        or not authorization.startswith("Bearer ")
        or not 40 <= len(authorization[7:]) <= 100
    ):
        raise ApiError(401, "INVALID_CUSTOMER_LINK", "A private customer link is required")
    return authorization[7:]


Authorization = Annotated[str | None, Header(max_length=110)]


@router.get("/portal", response_model=CreditLedgerView)
def portal(db: Db, authorization: Authorization = None):
    return customers.portal_view(db, bearer(authorization))


@router.post("/portal/acknowledge", response_model=CreditLedgerView)
def acknowledge(
    payload: PortalDecision, request: Request, db: Db, authorization: Authorization = None
):
    origin_guard(request)
    return customers.record_customer_decision(db, bearer(authorization), payload)


@router.post("/public/consent", response_model=MessageView)
def consent(payload: ConsentInput, request: Request, db: Db):
    origin_guard(request)
    customers.confirm_consent(db, payload.token, payload.decision)
    return MessageView(message="Your marketing preference has been recorded")


@router.post("/offers/evaluate", response_model=OfferQuote)
def evaluate(payload: OfferEvaluate, actor: CurrentActor, db: Db):
    return offers.evaluate_offer(db, actor, payload)


@router.get("/offers", response_model=Page[OfferView])
def offer_list(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, ProfitOffer, actor, limit, offset, OfferView)


@router.post("/offers", response_model=OfferView, status_code=201)
def offer_create(payload: OfferCreate, actor: CurrentActor, db: Db):
    return offers.create_offer(db, actor, payload)


@router.post("/offers/{offer_id}/approve", response_model=OfferView)
def offer_approve(offer_id: UUID, actor: CurrentActor, db: Db):
    return offers.transition_offer(db, actor, offer_id, "approve")


@router.post("/offers/{offer_id}/activate", response_model=OfferView)
def offer_activate(offer_id: UUID, actor: CurrentActor, db: Db):
    return offers.transition_offer(db, actor, offer_id, "activate")


@router.post("/offers/{offer_id}/complete", response_model=OfferView)
def offer_complete(offer_id: UUID, actor: CurrentActor, db: Db):
    return offers.transition_offer(db, actor, offer_id, "complete")


@router.get("/sales", response_model=Page[SaleView])
def sale_list(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, Sale, actor, limit, offset, SaleView)


@router.post("/sales", response_model=SaleView, status_code=201)
def sale_create(payload: SaleCreate, actor: CurrentActor, db: Db):
    return sales.record_sale(db, actor, payload)


@router.post("/sales/{sale_id}/void", response_model=SaleView)
def sale_void(sale_id: UUID, payload: ReversalInput, actor: CurrentActor, db: Db):
    return sales.void_sale(db, actor, sale_id, payload)


@router.get("/loyalty/settings", response_model=LoyaltySettings)
def loyalty_policy(actor: CurrentActor, db: Db):
    return loyalty.get_policy(db, actor)


@router.post("/loyalty/settings", response_model=LoyaltySettings)
def loyalty_save(payload: LoyaltySettings, actor: CurrentActor, db: Db):
    return loyalty.save_policy(db, actor, payload)


@router.get("/loyalty/{customer_id}", response_model=LoyaltyBalance)
def loyalty_balance(customer_id: UUID, actor: CurrentActor, db: Db):
    return loyalty.get_loyalty(db, actor.merchant_id, customer_id)


@router.get("/retention/preview", response_model=list[CustomerView])
def retention_preview(
    actor: CurrentActor, db: Db, inactive_days: Annotated[int, Query(ge=7, le=365)] = 30
):
    return retention.eligible_customers(db, actor, inactive_days)


@router.get("/retention/campaigns", response_model=Page[RetentionView])
def retention_list(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, RetentionCampaign, actor, limit, offset, RetentionView)


@router.post("/retention/campaigns", response_model=RetentionView, status_code=201)
def retention_create(payload: RetentionCreate, actor: CurrentActor, db: Db):
    return retention.create_retention(db, actor, payload)


@router.post("/retention/campaigns/{campaign_id}/approve", response_model=RetentionView)
def retention_approve(campaign_id: UUID, request: Request, actor: CurrentActor, db: Db):
    return retention.retention_action(db, actor, campaign_id, "approve", request.app.state.settings)


@router.post("/retention/campaigns/{campaign_id}/queue", response_model=RetentionView)
def retention_queue(campaign_id: UUID, request: Request, actor: CurrentActor, db: Db):
    return retention.retention_action(db, actor, campaign_id, "queue", request.app.state.settings)


@router.get("/outbox", response_model=Page[OutboxView])
def outbox(actor: CurrentActor, db: Db, limit: Limit = 20, offset: Offset = 0):
    return page(db, EmailOutbox, actor, limit, offset, OutboxView)
