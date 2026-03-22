import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Literal, Optional
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, Field
import requests
from starlette.middleware.cors import CORSMiddleware


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

DEFAULT_ADMIN_EMAIL = "admin@dialforhelp.com"
DEFAULT_ADMIN_PASSWORD = "Admin@123"

USER_PLAN_PRICE_INR = 99
WORKER_PLAN_PRICE_INR = 199
USER_PLAN_PRICE_PAISE = USER_PLAN_PRICE_INR * 100
WORKER_PLAN_PRICE_PAISE = WORKER_PLAN_PRICE_INR * 100

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Dial For Help API")
api_router = APIRouter(prefix="/api")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(phone: str) -> str:
    return phone.strip().replace(" ", "")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_identity_key(phone: str, email: str) -> str:
    return f"{normalize_phone(phone)}::{normalize_email(email)}"


def get_plan_amount_paise(plan_type: str) -> int:
    return USER_PLAN_PRICE_PAISE if plan_type == "user" else WORKER_PLAN_PRICE_PAISE


class NotificationLog(BaseModel):
    channel: Literal["sms", "email"]
    recipient: str
    success: bool
    detail: str
    timestamp: str


class BookingCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    service_type: Literal[
        "Plumbing",
        "Electrical",
        "Cleaning",
        "General Handyman",
        "AC Repair",
        "Carpentry",
        "Painting",
        "Pest Control",
        "Appliance Repair",
        "Deep Cleaning",
        "Salon at Home",
        "RO Service",
        "CCTV Installation",
        "Movers & Packers",
        "Gardening",
        "Other",
    ]
    address: str = Field(min_length=5, max_length=220)
    preferred_date: str
    notes: str = Field(default="", max_length=800)


class BookingResponse(BookingCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    status: Literal["pending", "assigned", "completed"]
    assigned_worker_id: Optional[str] = None
    identity_key: str
    charge_type: Literal["free", "subscription"]
    created_at: str
    updated_at: str
    notification_log: List[NotificationLog] = Field(default_factory=list)


class WorkerSignupCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    skill: Literal[
        "Plumbing",
        "Electrical",
        "Cleaning",
        "General Handyman",
        "AC Repair",
        "Carpentry",
        "Painting",
        "Pest Control",
        "Appliance Repair",
        "Deep Cleaning",
        "Salon at Home",
        "RO Service",
        "CCTV Installation",
        "Movers & Packers",
        "Gardening",
    ]
    city: str = Field(min_length=2, max_length=80)
    years_experience: int = Field(ge=0, le=60)
    availability: Literal["Full-time", "Part-time", "Weekends"]
    about: str = Field(default="", max_length=600)


class WorkerResponse(WorkerSignupCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    joined_at: str
    is_active: bool
    subscription_expires_at: Optional[str] = None


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    message: str = Field(min_length=5, max_length=1000)


class ContactResponse(ContactCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: str


class UserRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: str = Field(min_length=7, max_length=20)
    address: str = Field(default="", max_length=220)
    notify_email: bool = True
    notify_sms: bool = True


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserProfileResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    phone: str
    address: str
    notify_email: bool
    notify_sms: bool
    created_at: str
    updated_at: str


class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    address: Optional[str] = Field(default=None, max_length=220)
    notify_email: Optional[bool] = None
    notify_sms: Optional[bool] = None


class UserAuthResponse(BaseModel):
    token: str
    expires_at: str
    user: UserProfileResponse


class UserNotificationItem(BaseModel):
    id: str
    title: str
    message: str
    category: str
    booking_id: Optional[str] = None
    read: bool
    created_at: str


class RenewalDispatchResponse(BaseModel):
    reminded_count: int
    message: str


class AdminDemoActionResponse(BaseModel):
    message: str
    deleted_records: int


class MonthlyAnalyticsItem(BaseModel):
    month: str
    bookings: int
    revenue_inr: int
    renewals_due: int


class AdminAnalyticsResponse(BaseModel):
    monthly: List[MonthlyAnalyticsItem]
    assignment_completion_rate: float
    active_subscriptions: int
    total_revenue_inr: int


class DemoLoginItem(BaseModel):
    role: str
    full_name: str
    email: str
    phone: str
    login_password: Optional[str] = None


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class AdminLoginResponse(BaseModel):
    token: str
    admin_email: EmailStr
    expires_at: str


class BookingStatusUpdate(BaseModel):
    status: Literal["pending", "assigned", "completed"]
    assigned_worker_id: Optional[str] = None


class DashboardStats(BaseModel):
    pending: int
    assigned: int
    completed: int
    total_workers: int
    total_contacts: int


class AdminOverviewResponse(BaseModel):
    stats: DashboardStats
    bookings: List[BookingResponse]
    workers: List[WorkerResponse]
    contacts: List[ContactResponse]


class SubscriptionStatusResponse(BaseModel):
    identity_key: str
    bookings_used: int
    free_remaining: int
    has_active_subscription: bool
    requires_subscription: bool
    subscription_expires_at: Optional[str] = None


class WorkerSubscriptionStatusResponse(BaseModel):
    subscriber_key: str
    has_active_subscription: bool
    subscription_expires_at: Optional[str] = None


class PaymentCreateOrderRequest(BaseModel):
    plan_type: Literal["user", "worker"]
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)


class PaymentCreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str
    plan_type: Literal["user", "worker"]
    amount_inr: int


class PaymentVerifyRequest(BaseModel):
    plan_type: Literal["user", "worker"]
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    subscriber_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)


class PaymentVerifyResponse(BaseModel):
    message: str
    plan_type: Literal["user", "worker"]
    active_until: str


class BookingTrackingResponse(BaseModel):
    booking_id: str
    customer_name: str
    service_type: str
    status: str
    preferred_date: str
    created_at: str
    charge_type: str
    assigned_worker_name: Optional[str] = None


class WorkerSuggestion(BaseModel):
    worker_id: str
    full_name: str
    skill: str
    availability: str
    score: int


class AdminSubscriptionItem(BaseModel):
    id: str
    plan_type: str
    subscriber_name: str
    email: str
    phone: str
    status: str
    started_at: str
    expires_at: str
    days_remaining: int
    renewal_reminder_due: bool


def _coerce_booking_doc(document: dict) -> dict:
    document.setdefault("identity_key", get_identity_key(document["phone"], document["email"]))
    document.setdefault("charge_type", "free")
    document.setdefault("notification_log", [])
    document.setdefault("assigned_worker_id", None)
    return document


def _coerce_worker_doc(document: dict) -> dict:
    document.setdefault("subscription_expires_at", None)
    return document


def _coerce_user_doc(document: dict) -> dict:
    return {
        "id": document["id"],
        "full_name": document.get("full_name", ""),
        "email": document.get("email", ""),
        "phone": document.get("phone", ""),
        "address": document.get("address", ""),
        "notify_email": document.get("notify_email", True),
        "notify_sms": document.get("notify_sms", True),
        "created_at": document.get("created_at", now_iso()),
        "updated_at": document.get("updated_at", now_iso()),
    }


def _send_sms_message(phone_number: str, message: str) -> NotificationLog:
    fast2sms_api_key = os.environ.get("FAST2SMS_API_KEY")
    if fast2sms_api_key:
        sender_id = os.environ.get("FAST2SMS_SENDER_ID", "FSTSMS")
        cleaned_number = normalize_phone(phone_number).replace("+", "")
        try:
            response = requests.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={
                    "authorization": fast2sms_api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Cache-Control": "no-cache",
                },
                data={
                    "route": "q",
                    "sender_id": sender_id,
                    "message": message,
                    "language": "english",
                    "numbers": cleaned_number,
                },
                timeout=15,
            )
            response_data = response.json() if response.content else {}
            success = bool(response_data.get("return", False))
            error_text = response_data.get("message") or response_data.get("error") or ""
            if success:
                return NotificationLog(
                    channel="sms",
                    recipient=phone_number,
                    success=True,
                    detail="SMS sent via Fast2SMS",
                    timestamp=now_iso(),
                )
            return NotificationLog(
                channel="sms",
                recipient=phone_number,
                success=False,
                detail=f"Fast2SMS error {response.status_code}: {error_text}",
                timestamp=now_iso(),
            )
        except Exception as exc:  # noqa: BLE001
            return NotificationLog(
                channel="sms",
                recipient=phone_number,
                success=False,
                detail=f"Fast2SMS request failed: {str(exc)}",
                timestamp=now_iso(),
            )

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")

    if not account_sid or not auth_token or not from_number:
        return NotificationLog(
            channel="sms",
            recipient=phone_number,
            success=False,
            detail="Twilio is not configured yet",
            timestamp=now_iso(),
        )

    twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        response = requests.post(
            twilio_url,
            data={"To": phone_number, "From": from_number, "Body": message},
            auth=(account_sid, auth_token),
            timeout=15,
        )
        if response.status_code < 300:
            return NotificationLog(
                channel="sms",
                recipient=phone_number,
                success=True,
                detail="SMS sent",
                timestamp=now_iso(),
            )
        return NotificationLog(
            channel="sms",
            recipient=phone_number,
            success=False,
            detail=f"Twilio error {response.status_code}",
            timestamp=now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        return NotificationLog(
            channel="sms",
            recipient=phone_number,
            success=False,
            detail=f"Twilio request failed: {str(exc)}",
            timestamp=now_iso(),
        )


async def _create_user_notification(
    email: str,
    phone: str,
    title: str,
    message: str,
    category: str,
    booking_id: Optional[str] = None,
) -> None:
    notification_doc = {
        "id": str(uuid.uuid4()),
        "email": normalize_email(email),
        "phone": normalize_phone(phone),
        "title": title,
        "message": message,
        "category": category,
        "booking_id": booking_id,
        "read": False,
        "created_at": now_iso(),
    }
    await db.user_notifications.insert_one(notification_doc)


def _send_email_message(recipient: str, subject: str, body_text: str) -> NotificationLog:
    sendgrid_api_key = os.environ.get("SENDGRID_API_KEY")
    sendgrid_from_email = os.environ.get("SENDGRID_FROM_EMAIL")

    if not sendgrid_api_key or not sendgrid_from_email:
        return NotificationLog(
            channel="email",
            recipient=recipient,
            success=False,
            detail="SendGrid is not configured yet",
            timestamp=now_iso(),
        )

    payload = {
        "personalizations": [{"to": [{"email": recipient}]}],
        "from": {"email": sendgrid_from_email},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body_text}],
    }

    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if response.status_code in {200, 202}:
            return NotificationLog(
                channel="email",
                recipient=recipient,
                success=True,
                detail="Email sent",
                timestamp=now_iso(),
            )
        return NotificationLog(
            channel="email",
            recipient=recipient,
            success=False,
            detail=f"SendGrid error {response.status_code}",
            timestamp=now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        return NotificationLog(
            channel="email",
            recipient=recipient,
            success=False,
            detail=f"SendGrid request failed: {str(exc)}",
            timestamp=now_iso(),
        )


async def _notify_booking_event(booking: BookingResponse, event_title: str) -> List[NotificationLog]:
    logs: List[NotificationLog] = []
    admin_email = os.environ.get("ADMIN_NOTIFY_EMAIL")
    admin_phone = os.environ.get("ADMIN_NOTIFY_PHONE")

    email_targets = [booking.email]
    if admin_email and admin_email not in email_targets:
        email_targets.append(admin_email)

    sms_targets = [booking.phone]
    if admin_phone and admin_phone not in sms_targets:
        sms_targets.append(admin_phone)

    email_subject = f"Dial For Help: {event_title}"
    email_body = (
        f"Booking ID: {booking.id}\n"
        f"Customer: {booking.full_name}\n"
        f"Service: {booking.service_type}\n"
        f"Status: {booking.status}\n"
        f"Preferred Date: {booking.preferred_date}\n"
    )
    sms_body = (
        f"Dial For Help update: {event_title}. "
        f"Booking {booking.id[:8]} | {booking.service_type} | Status: {booking.status}."
    )

    tasks = [
        asyncio.to_thread(_send_email_message, email, email_subject, email_body)
        for email in email_targets
    ]
    tasks.extend(
        [asyncio.to_thread(_send_sms_message, phone, sms_body) for phone in sms_targets]
    )

    if tasks:
        logs = await asyncio.gather(*tasks)

    return logs


def _create_razorpay_order(amount_paise: int, receipt: str, notes: dict) -> dict:
    razorpay_key_id = os.environ.get("RAZORPAY_KEY_ID")
    razorpay_key_secret = os.environ.get("RAZORPAY_KEY_SECRET")

    if not razorpay_key_id or not razorpay_key_secret:
        raise HTTPException(status_code=500, detail="Razorpay credentials missing")

    response = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(razorpay_key_id, razorpay_key_secret),
        json={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt[:40],
            "payment_capture": 1,
            "notes": notes,
        },
        timeout=20,
    )

    if response.status_code >= 300:
        raise HTTPException(status_code=502, detail="Could not create Razorpay order")

    return response.json()


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    razorpay_key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
    if not razorpay_key_secret:
        raise HTTPException(status_code=500, detail="Razorpay credentials missing")

    body = f"{order_id}|{payment_id}".encode("utf-8")
    generated_signature = hmac.new(
        razorpay_key_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(generated_signature, signature)


def _subscription_is_active(subscription: Optional[dict]) -> bool:
    if not subscription:
        return False

    expires_at = subscription.get("expires_at")
    if not expires_at:
        return False

    try:
        return datetime.fromisoformat(expires_at) > datetime.now(timezone.utc)
    except ValueError:
        return False


def _days_remaining(iso_datetime: str) -> int:
    try:
        expiry = datetime.fromisoformat(iso_datetime)
    except ValueError:
        return 0

    remaining = expiry - datetime.now(timezone.utc)
    return max(0, remaining.days)


def _parse_iso(iso_value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(iso_value)
    except ValueError:
        return None


def _month_bucket(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _last_month_buckets(count: int = 6) -> List[str]:
    current = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    buckets = []
    for offset in range(count - 1, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        buckets.append(f"{year:04d}-{month:02d}")
    return buckets


async def _reset_demo_data() -> int:
    demo_email_filter = {"$regex": "@dialhelp\\.demo$", "$options": "i"}

    user_docs = await db.users.find({"email": demo_email_filter}, {"_id": 0, "email": 1}).to_list(5000)
    worker_docs = await db.workers.find({"email": demo_email_filter}, {"_id": 0, "email": 1}).to_list(5000)

    demo_emails = list({doc["email"] for doc in user_docs + worker_docs if doc.get("email")})
    deleted_records = 0

    if demo_emails:
        deleted_records += (await db.user_sessions.delete_many({"user_email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.users.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.workers.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.bookings.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.contacts.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.user_notifications.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.subscriptions.delete_many({"email": {"$in": demo_emails}})).deleted_count
        deleted_records += (await db.payment_orders.delete_many({"email": {"$in": demo_emails}})).deleted_count

    return deleted_records


async def _get_active_subscription(phone: str, email: str, plan_type: Literal["user", "worker"]) -> Optional[dict]:
    subscriber_key = get_identity_key(phone, email)
    subscription = await db.subscriptions.find_one(
        {
            "subscriber_key": subscriber_key,
            "plan_type": plan_type,
            "status": "active",
        },
        {"_id": 0},
    )
    if _subscription_is_active(subscription):
        return subscription
    return None


async def _build_user_subscription_status(phone: str, email: str) -> dict:
    identity_key = get_identity_key(phone, email)
    bookings_used = await db.bookings.count_documents({"identity_key": identity_key})
    subscription = await _get_active_subscription(phone, email, "user")

    free_remaining = max(0, 2 - bookings_used)
    has_active_subscription = subscription is not None
    requires_subscription = bookings_used >= 2 and not has_active_subscription

    return {
        "identity_key": identity_key,
        "bookings_used": bookings_used,
        "free_remaining": free_remaining,
        "has_active_subscription": has_active_subscription,
        "requires_subscription": requires_subscription,
        "subscription_expires_at": subscription["expires_at"] if subscription else None,
    }


async def _ensure_default_admin() -> None:
    existing = await db.admins.find_one({"email": DEFAULT_ADMIN_EMAIL}, {"_id": 0})
    if existing:
        return

    admin_doc = {
        "id": str(uuid.uuid4()),
        "email": DEFAULT_ADMIN_EMAIL,
        "password_hash": pwd_context.hash(DEFAULT_ADMIN_PASSWORD),
        "created_at": now_iso(),
    }
    await db.admins.insert_one(dict(admin_doc))
    logger.info("Default admin account initialized")


async def _get_admin_session(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin token",
        )

    token = authorization.replace("Bearer ", "", 1).strip()
    session = await db.admin_sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at <= datetime.now(timezone.utc):
        await db.admin_sessions.delete_one({"token": token})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token expired",
        )

    return session


async def _get_user_session(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing user token",
        )

    token = authorization.replace("Bearer ", "", 1).strip()
    session = await db.user_sessions.find_one({"token": token}, {"_id": 0})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user token",
        )

    expires_at = datetime.fromisoformat(session["expires_at"])
    if expires_at <= datetime.now(timezone.utc):
        await db.user_sessions.delete_one({"token": token})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User token expired",
        )

    return session


@api_router.get("/")
async def root():
    return {
        "message": "Dial For Help API is running",
        "plans": {
            "user": f"₹{USER_PLAN_PRICE_INR}/year after 2 free services",
            "worker": f"₹{WORKER_PLAN_PRICE_INR}/year mandatory before signup",
        },
    }


@api_router.get("/subscriptions/user-status", response_model=SubscriptionStatusResponse)
async def user_subscription_status(
    phone: str = Query(..., min_length=7),
    email: EmailStr = Query(...),
):
    status_data = await _build_user_subscription_status(phone, str(email))
    return SubscriptionStatusResponse(**status_data)


@api_router.get("/subscriptions/worker-status", response_model=WorkerSubscriptionStatusResponse)
async def worker_subscription_status(
    phone: str = Query(..., min_length=7),
    email: EmailStr = Query(...),
):
    subscription = await _get_active_subscription(phone, str(email), "worker")
    return WorkerSubscriptionStatusResponse(
        subscriber_key=get_identity_key(phone, str(email)),
        has_active_subscription=subscription is not None,
        subscription_expires_at=subscription["expires_at"] if subscription else None,
    )


@api_router.post("/payments/create-order", response_model=PaymentCreateOrderResponse)
async def create_payment_order(payload: PaymentCreateOrderRequest):
    amount_paise = get_plan_amount_paise(payload.plan_type)
    amount_inr = USER_PLAN_PRICE_INR if payload.plan_type == "user" else WORKER_PLAN_PRICE_INR

    receipt = f"{payload.plan_type[:1]}_{uuid.uuid4().hex[:18]}"
    subscriber_key = get_identity_key(payload.phone, str(payload.email))
    order = _create_razorpay_order(
        amount_paise=amount_paise,
        receipt=receipt,
        notes={"plan_type": payload.plan_type, "subscriber_key": subscriber_key},
    )

    order_doc = {
        "id": str(uuid.uuid4()),
        "order_id": order["id"],
        "plan_type": payload.plan_type,
        "subscriber_name": payload.name,
        "email": str(payload.email),
        "phone": payload.phone,
        "subscriber_key": subscriber_key,
        "amount": amount_paise,
        "currency": order.get("currency", "INR"),
        "status": "created",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.payment_orders.insert_one(order_doc)

    razorpay_key_id = os.environ.get("RAZORPAY_KEY_ID")
    if not razorpay_key_id:
        raise HTTPException(status_code=500, detail="Razorpay key not configured")

    return PaymentCreateOrderResponse(
        order_id=order["id"],
        amount=amount_paise,
        currency=order.get("currency", "INR"),
        key_id=razorpay_key_id,
        plan_type=payload.plan_type,
        amount_inr=amount_inr,
    )


@api_router.post("/payments/verify", response_model=PaymentVerifyResponse)
async def verify_payment(payload: PaymentVerifyRequest):
    is_valid = _verify_razorpay_signature(
        payload.razorpay_order_id,
        payload.razorpay_payment_id,
        payload.razorpay_signature,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    payment_order = await db.payment_orders.find_one(
        {"order_id": payload.razorpay_order_id, "plan_type": payload.plan_type},
        {"_id": 0},
    )
    if not payment_order:
        raise HTTPException(status_code=404, detail="Payment order not found")

    started_at = datetime.now(timezone.utc)
    expires_at = started_at + timedelta(days=365)
    amount_inr = USER_PLAN_PRICE_INR if payload.plan_type == "user" else WORKER_PLAN_PRICE_INR

    subscriber_key = get_identity_key(payload.phone, str(payload.email))
    subscription_doc = {
        "id": str(uuid.uuid4()),
        "subscriber_key": subscriber_key,
        "subscriber_name": payload.subscriber_name,
        "email": str(payload.email),
        "phone": payload.phone,
        "plan_type": payload.plan_type,
        "amount_inr": amount_inr,
        "status": "active",
        "started_at": started_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "razorpay_order_id": payload.razorpay_order_id,
        "razorpay_payment_id": payload.razorpay_payment_id,
        "updated_at": now_iso(),
    }

    await db.subscriptions.update_one(
        {"subscriber_key": subscriber_key, "plan_type": payload.plan_type},
        {"$set": subscription_doc},
        upsert=True,
    )

    await db.payment_orders.update_one(
        {"order_id": payload.razorpay_order_id},
        {
            "$set": {
                "status": "paid",
                "razorpay_payment_id": payload.razorpay_payment_id,
                "updated_at": now_iso(),
            }
        },
    )

    return PaymentVerifyResponse(
        message="Subscription activated",
        plan_type=payload.plan_type,
        active_until=expires_at.isoformat(),
    )


@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(payload: BookingCreate):
    subscription_status = await _build_user_subscription_status(payload.phone, str(payload.email))
    if subscription_status["requires_subscription"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "USER_SUBSCRIPTION_REQUIRED",
                "message": f"First 2 services are free. Please subscribe for ₹{USER_PLAN_PRICE_INR}/year to continue.",
                "free_remaining": 0,
                "required_amount_inr": USER_PLAN_PRICE_INR,
            },
        )

    timestamp = now_iso()
    charge_type = "subscription" if subscription_status["has_active_subscription"] else "free"
    booking = BookingResponse(
        id=str(uuid.uuid4()),
        status="pending",
        assigned_worker_id=None,
        identity_key=subscription_status["identity_key"],
        charge_type=charge_type,
        created_at=timestamp,
        updated_at=timestamp,
        notification_log=[],
        **payload.model_dump(),
    )
    booking_doc = booking.model_dump()
    await db.bookings.insert_one(dict(booking_doc))

    await _create_user_notification(
        email=str(payload.email),
        phone=payload.phone,
        title="Booking received",
        message=f"Your booking for {payload.service_type} is received and currently pending.",
        category="booking",
        booking_id=booking.id,
    )

    notification_log = await _notify_booking_event(booking, "Booking received")
    if notification_log:
        updated_at = now_iso()
        await db.bookings.update_one(
            {"id": booking.id},
            {
                "$set": {
                    "notification_log": [item.model_dump() for item in notification_log],
                    "updated_at": updated_at,
                }
            },
        )
        booking.notification_log = notification_log
        booking.updated_at = updated_at

    return booking


@api_router.get("/bookings/track/{booking_id}", response_model=BookingTrackingResponse)
async def track_booking(booking_id: str):
    booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking ID not found")

    booking = BookingResponse(**_coerce_booking_doc(booking_doc))
    assigned_worker_name = None
    if booking.assigned_worker_id:
        worker = await db.workers.find_one({"id": booking.assigned_worker_id}, {"_id": 0})
        if worker:
            assigned_worker_name = worker.get("full_name")

    return BookingTrackingResponse(
        booking_id=booking.id,
        customer_name=booking.full_name,
        service_type=booking.service_type,
        status=booking.status,
        preferred_date=booking.preferred_date,
        created_at=booking.created_at,
        charge_type=booking.charge_type,
        assigned_worker_name=assigned_worker_name,
    )


@api_router.post("/workers/signup", response_model=WorkerResponse)
async def worker_signup(payload: WorkerSignupCreate):
    active_worker_subscription = await _get_active_subscription(payload.phone, str(payload.email), "worker")
    if not active_worker_subscription:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "WORKER_SUBSCRIPTION_REQUIRED",
                "message": f"Worker subscription of ₹{WORKER_PLAN_PRICE_INR}/year is mandatory before signup.",
                "required_amount_inr": WORKER_PLAN_PRICE_INR,
            },
        )

    worker = WorkerResponse(
        id=str(uuid.uuid4()),
        joined_at=now_iso(),
        is_active=True,
        subscription_expires_at=active_worker_subscription["expires_at"],
        **payload.model_dump(),
    )
    await db.workers.insert_one(worker.model_dump())
    return worker


@api_router.post("/contacts", response_model=ContactResponse)
async def create_contact(payload: ContactCreate):
    contact = ContactResponse(
        id=str(uuid.uuid4()),
        created_at=now_iso(),
        **payload.model_dump(),
    )
    await db.contacts.insert_one(contact.model_dump())
    return contact


@api_router.post("/users/register", response_model=UserAuthResponse)
async def user_register(payload: UserRegisterRequest):
    existing = await db.users.find_one({"email": normalize_email(str(payload.email))}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")

    timestamp = now_iso()
    user_doc = {
        "id": str(uuid.uuid4()),
        "full_name": payload.full_name,
        "email": normalize_email(str(payload.email)),
        "password_hash": pwd_context.hash(payload.password),
        "phone": normalize_phone(payload.phone),
        "address": payload.address,
        "notify_email": payload.notify_email,
        "notify_sms": payload.notify_sms,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await db.users.insert_one(dict(user_doc))

    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    await db.user_sessions.insert_one(
        {
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user_doc["id"],
            "user_email": user_doc["email"],
            "expires_at": expires_at,
            "created_at": now_iso(),
        }
    )

    return UserAuthResponse(
        token=token,
        expires_at=expires_at,
        user=UserProfileResponse(**_coerce_user_doc(user_doc)),
    )


@api_router.post("/users/login", response_model=UserAuthResponse)
async def user_login(payload: UserLoginRequest):
    user = await db.users.find_one({"email": normalize_email(str(payload.email))}, {"_id": 0})
    if not user or not pwd_context.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid user credentials")

    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    await db.user_sessions.insert_one(
        {
            "id": str(uuid.uuid4()),
            "token": token,
            "user_id": user["id"],
            "user_email": user["email"],
            "expires_at": expires_at,
            "created_at": now_iso(),
        }
    )

    return UserAuthResponse(
        token=token,
        expires_at=expires_at,
        user=UserProfileResponse(**_coerce_user_doc(user)),
    )


@api_router.post("/users/logout")
async def user_logout(session: dict = Depends(_get_user_session)):
    await db.user_sessions.delete_one({"token": session["token"]})
    return {"message": "User logged out"}


@api_router.get("/users/profile", response_model=UserProfileResponse)
async def get_user_profile(session: dict = Depends(_get_user_session)):
    user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfileResponse(**_coerce_user_doc(user))


@api_router.put("/users/profile", response_model=UserProfileResponse)
async def update_user_profile(
    payload: UserProfileUpdateRequest,
    session: dict = Depends(_get_user_session),
):
    update_fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_fields:
        user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserProfileResponse(**_coerce_user_doc(user))

    if "phone" in update_fields:
        update_fields["phone"] = normalize_phone(update_fields["phone"])
    update_fields["updated_at"] = now_iso()

    await db.users.update_one({"id": session["user_id"]}, {"$set": update_fields})
    user = await db.users.find_one({"id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(**_coerce_user_doc(user))


@api_router.get("/users/bookings", response_model=List[BookingResponse])
async def get_user_bookings(session: dict = Depends(_get_user_session)):
    bookings = await db.bookings.find(
        {"email": normalize_email(session["user_email"])},
        {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    return [BookingResponse(**_coerce_booking_doc(item)) for item in bookings]


@api_router.get("/users/notifications", response_model=List[UserNotificationItem])
async def get_user_notifications(session: dict = Depends(_get_user_session)):
    notifications = await db.user_notifications.find(
        {"email": normalize_email(session["user_email"])},
        {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    return [UserNotificationItem(**item) for item in notifications]


@api_router.patch("/users/notifications/{notification_id}/read", response_model=UserNotificationItem)
async def mark_user_notification_read(
    notification_id: str,
    session: dict = Depends(_get_user_session),
):
    await db.user_notifications.update_one(
        {
            "id": notification_id,
            "email": normalize_email(session["user_email"]),
        },
        {"$set": {"read": True}},
    )
    notification = await db.user_notifications.find_one(
        {
            "id": notification_id,
            "email": normalize_email(session["user_email"]),
        },
        {"_id": 0},
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return UserNotificationItem(**notification)


@api_router.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(payload: AdminLoginRequest):
    admin = await db.admins.find_one({"email": payload.email}, {"_id": 0})
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not pwd_context.verify(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = str(uuid.uuid4())
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
    await db.admin_sessions.insert_one(
        {
            "id": str(uuid.uuid4()),
            "token": token,
            "admin_email": payload.email,
            "expires_at": expires_at,
            "created_at": now_iso(),
        }
    )

    return AdminLoginResponse(token=token, admin_email=payload.email, expires_at=expires_at)


@api_router.post("/admin/logout")
async def admin_logout(session: dict = Depends(_get_admin_session)):
    await db.admin_sessions.delete_one({"token": session["token"]})
    return {"message": "Logged out"}


@api_router.get("/admin/overview", response_model=AdminOverviewResponse)
async def admin_overview(_: dict = Depends(_get_admin_session)):
    bookings = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(400)
    workers = await db.workers.find({}, {"_id": 0}).sort("joined_at", -1).to_list(400)
    contacts = await db.contacts.find({}, {"_id": 0}).sort("created_at", -1).to_list(400)

    booking_items = [BookingResponse(**_coerce_booking_doc(item)) for item in bookings]
    worker_items = [WorkerResponse(**_coerce_worker_doc(item)) for item in workers]
    contact_items = [ContactResponse(**item) for item in contacts]

    stats = DashboardStats(
        pending=len([item for item in booking_items if item.status == "pending"]),
        assigned=len([item for item in booking_items if item.status == "assigned"]),
        completed=len([item for item in booking_items if item.status == "completed"]),
        total_workers=len(worker_items),
        total_contacts=len(contact_items),
    )

    return AdminOverviewResponse(
        stats=stats,
        bookings=booking_items,
        workers=worker_items,
        contacts=contact_items,
    )


@api_router.get("/admin/subscriptions", response_model=List[AdminSubscriptionItem])
async def admin_subscriptions(_: dict = Depends(_get_admin_session)):
    subscriptions = await db.subscriptions.find({}, {"_id": 0}).sort("expires_at", 1).to_list(1000)
    items: List[AdminSubscriptionItem] = []

    for entry in subscriptions:
        expires_at = entry.get("expires_at", now_iso())
        days_remaining = _days_remaining(expires_at)
        items.append(
            AdminSubscriptionItem(
                id=entry.get("id", str(uuid.uuid4())),
                plan_type=entry.get("plan_type", "unknown"),
                subscriber_name=entry.get("subscriber_name", "Unknown"),
                email=entry.get("email", ""),
                phone=entry.get("phone", ""),
                status=entry.get("status", "inactive"),
                started_at=entry.get("started_at", now_iso()),
                expires_at=expires_at,
                days_remaining=days_remaining,
                renewal_reminder_due=days_remaining <= 7,
            )
        )

    return items


@api_router.get("/admin/analytics", response_model=AdminAnalyticsResponse)
async def admin_analytics(_: dict = Depends(_get_admin_session)):
    month_buckets = _last_month_buckets(6)
    monthly_map = {
        bucket: {"bookings": 0, "revenue_inr": 0, "renewals_due": 0}
        for bucket in month_buckets
    }

    bookings = await db.bookings.find({}, {"_id": 0, "created_at": 1, "status": 1}).to_list(5000)
    subscriptions = await db.subscriptions.find(
        {},
        {"_id": 0, "started_at": 1, "expires_at": 1, "amount_inr": 1, "status": 1},
    ).to_list(5000)

    completed_count = 0
    assigned_or_completed_count = 0

    for booking in bookings:
        created_dt = _parse_iso(booking.get("created_at", ""))
        if created_dt:
            bucket = _month_bucket(created_dt)
            if bucket in monthly_map:
                monthly_map[bucket]["bookings"] += 1

        if booking.get("status") in {"assigned", "completed"}:
            assigned_or_completed_count += 1
        if booking.get("status") == "completed":
            completed_count += 1

    active_subscriptions = 0
    total_revenue = 0
    now = datetime.now(timezone.utc)
    for subscription in subscriptions:
        started_dt = _parse_iso(subscription.get("started_at", ""))
        expires_dt = _parse_iso(subscription.get("expires_at", ""))
        amount = int(subscription.get("amount_inr", 0) or 0)

        if started_dt:
            bucket = _month_bucket(started_dt)
            if bucket in monthly_map:
                monthly_map[bucket]["revenue_inr"] += amount

        if expires_dt:
            bucket = _month_bucket(expires_dt)
            if bucket in monthly_map:
                monthly_map[bucket]["renewals_due"] += 1

        if subscription.get("status") == "active" and expires_dt and expires_dt > now:
            active_subscriptions += 1
            total_revenue += amount

    assignment_completion_rate = (
        (completed_count / assigned_or_completed_count) * 100
        if assigned_or_completed_count
        else 0.0
    )

    monthly_items = [
        MonthlyAnalyticsItem(
            month=bucket,
            bookings=monthly_map[bucket]["bookings"],
            revenue_inr=monthly_map[bucket]["revenue_inr"],
            renewals_due=monthly_map[bucket]["renewals_due"],
        )
        for bucket in month_buckets
    ]

    return AdminAnalyticsResponse(
        monthly=monthly_items,
        assignment_completion_rate=round(assignment_completion_rate, 2),
        active_subscriptions=active_subscriptions,
        total_revenue_inr=total_revenue,
    )


@api_router.get("/admin/demo-logins", response_model=List[DemoLoginItem])
async def admin_demo_logins(_: dict = Depends(_get_admin_session)):
    demo_email_filter = {"$regex": "@dialhelp\\.demo$", "$options": "i"}
    users = await db.users.find(
        {"email": demo_email_filter},
        {"_id": 0, "full_name": 1, "email": 1, "phone": 1},
    ).sort("created_at", -1).to_list(30)
    workers = await db.workers.find(
        {"email": demo_email_filter},
        {"_id": 0, "full_name": 1, "email": 1, "phone": 1},
    ).sort("joined_at", -1).to_list(30)

    items = [
        DemoLoginItem(
            role="admin",
            full_name="Default Admin",
            email=DEFAULT_ADMIN_EMAIL,
            phone="N/A",
            login_password=DEFAULT_ADMIN_PASSWORD,
        )
    ]

    for user in users[:12]:
        items.append(
            DemoLoginItem(
                role="user",
                full_name=user.get("full_name", "Demo User"),
                email=user.get("email", ""),
                phone=user.get("phone", ""),
                login_password="User@123",
            )
        )

    for worker in workers[:12]:
        items.append(
            DemoLoginItem(
                role="worker-reference",
                full_name=worker.get("full_name", "Demo Worker"),
                email=worker.get("email", ""),
                phone=worker.get("phone", ""),
                login_password=None,
            )
        )

    return items


@api_router.post("/admin/demo/reset", response_model=AdminDemoActionResponse)
async def admin_reset_demo_data(_: dict = Depends(_get_admin_session)):
    deleted_records = await _reset_demo_data()
    return AdminDemoActionResponse(
        message="Demo records cleared",
        deleted_records=deleted_records,
    )


@api_router.post("/admin/demo/reset-reseed", response_model=AdminDemoActionResponse)
async def admin_reset_reseed_demo(_: dict = Depends(_get_admin_session)):
    deleted_records = await _reset_demo_data()

    try:
        run_result = subprocess.run(
            [sys.executable, "/app/scripts/seed_demo_data.py"],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        message = f"Reset + reseed completed. {run_result.stdout.strip()}"
    except subprocess.CalledProcessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Reseed failed: {exc.stderr.strip() or 'Unknown error'}",
        ) from exc

    return AdminDemoActionResponse(
        message=message,
        deleted_records=deleted_records,
    )


@api_router.post("/admin/subscriptions/dispatch-renewal-reminders", response_model=RenewalDispatchResponse)
async def dispatch_renewal_reminders(_: dict = Depends(_get_admin_session)):
    subscriptions = await db.subscriptions.find(
        {"status": "active"},
        {"_id": 0},
    ).to_list(1000)

    now = datetime.now(timezone.utc)
    threshold = now + timedelta(days=7)
    reminded_count = 0

    for entry in subscriptions:
        try:
            expires_at = datetime.fromisoformat(entry.get("expires_at", ""))
        except ValueError:
            continue

        if now <= expires_at <= threshold:
            plan_label = "User" if entry.get("plan_type") == "user" else "Worker"
            message = (
                f"Your {plan_label} subscription will expire on "
                f"{expires_at.date().isoformat()}. Please renew to avoid interruption."
            )

            await asyncio.gather(
                asyncio.to_thread(_send_sms_message, entry.get("phone", ""), message),
                asyncio.to_thread(
                    _send_email_message,
                    entry.get("email", ""),
                    "Dial For Help Subscription Renewal Reminder",
                    message,
                ),
            )

            await _create_user_notification(
                email=entry.get("email", ""),
                phone=entry.get("phone", ""),
                title="Subscription renewal reminder",
                message=message,
                category="subscription",
                booking_id=None,
            )
            reminded_count += 1

    return RenewalDispatchResponse(
        reminded_count=reminded_count,
        message="Renewal reminder dispatch completed",
    )


@api_router.get("/admin/bookings/{booking_id}/suggest-workers", response_model=List[WorkerSuggestion])
async def suggest_workers_for_booking(
    booking_id: str,
    _: dict = Depends(_get_admin_session),
):
    booking_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking = BookingResponse(**_coerce_booking_doc(booking_doc))
    workers = await db.workers.find({"is_active": True}, {"_id": 0}).to_list(500)

    suggestions: List[WorkerSuggestion] = []
    for worker_doc in workers:
        worker = WorkerResponse(**_coerce_worker_doc(worker_doc))
        score = 0
        if worker.skill == booking.service_type:
            score += 5
        if worker.availability == "Full-time":
            score += 2
        if worker.years_experience >= 5:
            score += 1

        suggestions.append(
            WorkerSuggestion(
                worker_id=worker.id,
                full_name=worker.full_name,
                skill=worker.skill,
                availability=worker.availability,
                score=score,
            )
        )

    suggestions.sort(key=lambda item: item.score, reverse=True)
    return suggestions[:5]


@api_router.patch("/admin/bookings/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: str,
    payload: BookingStatusUpdate,
    _: dict = Depends(_get_admin_session),
):
    existing = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_data = {
        "status": payload.status,
        "updated_at": now_iso(),
        "assigned_worker_id": payload.assigned_worker_id,
    }
    await db.bookings.update_one({"id": booking_id}, {"$set": update_data})

    updated_doc = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    booking = BookingResponse(**_coerce_booking_doc(updated_doc))

    if payload.status == "assigned" and payload.assigned_worker_id:
        worker = await db.workers.find_one({"id": payload.assigned_worker_id}, {"_id": 0})
        if worker:
            assignment_message = (
                f"Your service request is assigned to {worker.get('full_name', 'our worker')} "
                f"(Phone: {worker.get('phone', 'N/A')})."
            )
            assignment_email_subject = "Dial For Help: Worker Assigned"
            assignment_email_body = (
                f"Booking ID: {booking.id}\n"
                f"Service: {booking.service_type}\n"
                f"Assigned Worker: {worker.get('full_name', 'N/A')}\n"
                f"Worker Phone: {worker.get('phone', 'N/A')}\n"
            )

            assignment_logs = await asyncio.gather(
                asyncio.to_thread(_send_sms_message, booking.phone, assignment_message),
                asyncio.to_thread(
                    _send_email_message,
                    booking.email,
                    assignment_email_subject,
                    assignment_email_body,
                ),
            )

            existing_logs = booking.notification_log
            merged_logs = existing_logs + assignment_logs
            await db.bookings.update_one(
                {"id": booking_id},
                {"$set": {"notification_log": [item.model_dump() for item in merged_logs]}},
            )
            booking.notification_log = merged_logs

            await _create_user_notification(
                email=booking.email,
                phone=booking.phone,
                title="Worker assigned",
                message=(
                    f"{worker.get('full_name', 'Worker')} assigned. "
                    f"Contact: {worker.get('phone', 'N/A')}"
                ),
                category="assignment",
                booking_id=booking.id,
            )

    event_name = f"Status changed to {payload.status}"
    notification_log = await _notify_booking_event(booking, event_name)
    if notification_log:
        combined_log = booking.notification_log + notification_log
        updated_at = now_iso()
        await db.bookings.update_one(
            {"id": booking_id},
            {
                "$set": {
                    "notification_log": [item.model_dump() for item in combined_log],
                    "updated_at": updated_at,
                }
            },
        )
        booking.notification_log = combined_log
        booking.updated_at = updated_at

    await _create_user_notification(
        email=booking.email,
        phone=booking.phone,
        title="Booking status updated",
        message=f"Your booking status is now {payload.status}.",
        category="status",
        booking_id=booking.id,
    )

    return booking


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_tasks():
    await _ensure_default_admin()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()