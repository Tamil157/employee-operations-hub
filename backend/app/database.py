import sqlite3
from collections.abc import Iterable
from pathlib import Path

from app.schemas import DepartmentSummary, Employee, EmployeeCreate, EmployeeUpdate

SEED_EMPLOYEES = (
    ("Aisha Patel", "aisha.patel@example.com", "Engineering", "Senior Engineer", "2023-01-15"),
    ("Rohan Mehta", "rohan.mehta@example.com", "Engineering", "Product Engineer", "2024-04-08"),
    ("Maya Iyer", "maya.iyer@example.com", "HR", "People Partner", "2022-07-21"),
    ("Vikram Shah", "vikram.shah@example.com", "Finance", "Finance Analyst", "2023-10-11"),
    ("Neha Kapoor", "neha.kapoor@example.com", "Sales", "Account Executive", "2024-02-19"),
)


class EmployeeRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    department TEXT NOT NULL CHECK(
                        department IN ('Engineering', 'HR', 'Finance', 'Sales')
                    ),
                    designation TEXT NOT NULL,
                    joining_date TEXT NOT NULL
                )
                """
            )
            count = connection.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
            if count == 0:
                connection.executemany(
                    """
                    INSERT INTO employees (name, email, department, designation, joining_date)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    SEED_EMPLOYEES,
                )

    @staticmethod
    def _employee(row: sqlite3.Row) -> Employee:
        return Employee.model_validate(dict(row))

    def list_employees(self, query: str | None, department: str | None) -> list[Employee]:
        clauses: list[str] = []
        params: list[str] = []
        if query:
            clauses.append("(name LIKE ? OR email LIKE ? OR designation LIKE ?)")
            wildcard = f"%{query.strip()}%"
            params.extend([wildcard, wildcard, wildcard])
        if department:
            clauses.append("department = ?")
            params.append(department)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM employees{where} ORDER BY joining_date DESC, id DESC", params
            ).fetchall()
        return [self._employee(row) for row in rows]

    def get_employee(self, employee_id: int) -> Employee | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()
        return self._employee(row) if row else None

    def create_employee(self, employee: EmployeeCreate) -> Employee:
        values = employee.model_dump(mode="json")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO employees (name, email, department, designation, joining_date)
                VALUES (:name, :email, :department, :designation, :joining_date)
                """,
                values,
            )
            row = connection.execute(
                "SELECT * FROM employees WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return self._employee(row)

    def update_employee(self, employee_id: int, employee: EmployeeUpdate) -> Employee | None:
        changes = employee.model_dump(mode="json", exclude_none=True)
        if not changes:
            return self.get_employee(employee_id)
        columns = ", ".join(f"{column} = :{column}" for column in changes)
        changes["employee_id"] = employee_id
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE employees SET {columns} WHERE id = :employee_id", changes
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT * FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()
        return self._employee(row)

    def delete_employee(self, employee_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        return cursor.rowcount > 0

    def department_summary(self) -> list[DepartmentSummary]:
        with self._connect() as connection:
            rows: Iterable[sqlite3.Row] = connection.execute(
                "SELECT department, COUNT(*) AS count "
                "FROM employees GROUP BY department ORDER BY department"
            ).fetchall()
        return [DepartmentSummary.model_validate(dict(row)) for row in rows]
