import sqlite3
from typing import Any

from ag_ui_strands import StrandsAgent
from strands import Agent, tool

from app.approvals import ApprovalStore
from app.config import Settings
from app.database import EmployeeRepository
from app.model_provider import build_language_model
from app.schemas import EmployeeCreate


def build_employee_operations_agent(
    repository: EmployeeRepository, approvals: ApprovalStore, settings: Settings
) -> StrandsAgent:
    @tool
    def search_employees(query: str = "", department: str = "") -> list[dict[str, Any]]:
        """Search employees by name, role, email, or department."""
        return [
            employee.model_dump(mode="json")
            for employee in repository.list_employees(query, department)
        ]

    @tool
    def get_employee_details(employee_id: int) -> dict[str, Any]:
        """Get the full details for one employee ID."""
        employee = repository.get_employee(employee_id)
        if employee is None:
            return {"found": False, "message": "Employee not found."}
        return {"found": True, "employee": employee.model_dump(mode="json")}

    @tool
    def get_department_summary() -> list[dict[str, Any]]:
        """Get the authoritative employee count for every department."""
        return [item.model_dump() for item in repository.department_summary()]

    @tool
    def create_employee(
        name: str,
        email: str,
        department: str,
        designation: str,
        joining_date: str,
        confirmation_token: str,
    ) -> dict[str, Any]:
        """Create an employee only after the browser has issued a matching confirmation token."""
        employee = EmployeeCreate.model_validate(
            {
                "name": name,
                "email": email,
                "department": department,
                "designation": designation,
                "joining_date": joining_date,
            }
        )
        if not approvals.consume(
            confirmation_token,
            "create",
            None,
            employee.model_dump(mode="json"),
        ):
            return {
                "success": False,
                "message": "Confirmation is missing, expired, already used, or does not match the employee details.",
            }
        try:
            created = repository.create_employee(employee)
        except sqlite3.IntegrityError:
            return {"success": False, "message": "An employee with this email already exists."}
        return {"success": True, "employee": created.model_dump(mode="json")}

    instructions = """You are the Employee Operations Hub assistant.

Help users work with the employee directory accurately and concisely. Use backend tools for
employee facts and frontend tools for visible interface changes. Do not invent employee data.

For a new employee, collect a valid name, email, department, designation, and joining date.
Open and fill the form, request user confirmation, and create the employee only after approval.
Refresh the directory after a successful creation. If the user asks not to save, fill the form
without requesting confirmation. Use the department summary tool before rendering a summary."""
    return StrandsAgent(
        Agent(
            model=build_language_model(settings),
            system_prompt=instructions,
            tools=[search_employees, get_employee_details, get_department_summary, create_employee],
        ),
        name="employee_operations",
    )
