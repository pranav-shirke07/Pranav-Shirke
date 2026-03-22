import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import load_dotenv


# Admin demo utility + analytics endpoints and core regression smoke coverage.
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


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


@pytest.fixture
def admin_token(api_client, api_base_url) -> str:
    response = api_client.post(
        f"{api_base_url}/api/admin/login",
        json={"email": "admin@dialforhelp.com", "password": "Admin@123"},
        timeout=30,
    )
    assert response.status_code == 200
    token = response.json().get("token")
    assert isinstance(token, str) and token
    return token


def _mk_identity(prefix: str) -> dict:
    uniq = uuid.uuid4().hex[:10]
    return {
        "name": f"TEST_{prefix}_{uniq}",
        "phone": f"+9188{uniq[:8]}",
        "email": f"test_{prefix}_{uniq}@example.com",
    }


def test_admin_demo_reset_reseed_and_demo_logins(api_client, api_base_url, admin_token):
    reseed = api_client.post(
        f"{api_base_url}/api/admin/demo/reset-reseed",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=300,
    )
    assert reseed.status_code == 200
    reseed_data = reseed.json()
    assert reseed_data["deleted_records"] >= 0
    assert "Reset + reseed completed" in reseed_data["message"]

    demo_logins = api_client.get(
        f"{api_base_url}/api/admin/demo-logins",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=40,
    )
    assert demo_logins.status_code == 200
    rows = demo_logins.json()
    assert isinstance(rows, list)
    assert len(rows) >= 3

    roles = {item["role"] for item in rows}
    assert "admin" in roles
    assert "user" in roles
    assert "worker-reference" in roles

    admin_row = next((item for item in rows if item["role"] == "admin"), None)
    assert admin_row is not None
    assert admin_row["email"] == "admin@dialforhelp.com"
    assert admin_row["login_password"] == "Admin@123"


def test_admin_demo_reset_then_reseed_recovers_seeded_rows(api_client, api_base_url, admin_token):
    reset = api_client.post(
        f"{api_base_url}/api/admin/demo/reset",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=120,
    )
    assert reset.status_code == 200
    reset_data = reset.json()
    assert reset_data["deleted_records"] >= 0
    assert reset_data["message"] == "Demo records cleared"

    after_reset = api_client.get(
        f"{api_base_url}/api/admin/demo-logins",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=30,
    )
    assert after_reset.status_code == 200
    reset_rows = after_reset.json()
    assert len(reset_rows) == 1
    assert reset_rows[0]["role"] == "admin"

    reseed = api_client.post(
        f"{api_base_url}/api/admin/demo/reset-reseed",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=300,
    )
    assert reseed.status_code == 200

    after_reseed = api_client.get(
        f"{api_base_url}/api/admin/demo-logins",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=40,
    )
    assert after_reseed.status_code == 200
    reseed_rows = after_reseed.json()
    assert len(reseed_rows) > 1
    assert any(item["role"] == "user" for item in reseed_rows)


def test_admin_analytics_monthly_and_kpis_shape(api_client, api_base_url, admin_token):
    analytics = api_client.get(
        f"{api_base_url}/api/admin/analytics",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=40,
    )
    assert analytics.status_code == 200
    data = analytics.json()

    assert isinstance(data["assignment_completion_rate"], (int, float))
    assert 0 <= data["assignment_completion_rate"] <= 100
    assert isinstance(data["active_subscriptions"], int)
    assert isinstance(data["total_revenue_inr"], int)

    monthly = data["monthly"]
    assert isinstance(monthly, list)
    assert len(monthly) == 6
    for item in monthly:
        assert len(item["month"]) == 7
        assert isinstance(item["bookings"], int)
        assert isinstance(item["revenue_inr"], int)
        assert isinstance(item["renewals_due"], int)


def test_regression_admin_auth_booking_contact_subscription_worker_gate(api_client, api_base_url, admin_token):
    overview = api_client.get(
        f"{api_base_url}/api/admin/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=40,
    )
    assert overview.status_code == 200
    overview_data = overview.json()
    assert "bookings" in overview_data and isinstance(overview_data["bookings"], list)
    assert "stats" in overview_data and isinstance(overview_data["stats"], dict)

    identity = _mk_identity("regression")
    preferred_date = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()

    booking = api_client.post(
        f"{api_base_url}/api/bookings",
        json={
            "full_name": identity["name"],
            "phone": identity["phone"],
            "email": identity["email"],
            "service_type": "Cleaning",
            "address": "TEST address, Bengaluru",
            "preferred_date": preferred_date,
            "notes": "Regression booking",
        },
        timeout=40,
    )
    assert booking.status_code == 200
    booking_data = booking.json()
    assert booking_data["status"] == "pending"

    contact = api_client.post(
        f"{api_base_url}/api/contacts",
        json={
            "name": identity["name"],
            "email": identity["email"],
            "phone": identity["phone"],
            "message": "TEST contact message",
        },
        timeout=30,
    )
    assert contact.status_code == 200
    contact_data = contact.json()
    assert contact_data["email"] == identity["email"]

    user_status = api_client.get(
        f"{api_base_url}/api/subscriptions/user-status",
        params={"phone": identity["phone"], "email": identity["email"]},
        timeout=30,
    )
    assert user_status.status_code == 200
    user_status_data = user_status.json()
    assert isinstance(user_status_data["bookings_used"], int)

    worker_status = api_client.get(
        f"{api_base_url}/api/subscriptions/worker-status",
        params={"phone": identity["phone"], "email": identity["email"]},
        timeout=30,
    )
    assert worker_status.status_code == 200
    assert worker_status.json()["has_active_subscription"] is False

    worker_signup = api_client.post(
        f"{api_base_url}/api/workers/signup",
        json={
            "full_name": identity["name"],
            "phone": identity["phone"],
            "email": identity["email"],
            "skill": "Plumbing",
            "city": "TEST City",
            "years_experience": 4,
            "availability": "Part-time",
            "about": "Regression worker signup path",
        },
        timeout=35,
    )
    assert worker_signup.status_code == 402
    worker_gate = worker_signup.json()["detail"]
    assert worker_gate["code"] == "WORKER_SUBSCRIPTION_REQUIRED"
