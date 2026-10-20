import sqlite3
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.agent import build_employee_operations_agent
from app.approvals import ApprovalStore
from app.config import Settings
from app.database import EmployeeRepository
from app.schemas import (
    ApprovalRequest,
    DepartmentSummary,
    Employee,
    EmployeeCreate,
    EmployeeList,
    EmployeeUpdate,
    HealthStatus,
    RuntimeConfiguration,
)

settings = Settings()
repository = EmployeeRepository(settings.database_path)
approvals = ApprovalStore()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    repository.initialize()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started_at = time.perf_counter()
        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time-ms"] = str(
            round((time.perf_counter() - started_at) * 1000, 1)
        )
        return response

    @app.get("/health", response_model=HealthStatus)
    def health() -> HealthStatus:
        return HealthStatus(status="ok", database="ready")

    @app.get("/api/runtime/config", response_model=RuntimeConfiguration)
    def runtime_configuration() -> RuntimeConfiguration:
        return RuntimeConfiguration(
            provider=settings.llm_provider,
            provider_label=settings.provider_label,
            model=settings.llm_model,
        )

    @app.get("/api/employees", response_model=EmployeeList)
    def list_employees(query: str | None = None, department: str | None = None) -> EmployeeList:
        employees = repository.list_employees(query, department)
        return EmployeeList(items=employees, total=len(employees))

    @app.get("/api/employees/{employee_id}", response_model=Employee)
    def get_employee(employee_id: int) -> Employee:
        employee = repository.get_employee(employee_id)
        if not employee:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return employee

    @app.post("/api/employees", response_model=Employee, status_code=status.HTTP_201_CREATED)
    def create_employee(
        employee: EmployeeCreate, x_confirmation_token: str | None = Header(default=None)
    ) -> Employee:
        if not x_confirmation_token or not approvals.consume(
            x_confirmation_token,
            "create",
            None,
            employee.model_dump(mode="json"),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A valid one-time confirmation is required before creating an employee",
            )
        try:
            return repository.create_employee(employee)
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An employee with this email already exists",
            ) from error

    @app.post("/api/approvals")
    def issue_approval(request: ApprovalRequest) -> dict[str, str]:
        if request.action == "create" and request.employee_id is not None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Create has no employee ID")
        if request.action in {"update", "delete"} and request.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{request.action.title()} requires an employee ID",
            )
        return {
            "confirmation_token": approvals.issue(
                request.action, request.employee_id, request.payload
            )
        }

    @app.patch("/api/employees/{employee_id}", response_model=Employee)
    def update_employee(
        employee_id: int,
        employee: EmployeeUpdate,
        x_confirmation_token: str | None = Header(default=None),
    ) -> Employee:
        payload = employee.model_dump(mode="json", exclude_none=True)
        if not x_confirmation_token or not approvals.consume(
            x_confirmation_token, "update", employee_id, payload
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A valid one-time confirmation is required before updating an employee",
            )
        try:
            updated = repository.update_employee(employee_id, employee)
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An employee with this email already exists",
            ) from error
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return updated

    @app.delete("/api/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_employee(
        employee_id: int, x_confirmation_token: str | None = Header(default=None)
    ) -> Response:
        if not x_confirmation_token or not approvals.consume(
            x_confirmation_token, "delete", employee_id, {}
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A valid one-time confirmation is required before deleting an employee",
            )
        if not repository.delete_employee(employee_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/departments/summary", response_model=list[DepartmentSummary])
    def department_summary() -> list[DepartmentSummary]:
        return repository.department_summary()

    from ag_ui_strands import add_strands_fastapi_endpoint

    add_strands_fastapi_endpoint(
        app, build_employee_operations_agent(repository, approvals, settings), "/agent"
    )
    return app


app = create_app()
