from datetime import datetime, timedelta, timezone


def task_payload(**overrides):
    payload = {
        "title": "Review case bundle",
        "description": "Check the latest documents before the hearing.",
        "status": "todo",
        "due_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_retrieve_task(client):
    created = client.post("/api/tasks", json=task_payload())
    assert created.status_code == 201
    task = created.json()
    assert task["id"] == 1
    assert task["title"] == "Review case bundle"
    assert task["status"] == "todo"
    assert task["due_at"].endswith("Z")

    retrieved = client.get(f"/api/tasks/{task['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == task


def test_list_tasks_and_filter_by_status(client):
    client.post("/api/tasks", json=task_payload(title="First task"))
    client.post(
        "/api/tasks",
        json=task_payload(title="Second task", status="in_progress"),
    )

    all_tasks = client.get("/api/tasks")
    in_progress = client.get("/api/tasks", params={"status": "in_progress"})

    assert all_tasks.status_code == 200
    assert len(all_tasks.json()) == 2
    assert len(in_progress.json()) == 1
    assert in_progress.json()[0]["title"] == "Second task"


def test_update_task_fields_and_status(client):
    task_id = client.post("/api/tasks", json=task_payload()).json()["id"]

    response = client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "Updated case bundle", "status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated case bundle"
    assert response.json()["status"] == "completed"


def test_status_endpoint(client):
    task_id = client.post("/api/tasks", json=task_payload()).json()["id"]
    response = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_delete_task(client):
    task_id = client.post("/api/tasks", json=task_payload()).json()["id"]
    deleted = client.delete(f"/api/tasks/{task_id}")
    retrieved = client.get(f"/api/tasks/{task_id}")

    assert deleted.status_code == 204
    assert retrieved.status_code == 404
    assert retrieved.json()["error"]["code"] == "not_found"


def test_missing_task_returns_consistent_not_found_error(client):
    response = client.get("/api/tasks/999")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Task 999 was not found"}
    }


def test_rejects_blank_title(client):
    response = client.post("/api/tasks", json=task_payload(title="   "))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rejects_invalid_status(client):
    response = client.post("/api/tasks", json=task_payload(status="blocked"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rejects_due_date_without_timezone(client):
    response = client.post(
        "/api/tasks",
        json=task_payload(due_at="2030-05-01T09:00:00"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_rejects_empty_update(client):
    task_id = client.post("/api/tasks", json=task_payload()).json()["id"]
    response = client.patch(f"/api/tasks/{task_id}", json={})
    assert response.status_code == 422


def test_serves_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Casework tasks" in response.text


def test_rejects_null_for_required_update_fields(client):
    task_id = client.post("/api/tasks", json=task_payload()).json()["id"]
    for field in ("title", "status", "due_at"):
        response = client.patch(f"/api/tasks/{task_id}", json={field: None})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_due_dates_are_sorted_chronologically(client):
    later = client.post(
        "/api/tasks",
        json=task_payload(title="Later", due_at="2030-05-01T09:00:00.500000+00:00"),
    )
    earlier = client.post(
        "/api/tasks",
        json=task_payload(title="Earlier", due_at="2030-05-01T09:00:00+00:00"),
    )
    assert later.status_code == earlier.status_code == 201
    tasks = client.get("/api/tasks").json()
    assert [task["title"] for task in tasks] == ["Earlier", "Later"]
