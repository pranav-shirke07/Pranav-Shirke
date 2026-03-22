import os
import uuid
import hashlib
import hmac

import pytest
import requests


# Core public and admin API flow tests for Dial For Help.
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
RAZORPAY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def _activate_worker_subscription(api_client, api_base_url, worker_payload):
    if not RAZORPAY_SECRET:
        pytest.skip("RAZORPAY_KEY_SECRET is not set")

    order_response = api_client.post(
        f"{api_base_url}/api/payments/create-order",
        json={
            "plan_type": "worker",
            "name": worker_payload["full_name"],
            "email": worker_payload["email"],
            "phone": worker_payload["phone"],
        },
        timeout=30,
    )
    assert order_response.status_code == 200
    order_data = order_response.json()

    payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    signature_payload = f"{order_data['order_id']}|{payment_id}".encode("utf-8")
    signature = hmac.new(
        RAZORPAY_SECRET.encode("utf-8"),
        signature_payload,
        hashlib.sha256,
    ).hexdigest()

    verify_response = api_client.post(
        f"{api_base_url}/api/payments/verify",
        json={
            "plan_type": "worker",
            "razorpay_order_id": order_data["order_id"],
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
            "subscriber_name": worker_payload["full_name"],
            "email": worker_payload["email"],
            "phone": worker_payload["phone"],
        },
        timeout=30,
    )
    assert verify_response.status_code == 200


@pytest.fixture
def admin_token(api_client, api_base_url) -> str:
    response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "Admin@123"},
        timeout=20,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("token"), str) and data["token"]
    return data["token"]


def test_root_health(api_client, api_base_url):
    response = api_client.get(f"{api_base_url}/api/", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Dial For Help API is running"


def test_create_booking_and_verify_overview_persistence(api_client, api_base_url, admin_token):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "full_name": f"TEST Booking {unique}",
        "phone": "+15550001234",
        "email": f"test_booking_{unique}@example.com",
        "service_type": "Plumbing",
        "address": "123 Test Street, Test City",
        "preferred_date": "2026-03-25",
        "notes": "TEST booking flow",
    }

    create_response = api_client.post(f"{api_base_url}/api/bookings", json=payload, timeout=30)
    assert create_response.status_code == 200
    created = create_response.json()

    assert created["full_name"] == payload["full_name"]
    assert created["status"] == "pending"
    assert isinstance(created["id"], str) and created["id"]
    assert isinstance(created["notification_log"], list)

    overview_response = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    booking_ids = [item["id"] for item in overview["bookings"]]
    assert created["id"] in booking_ids


def test_create_worker_signup_and_verify_overview(api_client, api_base_url, admin_token):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "full_name": f"TEST Worker {unique}",
        "phone": "+15550002222",
        "email": f"test_worker_{unique}@example.com",
        "skill": "Electrical",
        "city": "Testville",
        "years_experience": 5,
        "availability": "Part-time",
        "about": "TEST electrician profile",
    }

    _activate_worker_subscription(api_client, api_base_url, payload)

    create_response = api_client.post(f"{api_base_url}/api/workers/signup", json=payload, timeout=20)
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["full_name"] == payload["full_name"]
    assert created["skill"] == payload["skill"]
    assert created["is_active"] is True

    overview_response = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    worker_ids = [item["id"] for item in overview["workers"]]
    assert created["id"] in worker_ids


def test_create_contact_and_verify_overview(api_client, api_base_url, admin_token):
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST Contact {unique}",
        "email": f"test_contact_{unique}@example.com",
        "phone": "+15550003333",
        "message": "TEST contact message for support",
    }

    create_response = api_client.post(f"{api_base_url}/api/contacts", json=payload, timeout=20)
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == payload["name"]
    assert created["message"] == payload["message"]
    assert isinstance(created["id"], str)

    overview_response = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    contact_ids = [item["id"] for item in overview["contacts"]]
    assert created["id"] in contact_ids


def test_admin_login_invalid_credentials(api_client, api_base_url):
    response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "wrong-password"},
        timeout=20,
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


def test_admin_overview_requires_token(api_client, api_base_url):
    response = api_client.get(f"{api_base_url}/api/admin/overview", timeout=20)
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Missing admin token"


def test_update_booking_status_and_verify_in_overview(api_client, api_base_url, admin_token):
    unique = uuid.uuid4().hex[:8]
    booking_payload = {
        "full_name": f"TEST Status Booking {unique}",
        "phone": "+15550004444",
        "email": f"status_booking_{unique}@example.com",
        "service_type": "Cleaning",
        "address": "456 Status Ave, Test City",
        "preferred_date": "2026-03-30",
        "notes": "TEST status update",
    }
    worker_payload = {
        "full_name": f"TEST Assign Worker {unique}",
        "phone": "+15550005555",
        "email": f"assign_worker_{unique}@example.com",
        "skill": "Cleaning",
        "city": "Status City",
        "years_experience": 4,
        "availability": "Full-time",
        "about": "TEST worker for assignment",
    }

    create_booking = api_client.post(f"{api_base_url}/api/bookings", json=booking_payload, timeout=30)
    assert create_booking.status_code == 200
    booking = create_booking.json()

    _activate_worker_subscription(api_client, api_base_url, worker_payload)

    create_worker = api_client.post(f"{api_base_url}/api/workers/signup", json=worker_payload, timeout=20)
    assert create_worker.status_code == 200
    worker = create_worker.json()

    patch_response = api_client.patch(
        f"{api_base_url}/api/admin/bookings/{booking['id']}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "assigned", "assigned_worker_id": worker["id"]},
        timeout=30,
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["status"] == "assigned"
    assert patched["assigned_worker_id"] == worker["id"]

    overview_response = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert overview_response.status_code == 200
    overview = overview_response.json()
    matching = [item for item in overview["bookings"] if item["id"] == booking["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "assigned"
    assert matching[0]["assigned_worker_id"] == worker["id"]
