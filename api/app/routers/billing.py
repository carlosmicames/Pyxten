"""
Billing endpoints for Stripe subscription management
"""
import stripe
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.auth import get_current_user
from app.config import get_settings
from app.models import Subscription, StripeEvent
from app.schemas import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PortalSessionResponse,
    SubscriptionResponse,
    UserInfo,
)

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()

# Initialize Stripe with secret key
stripe.api_key = settings.stripe_secret_key


def _get_price_id(tier: str, period: str) -> str:
    """Map tier and period to Stripe Price ID from environment variables"""
    price_map = {
        ("professional", "monthly"): settings.stripe_price_professional_monthly,
        ("professional", "annual"): settings.stripe_price_professional_annual,
        ("empresarial", "monthly"): settings.stripe_price_empresarial_monthly,
        ("empresarial", "annual"): settings.stripe_price_empresarial_annual,
    }
    price_id = price_map.get((tier, period))
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier/period combination: {tier}/{period}",
        )
    return price_id


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription status"""
    subscription = db.query(Subscription).filter(Subscription.user_id == user.user_id).first()
    if not subscription:
        # Return default free tier if no subscription record exists
        return SubscriptionResponse(
            user_id=user.user_id,
            tier="free",
            status="inactive",
        )
    return subscription


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    data: CheckoutSessionRequest,
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for subscription"""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing service not configured",
        )

    price_id = _get_price_id(data.tier, data.period)

    try:
        # Check if user already has a stripe customer
        existing_sub = db.query(Subscription).filter(Subscription.user_id == user.user_id).first()
        customer_id = existing_sub.stripe_customer_id if existing_sub else None

        checkout_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{settings.app_url}/planes?success=1",
            "cancel_url": f"{settings.app_url}/planes?canceled=1",
            "client_reference_id": str(user.user_id),
            "metadata": {
                "user_id": str(user.user_id),
                "tier": data.tier,
                "period": data.period,
            },
        }

        # Use existing customer or set email for new customer
        if customer_id:
            checkout_params["customer"] = customer_id
        elif user.email:
            checkout_params["customer_email"] = user.email

        session = stripe.checkout.Session.create(**checkout_params)

        return CheckoutSessionResponse(url=session.url)

    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events (no auth required)"""
    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Idempotency check: skip if event already processed
    try:
        stripe_event = StripeEvent(event_id=event.id)
        db.add(stripe_event)
        db.commit()
    except IntegrityError:
        db.rollback()
        # Event already processed, return success
        return {"status": "already_processed"}

    # Handle different event types
    event_type = event.type
    data_object = event.data.object

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data_object, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data_object, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data_object, db)

    return {"status": "success"}


def _handle_checkout_completed(session, db: Session):
    """Handle successful checkout - create/update subscription"""
    # Extract user_id from metadata or client_reference_id
    user_id = session.metadata.get("user_id") or session.client_reference_id
    if not user_id:
        return  # Cannot process without user_id

    tier = session.metadata.get("tier", "professional")
    customer_id = session.customer
    subscription_id = session.subscription

    # Fetch subscription details from Stripe
    stripe_sub = stripe.Subscription.retrieve(subscription_id)

    # Upsert subscription record
    subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if subscription:
        subscription.tier = tier
        subscription.status = stripe_sub.status
        subscription.stripe_customer_id = customer_id
        subscription.stripe_subscription_id = subscription_id
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        )
        subscription.updated_at = datetime.now(timezone.utc)
    else:
        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            status=stripe_sub.status,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            current_period_end=datetime.fromtimestamp(
                stripe_sub.current_period_end, tz=timezone.utc
            ),
        )
        db.add(subscription)

    db.commit()


def _handle_subscription_updated(stripe_sub, db: Session):
    """Handle subscription updates (renewal, plan change, etc.)"""
    subscription_id = stripe_sub.id
    customer_id = stripe_sub.customer

    # Find subscription by stripe_subscription_id
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if not subscription:
        # Try to find by customer_id
        subscription = db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()

    if subscription:
        subscription.status = stripe_sub.status
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_sub.current_period_end, tz=timezone.utc
        )
        subscription.updated_at = datetime.now(timezone.utc)

        # Update tier from metadata if available
        if stripe_sub.metadata.get("tier"):
            subscription.tier = stripe_sub.metadata.get("tier")

        db.commit()


def _handle_subscription_deleted(stripe_sub, db: Session):
    """Handle subscription cancellation"""
    subscription_id = stripe_sub.id

    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()

    if subscription:
        subscription.status = "canceled"
        subscription.tier = "free"
        subscription.updated_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/create-portal-session", response_model=PortalSessionResponse)
def create_portal_session(
    user: UserInfo = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for managing subscription"""
    subscription = db.query(Subscription).filter(Subscription.user_id == user.user_id).first()

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe una suscripcion activa. Primero debe suscribirse a un plan.",
        )

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=f"{settings.app_url}/planes",
        )
        return PortalSessionResponse(url=portal_session.url)
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}",
        )
