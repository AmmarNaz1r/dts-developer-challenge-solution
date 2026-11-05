"""FastAPI application for the DTS task-management challenge."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, build_engine, build_session_factory
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskStatus, TaskStatusUpdate, TaskUpdate, utc_iso


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def now_utc() -> str:
    return utc_iso(datetime.now(timezone.utc))


def create_app(database_url: str | None = None) -> FastAPI:
    """Application factory; accepts a database URL to support isolated tests."""
    resolved_url = database_url or os.getenv("DATABASE_URL", "sqlite:///./tasks.db")
    engine = build_engine(resolved_url)
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)

    app = FastAPI(
        title="Caseworker Task Manager API",
        description=(
            "A small task-management API for creating, viewing, updating and "
            "deleting caseworker tasks. All due dates are stored in UTC."
        ),
        version="1.0.0",
    )
    app.state.engine = engine
    app.state.session_factory = session_factory

    def get_session() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "request_error"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": str(exc.detail)}},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"] if part != "body"),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Please check the submitted task details.",
                    "details": details,
                }
            },
        )

    @app.get("/api/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/tasks",
        response_model=TaskRead,
        status_code=status.HTTP_201_CREATED,
        tags=["Tasks"],
        summary="Create a task",
    )
    def create_task(payload: TaskCreate, db: Session = Depends(get_session)) -> Task:
        timestamp = now_utc()
        task = Task(
            title=payload.title,
            description=payload.description,
            status=payload.status.value,
            due_at=utc_iso(payload.due_at),
            created_at=timestamp,
            updated_at=timestamp,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @app.get(
        "/api/tasks",
        response_model=list[TaskRead],
        tags=["Tasks"],
        summary="List tasks",
    )
    def list_tasks(
        status_filter: TaskStatus | None = Query(default=None, alias="status"),
        db: Session = Depends(get_session),
    ) -> list[Task]:
        statement = select(Task).order_by(Task.due_at.asc(), Task.id.asc())
        if status_filter is not None:
            statement = statement.where(Task.status == status_filter.value)
        return list(db.scalars(statement).all())

    @app.get(
        "/api/tasks/{task_id}",
        response_model=TaskRead,
        tags=["Tasks"],
        summary="Retrieve a task by ID",
    )
    def get_task(task_id: int, db: Session = Depends(get_session)) -> Task:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} was not found")
        return task

    @app.patch(
        "/api/tasks/{task_id}",
        response_model=TaskRead,
        tags=["Tasks"],
        summary="Update task details or status",
    )
    def update_task(
        task_id: int,
        payload: TaskUpdate,
        db: Session = Depends(get_session),
    ) -> Task:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} was not found")

        changes = payload.model_dump(exclude_unset=True)
        if "status" in changes and changes["status"] is not None:
            changes["status"] = changes["status"].value
        if "due_at" in changes and changes["due_at"] is not None:
            changes["due_at"] = utc_iso(changes["due_at"])
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = now_utc()
        db.commit()
        db.refresh(task)
        return task

    @app.patch(
        "/api/tasks/{task_id}/status",
        response_model=TaskRead,
        tags=["Tasks"],
        summary="Update a task's status",
    )
    def update_task_status(
        task_id: int,
        payload: TaskStatusUpdate,
        db: Session = Depends(get_session),
    ) -> Task:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} was not found")
        task.status = payload.status.value
        task.updated_at = now_utc()
        db.commit()
        db.refresh(task)
        return task

    @app.delete(
        "/api/tasks/{task_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["Tasks"],
        summary="Delete a task",
    )
    def delete_task(task_id: int, db: Session = Depends(get_session)) -> None:
        task = db.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} was not found")
        db.delete(task)
        db.commit()
        return None

    app.mount("/assets", StaticFiles(directory=FRONTEND_ROOT), name="assets")

    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_ROOT / "index.html")

    return app


app = create_app()
