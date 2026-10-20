from fastapi.testclient import TestClient

from app.approvals import ApprovalStore
from app.database import EmployeeRepository
from app.main import app


def client_for_temporary_database(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    test_repository = EmployeeRepository(tmp_path / "employees.db")
    monkeypatch.setattr("app.main.repository", test_repository)
    monkeypatch.setattr("app.main.approvals", ApprovalStore())
    return TestClient(app)


def test_health_reports_ready_database(tmp_path, monkeypatch) -> None:
    with client_for_temporary_database(tmp_path, monkeypatch) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ready"}
    assert response.headers["x-request-id"]


def test_create_requires_one_time_confirmation_and_filters_employee(tmp_path, monkeypatch) -> None:
    payload = {
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "joining_date": "2026-10-19",
    }
    with client_for_temporary_database(tmp_path, monkeypatch) as client:
        rejected = client.post("/api/employees", json=payload)
        approval = client.post(
            "/api/approvals", json={"action": "create", "payload": payload}
        )
        created = client.post(
            "/api/employees",
            json=payload,
            headers={"X-Confirmation-Token": approval.json()["confirmation_token"]},
        )
        filtered = client.get("/api/employees?department=Engineering&query=Arun")

    assert rejected.status_code == 403
    assert approval.status_code == 200
    assert created.status_code == 201
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "arun.kumar@example.com"


def test_malformed_employee_tool_text_is_rejected(tmp_path, monkeypatch) -> None:
    payload = {
        "name": "Karthik Kumar</name> parameter mismatch",
        "email": "karthik.kumar@example.com",
        "department": "Engineering",
        "designation": "QA Engineer",
        "joining_date": "2026-11-01",
    }
    with client_for_temporary_database(tmp_path, monkeypatch) as client:
        response = client.post("/api/employees", json=payload)

    assert response.status_code == 422


def test_duplicate_email_is_rejected(tmp_path, monkeypatch) -> None:
    payload = {
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "joining_date": "2026-10-19",
    }
    with client_for_temporary_database(tmp_path, monkeypatch) as client:
        first_approval = client.post(
            "/api/approvals", json={"action": "create", "payload": payload}
        )
        client.post(
            "/api/employees",
            json=payload,
            headers={"X-Confirmation-Token": first_approval.json()["confirmation_token"]},
        )
        second_approval = client.post(
            "/api/approvals", json={"action": "create", "payload": payload}
        )
        duplicate = client.post(
            "/api/employees",
            json=payload,
            headers={"X-Confirmation-Token": second_approval.json()["confirmation_token"]},
        )

    assert duplicate.status_code == 409


def test_confirmation_token_cannot_be_reused(tmp_path, monkeypatch) -> None:
    payload = {
        "name": "Arun Kumar",
        "email": "arun.kumar@example.com",
        "department": "Engineering",
        "designation": "Software Engineer",
        "joining_date": "2026-10-19",
    }
    with client_for_temporary_database(tmp_path, monkeypatch) as client:
        approval = client.post(
            "/api/approvals", json={"action": "create", "payload": payload}
        )
        headers = {"X-Confirmation-Token": approval.json()["confirmation_token"]}
        first = client.post("/api/employees", json=payload, headers=headers)
        replay = client.post("/api/employees", json=payload, headers=headers)

    assert first.status_code == 201
    assert replay.status_code == 403
