from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Department = Literal["Engineering", "HR", "Finance", "Sales"]


class EmployeeBase(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z][A-Za-z .'-]*$")
    email: EmailStr
    department: Department
    designation: str = Field(
        min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9 .,&()/-]*$"
    )
    joining_date: date


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=120, pattern=r"^[A-Za-z][A-Za-z .'-]*$"
    )
    email: EmailStr | None = None
    department: Department | None = None
    designation: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9 .,&()/-]*$",
    )
    joining_date: date | None = None


class Employee(EmployeeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class EmployeeList(BaseModel):
    items: list[Employee]
    total: int


class DepartmentSummary(BaseModel):
    department: Department
    count: int


class HealthStatus(BaseModel):
    status: Literal["ok"]
    database: Literal["ready"]


class RuntimeConfiguration(BaseModel):
    provider: str
    provider_label: str
    model: str


class ApprovalRequest(BaseModel):
    action: Literal["create", "update", "delete"]
    employee_id: int | None = Field(default=None, gt=0)
    payload: dict[str, Any] = Field(default_factory=dict)
