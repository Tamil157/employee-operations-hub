# Employee Operations Hub API

Run the local API from this directory:

```powershell
uv sync --all-groups
uv run uvicorn app.main:app --reload --port 8000
```

The SQLite database defaults to `data/employees.db`. Override it with `DATABASE_PATH` in a local `.env` file.
