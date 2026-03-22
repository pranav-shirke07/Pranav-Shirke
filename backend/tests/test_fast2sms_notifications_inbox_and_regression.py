import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv


# Notification + inbox + regression coverage for Fast2SMS, user/account, and admin flows.
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "frontend/.env")
load_dotenv(ROOT_DIR / "backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def razorpay_secret() -> str:
    if not RAZORPAY_SECRET:
        pytest.skip("RAZORPAY_KEY_SECRET is not set")
    return RAZORPAY_SECRET


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _identity(prefix: str) -> dict:
    unique = uuid.uuid4().hex[:10]
    return {
        "name": f"TEST_{prefix}_{unique}",
        "email": f"test_{prefix}_{unique}@example.com",
        "phone": f"+9171{unique[:8]}",
        "password": "Pass@12345",
    }


def _preferred_date(days_ahead: int = 2) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days_ahead)).date().isoformat()


def _register_user(api_client, api_base_url: str, identity: dict) -> str:
    register_response = api_client.post(
        f"{api_base_url}/api/users/register",
        json={
            "full_name": identity["name"],
            "email": identity["email"],
            "password": identity["password"],
            "phone": identity["phone"],
            "address": "TEST Address",
            "notify_email": True,
            "notify_sms": True,
        },
        timeout=30,
    )
    assert register_response.status_code == 200
    token = register_response.json().get("token")
    assert isinstance(token, str) and token
    return token


@pytest.fixture
def admin_token(api_client, api_base_url) -> str:
    login_response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "Admin@123"},
        timeout=25,
    )
    assert login_response.status_code == 200
    token = login_response.json().get("token")
    assert isinstance(token, str) and token
    return token


def _activate_worker_subscription(api_client, api_base_url: str, razorpay_secret: str, identity: dict) -> None:
    order_response = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "worker",
            "name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
        },
        timeout=40,
    )
    assert order_response.status_code == 200
    order_id = order_response.json()["order_id"]

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    sign_payload = f"{order_id}|{payment_id}".encode("utf-8")
    signature = hmac.new(razorpay_secret.encode("utf-8"), sign_payload, hashlib.sha256).hexdigest()

    verify_response = api_client.post(
        f"{api_base_url}/api/payments/verify",
        json={
            "plan_type": "worker",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
            "subscriber_name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
        },
        timeout=40,
    )
    assert verify_response.status_code == 200


def test_fast2sms_path_is_used_for_booking_notifications(api_client, api_base_url):
    identity = _identity("fast2sms_booking")
    booking_response = api_client.post(
        f"{api_base_url}/api/bookings",
        json={
            "full_name": identity["name"],
            "phone": identity["phone"],
            "email": identity["email"],
            "service_type": "Cleaning",
            "address": "TEST booking address",
            "preferred_date": _preferred_date(),
            "notes": "TEST fast2sms path",
        },
        timeout=45,
    )
    assert booking_response.status_code == 200
    booking_data = booking_response.json()

    sms_logs = [entry for entry in booking_data["notification_log"] if entry["channel"] == "sms"]
    assert len(sms_logs) >= 1
    assert any("Fast2SMS" in entry["detail"] for entry in sms_logs)
    assert all("Twilio" not in entry["detail"] for entry in sms_logs)


def test_user_notifications_get_and_mark_read(api_client, api_base_url):
    identity = _identity("user_inbox")
    user_token = _register_user(api_client, api_base_url, identity)

    create_booking = api_client.post(
        f"{api_base_url}/api/bookings",
        json={
            "full_name": identity["name"],
            "phone": identity["phone"],
            "email": identity["email"],
            "service_type": "Plumbing",
            "address": "TEST inbox address",
            "preferred_date": _preferred_date(),
            "notes": "TEST user inbox notification",
        },
        timeout=45,
    )
    assert create_booking.status_code == 200
    booking_id = create_booking.json()["id"]

    list_response = api_client.get(
        f"{api_base_url}/api/users/notifications",
        headers={"Authorization": f"Bearer {user_token}"},
        timeout=25,
    )
    assert list_response.status_code == 200
    notifications = list_response.json()
    assert isinstance(notifications, list)

    target = next(
        (
            item
            for item in notifications
            if item.get("booking_id") == booking_id and item.get("category") == "booking"
        ),
        None,
    )
    assert target is not None
    assert target["read"] is False

    mark_response = api_client.patch(
        f"{api_base_url}/api/users/notifications/{target['id']}/read",
        headers={"Authorization": f"Bearer {user_token}"},
        json={},
        timeout=25,
    )
    assert mark_response.status_code == 200
    mark_data = mark_response.json()
    assert mark_data["id"] == target["id"]
    assert mark_data["read"] is True

    list_after = api_client.get(
        f"{api_base_url}/api/users/notifications",
        headers={"Authorization": f"Bearer {user_token}"},
        timeout=25,
    )
    assert list_after.status_code == 200
    updated_item = next((item for item in list_after.json() if item["id"] == target["id"]), None)
    assert updated_item is not None
    assert updated_item["read"] is True


def test_assignment_updates_create_notification_attempts_and_user_inbox_entries(
    api_client,
    api_base_url,
    admin_token,
    razorpay_secret,
):
    customer = _identity("assignment_customer")
    worker_identity = _identity("assignment_worker")

    customer_token = _register_user(api_client, api_base_url, customer)

    booking_response = api_client.post(
        f"{api_base_url}/api/bookings",
        json={
            "full_name": customer["name"],
            "phone": customer["phone"],
            "email": customer["email"],
            "service_type": "Electrical",
            "address": "TEST assignment address",
            "preferred_date": _preferred_date(3),
            "notes": "TEST assignment notifications",
        },
        timeout=45,
    )
    assert booking_response.status_code == 200
    booking = booking_response.json()
    before_log_count = len(booking["notification_log"])

    _activate_worker_subscription(api_client, api_base_url, razorpay_secret, worker_identity)
    signup_response = api_client.post(
        f"{api_base_url}/api/workers/signup",
        json={
            "full_name": worker_identity["name"],
            "phone": worker_identity["phone"],
            "email": worker_identity["email"],
            "skill": "Electrical",
            "city": "TEST City",
            "years_experience": 7,
            "availability": "Full-time",
            "about": "TEST worker for assignment",
        },
        timeout=40,
    )
    assert signup_response.status_code == 200
    worker = signup_response.json()

    assign_response = api_client.patch(
        f"{api_base_url}/api/admin/bookings/{booking['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "assigned", "assigned_worker_id": worker["id"]},
        timeout=45,
    )
    assert assign_response.status_code == 200
    assigned = assign_response.json()
    assert assigned["status"] == "assigned"
    assert assigned["assigned_worker_id"] == worker["id"]
    assert len(assigned["notification_log"]) > before_log_count

    booking_sms_logs = [
        item
        for item in assigned["notification_log"]
        if item["channel"] == "sms" and item["recipient"] == customer["phone"]
    ]
    assert len(booking_sms_logs) >= 2
    assert any("Fast2SMS" in item["detail"] for item in booking_sms_logs)

    inbox_response = api_client.get(
        f"{api_base_url}/api/users/notifications",
        headers={"Authorization": f"Bearer {customer_token}"},
        timeout=30,
    )
    assert inbox_response.status_code == 200
    categories_for_booking = {
        item["category"] for item in inbox_response.json() if item.get("booking_id") == booking["id"]
    }
    assert "assignment" in categories_for_booking
    assert "status" in categories_for_booking


def test_admin_dispatch_renewal_reminders_endpoint_shape(api_client, api_base_url, admin_token):
    dispatch_response = api_client.post(
        f"{api_base_url}/api/admin/subscriptions/dispatch-renewal-reminders",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={},
        timeout=60,
    )
    assert dispatch_response.status_code == 200
    data = dispatch_response.json()
    assert isinstance(data.get("reminded_count"), int)
    assert data.get("message") == "Renewal reminder dispatch completed"


def test_regression_user_login_booking_track_and_admin_overview(api_client, api_base_url, admin_token):
    identity = _identity("regression_core")
    _register_user(api_client, api_base_url, identity)

    login_response = api_client.post(
        f"{api_base_url}/api/users/login",
        json={"email": identity["email"], "password": identity["password"]},
        timeout=25,
    )
    assert login_response.status_code == 200
    user_data = login_response.json()
    assert user_data["user"]["email"] == identity["email"].lower()

    booking_response = api_client.post(
        f"{api_base_url}/api/bookings",
        json={
            "full_name": identity["name"],
            "phone": identity["phone"],
            "email": identity["email"],
            "service_type": "Carpentry",
            "address": "TEST regression address",
            "preferred_date": _preferred_date(),
            "notes": "TEST regression booking",
        },
        timeout=45,
    )
    assert booking_response.status_code == 200
    booking_id = booking_response.json()["id"]

    track_response = api_client.get(f"{api_base_url}/api/bookings/track/{booking_id}", timeout=25)
    assert track_response.status_code == 200
    tracked = track_response.json()
    assert tracked["booking_id"] == booking_id
    assert tracked["status"] == "pending"

    overview_response = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=35,
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert "stats" in overview
    assert isinstance(overview.get("bookings"), list)
