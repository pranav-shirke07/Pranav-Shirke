import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


# User auth/profile/bookings and assignment-notification integration tests.
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


def _mk_identity(prefix: str) -> dict:
    uniq = uuid.uuid4().hex[:10]
    return {
        "name": f"TEST_{prefix}_{uniq}",
        "phone": f"+9170{uniq[:8]}",
        "email": f"test_{prefix}_{uniq}@example.com",
        "password": "Pass@12345",
    }


def _mk_booking_payload(identity: dict, service: str = "Plumbing") -> dict:
    preferred_date = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
    return {
        "full_name": identity["name"],
        "phone": identity["phone"],
        "email": identity["email"],
        "service_type": service,
        "address": "TEST Street, Bengaluru",
        "preferred_date": preferred_date,
        "notes": "TEST booking for user profile",
    }


def _verify_signature(secret: str, order_id: str, payment_id: str) -> str:
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _register_user_and_get_token(api_client, api_base_url, identity: dict):
    response = api_client.post(
        f"{api_base_url}/api/users/register",
        json={
            "full_name": identity["name"],
            "email": identity["email"],
            "password": identity["password"],
            "phone": identity["phone"],
            "address": "TEST User Address",
            "notify_email": True,
            "notify_sms": True,
        },
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["token"], str) and data["token"]
    return data


@pytest.fixture
def admin_token(api_client, api_base_url) -> str:
    response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "Admin@123"},
        timeout=25,
    )
    assert response.status_code == 200
    token = response.json().get("token")
    assert isinstance(token, str) and token
    return token


def test_user_register_and_profile_get(api_client, api_base_url):
    identity = _mk_identity("user_register")
    register_data = _register_user_and_get_token(api_client, api_base_url, identity)

    assert register_data["user"]["email"] == identity["email"].lower()
    assert register_data["user"]["full_name"] == identity["name"]
    assert register_data["user"]["phone"] == identity["phone"]

    profile = api_client.get(
        f"{api_base_url}/api/users/profile",
        headers={"Authorization": f"Bearer {register_data['token']}"},
        timeout=20,
    )
    assert profile.status_code == 200
    profile_data = profile.json()
    assert profile_data["email"] == identity["email"].lower()
    assert profile_data["full_name"] == identity["name"]


def test_user_login_success_and_invalid_password(api_client, api_base_url):
    identity = _mk_identity("user_login")
    _register_user_and_get_token(api_client, api_base_url, identity)

    success = api_client.post(
        f"{api_base_url}/api/users/login",
        json={"email": identity["email"], "password": identity["password"]},
        timeout=20,
    )
    assert success.status_code == 200
    success_data = success.json()
    assert success_data["user"]["email"] == identity["email"].lower()
    assert isinstance(success_data["token"], str) and success_data["token"]

    invalid = api_client.post(
        f"{api_base_url}/api/users/login",
        json={"email": identity["email"], "password": "Wrong@12345"},
        timeout=20,
    )
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "Invalid user credentials"


def test_user_profile_update_persists(api_client, api_base_url):
    identity = _mk_identity("user_profile_update")
    register_data = _register_user_and_get_token(api_client, api_base_url, identity)
    token = register_data["token"]

    updated_name = f"{identity['name']}_Updated"
    updated_phone = f"{identity['phone']}  "
    updated_address = "TEST Updated Address Line"

    update = api_client.put(
        f"{api_base_url}/api/users/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": updated_name,
            "phone": updated_phone,
            "address": updated_address,
            "notify_email": False,
            "notify_sms": True,
        },
        timeout=20,
    )
    assert update.status_code == 200
    update_data = update.json()
    assert update_data["full_name"] == updated_name
    assert update_data["phone"] == identity["phone"]
    assert update_data["address"] == updated_address
    assert update_data["notify_email"] is False

    fetched = api_client.get(
        f"{api_base_url}/api/users/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    assert fetched.status_code == 200
    fetched_data = fetched.json()
    assert fetched_data["full_name"] == updated_name
    assert fetched_data["notify_email"] is False


def test_user_bookings_returns_only_user_records(api_client, api_base_url):
    identity_a = _mk_identity("bookings_a")
    identity_b = _mk_identity("bookings_b")

    auth_a = _register_user_and_get_token(api_client, api_base_url, identity_a)
    _register_user_and_get_token(api_client, api_base_url, identity_b)

    booking_a = api_client.post(
        f"{api_base_url}/api/bookings",
        json=_mk_booking_payload(identity_a, service="Cleaning"),
        timeout=30,
    )
    assert booking_a.status_code == 200
    booking_a_id = booking_a.json()["id"]

    booking_b = api_client.post(
        f"{api_base_url}/api/bookings",
        json=_mk_booking_payload(identity_b, service="Plumbing"),
        timeout=30,
    )
    assert booking_b.status_code == 200
    booking_b_id = booking_b.json()["id"]

    user_bookings = api_client.get(
        f"{api_base_url}/api/users/bookings",
        headers={"Authorization": f"Bearer {auth_a['token']}"},
        timeout=25,
    )
    assert user_bookings.status_code == 200
    data = user_bookings.json()
    assert any(item["id"] == booking_a_id for item in data)
    assert all(item["id"] != booking_b_id for item in data)


def test_assignment_adds_contact_notification_attempts_for_user_email_sms(
    api_client,
    api_base_url,
    admin_token,
    razorpay_secret,
):
    booking_identity = _mk_identity("assign_notify_booking")
    worker_identity = _mk_identity("assign_notify_worker")

    create_booking = api_client.post(
        f"{api_base_url}/api/bookings",
        json=_mk_booking_payload(booking_identity, service="Electrical"),
        timeout=35,
    )
    assert create_booking.status_code == 200
    booking = create_booking.json()
    before_count = len(booking["notification_log"])

    create_order = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "worker",
            "name": worker_identity["name"],
            "email": worker_identity["email"],
            "phone": worker_identity["phone"],
        },
        timeout=40,
    )
    assert create_order.status_code == 200
    order = create_order.json()

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    signature = _verify_signature(razorpay_secret, order["order_id"], payment_id)

    verify = api_client.post(
        f"{api_base_url}/api/payments/verify",
        json={
            "plan_type": "worker",
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
            "subscriber_name": worker_identity["name"],
            "email": worker_identity["email"],
            "phone": worker_identity["phone"],
        },
        timeout=40,
    )
    assert verify.status_code == 200

    worker_signup = api_client.post(
        f"{api_base_url}/api/workers/signup",
        json={
            "full_name": worker_identity["name"],
            "phone": worker_identity["phone"],
            "email": worker_identity["email"],
            "skill": "Electrical",
            "city": "TEST City",
            "years_experience": 5,
            "availability": "Full-time",
            "about": "TEST worker for assigned notifications",
        },
        timeout=35,
    )
    assert worker_signup.status_code == 200
    worker = worker_signup.json()

    assign = api_client.patch(
        f"{api_base_url}/api/admin/bookings/{booking['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "assigned", "assigned_worker_id": worker["id"]},
        timeout=40,
    )
    assert assign.status_code == 200
    updated = assign.json()

    assert updated["status"] == "assigned"
    assert updated["assigned_worker_id"] == worker["id"]
    assert len(updated["notification_log"]) > before_count

    booking_phone = booking_identity["phone"]
    booking_email = booking_identity["email"].lower()
    sms_to_user = [
        item
        for item in updated["notification_log"]
        if item["channel"] == "sms" and item["recipient"] == booking_phone
    ]
    email_to_user = [
        item
        for item in updated["notification_log"]
        if item["channel"] == "email" and item["recipient"].lower() == booking_email
    ]

    assert len(sms_to_user) >= 2
    assert len(email_to_user) >= 2
    assert any(
        ("Twilio" in item["detail"]) or (item["detail"] == "SMS sent")
        for item in sms_to_user
    )
    assert any(
        ("SendGrid" in item["detail"]) or (item["detail"] == "Email sent")
        for item in email_to_user
    )
