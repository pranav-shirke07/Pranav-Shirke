from datetime import datetime, timedelta, timezone
import logging
import os
from pathlib import Path
from typing import List, Literal, Optional
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, status
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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Dial For Help API")
api_router = APIRouter(prefix="/api")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        "Plumbing", "Electrical", "Cleaning", "General Handyman", "Other"
    ]
    address: str = Field(min_length=5, max_length=220)
    preferred_date: str
    notes: str = Field(default="", max_length=800)


class BookingResponse(BookingCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    status: Literal["pending", "assigned", "completed"]
    assigned_worker_id: Optional[str] = None
    created_at: str
    updated_at: str
    notification_log: List[NotificationLog] = Field(default_factory=list)


class WorkerSignupCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    skill: Literal["Plumbing", "Electrical", "Cleaning", "General Handyman"]
    city: str = Field(min_length=2, max_length=80)
    years_experience: int = Field(ge=0, le=60)
    availability: Literal["Full-time", "Part-time", "Weekends"]
    about: str = Field(default="", max_length=600)


class WorkerResponse(WorkerSignupCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    joined_at: str
    is_active: bool


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    message: str = Field(min_length=5, max_length=1000)


class ContactResponse(ContactCreate):
    model_config = ConfigDict(extra="ignore")

    id: str
    created_at: str


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


def _send_sms_message(phone_number: str, message: str) -> NotificationLog:
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


def _notify_booking_event(booking: BookingResponse, event_title: str) -> List[NotificationLog]:
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

    for email in email_targets:
        logs.append(_send_email_message(email, email_subject, email_body))

    for phone in sms_targets:
        logs.append(_send_sms_message(phone, sms_body))

    return logs


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


@api_router.get("/")
async def root():
    return {"message": "Dial For Help API is running"}


@api_router.post("/bookings", response_model=BookingResponse)
async def create_booking(payload: BookingCreate):
    timestamp = now_iso()
    booking = BookingResponse(
        id=str(uuid.uuid4()),
        status="pending",
        assigned_worker_id=None,
        created_at=timestamp,
        updated_at=timestamp,
        notification_log=[],
        **payload.model_dump(),
    )
    booking_doc = booking.model_dump()
    await db.bookings.insert_one(dict(booking_doc))

    notification_log = _notify_booking_event(booking, "Booking received")
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


@api_router.post("/workers/signup", response_model=WorkerResponse)
async def worker_signup(payload: WorkerSignupCreate):
    worker = WorkerResponse(
        id=str(uuid.uuid4()),
        joined_at=now_iso(),
        is_active=True,
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

    booking_items = [BookingResponse(**item) for item in bookings]
    worker_items = [WorkerResponse(**item) for item in workers]
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
    booking = BookingResponse(**updated_doc)

    event_name = f"Status changed to {payload.status}"
    notification_log = _notify_booking_event(booking, event_name)
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