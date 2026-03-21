# Oasis NHI Ticket System Backend

This is the FastAPI backend for the Oasis NHI Ticket System.

## Running the Application

### Development (Docker Compose)

From the repository root:

```bash
docker compose up --build
```

The backend will be available on `http://localhost:8000` and will connect to the compose-managed Redis service.

### Development (CLI)

To run the application using `uv` and automatically load the environment variables from your `.env` file, use the following command from the `backend` directory:

```bash
uv run --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or you can execute the main script:

```bash
uv run --env-file .env python app/main.py
```

### Development (VS Code)

If you are using Visual Studio Code, you can use the "Backend: Uvicorn" run configuration. It is pre-configured in `.vscode/launch.json` to load the `.env` file automatically via the `"envFile"` property.
