import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


# Subscription, payment, booking gate, worker gate, and admin regression tests.
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


@pytest.fixture
def admin_token(api_client, api_base_url) -> str:
    response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "Admin@123"},
        timeout=25,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("token"), str) and data["token"]
    return data["token"]


def _mk_identity(prefix: str) -> dict:
    uniq = uuid.uuid4().hex[:10]
    return {
        "name": f"TEST_{prefix}_{uniq}",
        "phone": f"+9199{uniq[:8]}",
        "email": f"test_{prefix}_{uniq}@example.com",
    }


def _booking_payload(identity: dict, service: str = "Plumbing") -> dict:
    preferred_date = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()
    return {
        "full_name": identity["name"],
        "phone": identity["phone"],
        "email": identity["email"],
        "service_type": service,
        "address": "TEST Address, Bengaluru",
        "preferred_date": preferred_date,
        "notes": "TEST booking",
    }


def _verify_signature(secret: str, order_id: str, payment_id: str) -> str:
    body = f"{order_id}|{payment_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_user_status_initial_and_shape(api_client, api_base_url):
    identity = _mk_identity("user_status")
    response = api_client.get(
        f"{api_base_url}/api/subscriptions/user-status",
        params={"phone": identity["phone"], "email": identity["email"]},
        timeout=25,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["bookings_used"] == 0
    assert data["free_remaining"] == 2
    assert data["has_active_subscription"] is False
    assert data["requires_subscription"] is False
    assert isinstance(data["identity_key"], str) and "::" in data["identity_key"]


def test_booking_first_two_free_and_third_blocked(api_client, api_base_url):
    identity = _mk_identity("booking_gate")
    payload = _booking_payload(identity, service="Electrical")

    first = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["charge_type"] == "free"

    second = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["charge_type"] == "free"

    third = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert third.status_code == 402
    blocked = third.json()
    assert blocked["detail"]["code"] == "USER_SUBSCRIPTION_REQUIRED"
    assert blocked["detail"]["required_amount_inr"] == 99
    assert blocked["detail"]["free_remaining"] == 0


def test_create_order_returns_expected_values_for_both_plans(api_client, api_base_url):
    user_identity = _mk_identity("order_user")
    worker_identity = _mk_identity("order_worker")

    user_order = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "user",
            "name": user_identity["name"],
            "email": user_identity["email"],
            "phone": user_identity["phone"],
        },
        timeout=40,
    )
    assert user_order.status_code == 200
    user_data = user_order.json()
    assert isinstance(user_data["order_id"], str) and user_data["order_id"].startswith("order_")
    assert user_data["amount"] == 9900
    assert user_data["amount_inr"] == 99
    assert user_data["plan_type"] == "user"
    assert isinstance(user_data["key_id"], str) and user_data["key_id"].startswith("rzp_")

    worker_order = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "worker",
            "name": worker_identity["name"],
            "email": worker_identity["email"],
            "phone": worker_identity["phone"],
        },
        timeout=40,
    )
    assert worker_order.status_code == 200
    worker_data = worker_order.json()
    assert isinstance(worker_data["order_id"], str) and worker_data["order_id"].startswith("order_")
    assert worker_data["amount"] == 19900
    assert worker_data["amount_inr"] == 199
    assert worker_data["plan_type"] == "worker"


def test_verify_user_subscription_unblocks_booking(api_client, api_base_url, razorpay_secret):
    identity = _mk_identity("user_verify")
    payload = _booking_payload(identity, service="Cleaning")

    for _ in range(2):
        response = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
        assert response.status_code == 200

    blocked = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert blocked.status_code == 402
    assert blocked.json()["detail"]["code"] == "USER_SUBSCRIPTION_REQUIRED"

    create_order = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "user",
            "name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
        },
        timeout=40,
    )
    assert create_order.status_code == 200
    order = create_order.json()

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    signature = _verify_signature(razorpay_secret, order["order_id"], payment_id)

    verify_response = api_client.post(
        f"{api_base_url}/api/payments/verify",
        json={
            "plan_type": "user",
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
            "subscriber_name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
        },
        timeout=40,
    )
    assert verify_response.status_code == 200
    verify_data = verify_response.json()
    assert verify_data["message"] == "Subscription activated"
    assert verify_data["plan_type"] == "user"

    status_response = api_client.get(
        f"{api_base_url}/api/subscriptions/user-status",
        params={"phone": identity["phone"], "email": identity["email"]},
        timeout=25,
    )
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["has_active_subscription"] is True
    assert status_data["requires_subscription"] is False
    assert isinstance(status_data["subscription_expires_at"], str)

    allowed = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert allowed.status_code == 200
    allowed_data = allowed.json()
    assert allowed_data["charge_type"] == "subscription"


def test_worker_signup_blocked_before_subscription_and_allowed_after_verify(api_client, api_base_url, razorpay_secret):
    identity = _mk_identity("worker_verify")
    worker_payload = {
        "full_name": identity["name"],
        "phone": identity["phone"],
        "email": identity["email"],
        "skill": "Plumbing",
        "city": "TEST City",
        "years_experience": 6,
        "availability": "Full-time",
        "about": "TEST worker profile",
    }

    blocked_signup = api_client.post(
        f"{api_base_url}/api/workers/signup",
        json=worker_payload,
        timeout=30,
    )
    assert blocked_signup.status_code == 402
    blocked_data = blocked_signup.json()
    assert blocked_data["detail"]["code"] == "WORKER_SUBSCRIPTION_REQUIRED"
    assert blocked_data["detail"]["required_amount_inr"] == 199

    create_order = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "worker",
            "name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
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
            "subscriber_name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
        },
        timeout=40,
    )
    assert verify.status_code == 200
    verify_data = verify.json()
    assert verify_data["plan_type"] == "worker"
    assert verify_data["message"] == "Subscription activated"

    worker_status = api_client.get(
        f"{api_base_url}/api/subscriptions/worker-status",
        params={"phone": identity["phone"], "email": identity["email"]},
        timeout=25,
    )
    assert worker_status.status_code == 200
    worker_status_data = worker_status.json()
    assert worker_status_data["has_active_subscription"] is True
    assert isinstance(worker_status_data["subscription_expires_at"], str)

    allowed_signup = api_client.post(
        f"{api_base_url}/api/workers/signup",
        json=worker_payload,
        timeout=30,
    )
    assert allowed_signup.status_code == 200
    allowed_data = allowed_signup.json()
    assert allowed_data["is_active"] is True
    assert isinstance(allowed_data["subscription_expires_at"], str)


def test_admin_login_overview_and_booking_status_update_regression(api_client, api_base_url, admin_token):
    health = api_client.get(f"{api_base_url}/api/", timeout=20)
    assert health.status_code == 200

    identity = _mk_identity("admin_booking")
    booking_payload = _booking_payload(identity, service="Other")
    create_booking = api_client.post(f"{api_base_url}/api/bookings", json=booking_payload, timeout=30)
    assert create_booking.status_code == 200
    booking = create_booking.json()
    assert booking["status"] == "pending"

    overview_before = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_before.status_code == 200
    overview_data = overview_before.json()
    assert isinstance(overview_data["bookings"], list)
    assert isinstance(overview_data["stats"]["pending"], int)
    assert any(item["id"] == booking["id"] for item in overview_data["bookings"])

    update = api_client.patch(
        f"{api_base_url}/api/admin/bookings/{booking['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "completed", "assigned_worker_id": None},
        timeout=30,
    )
    assert update.status_code == 200
    updated_data = update.json()
    assert updated_data["status"] == "completed"

    overview_after = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_after.status_code == 200
    post_update = overview_after.json()
    matched = [item for item in post_update["bookings"] if item["id"] == booking["id"]]
    assert len(matched) == 1
    assert matched[0]["status"] == "completed"
