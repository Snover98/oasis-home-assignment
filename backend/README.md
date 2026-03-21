# Oasis NHI Ticket System Backend

This is the FastAPI backend for the Oasis NHI Ticket System.

## Running the Application

### Development (Docker Compose)

From the repository root:

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

The backend will be available on `http://localhost:8000` and will connect to the compose-managed Redis service at `redis://redis:6379/0`.

### Development (CLI)

To run the application using `uv` and automatically load the environment variables from your `.env` file, use the following command from the `backend` directory:

```bash
cp .env.example .env
uv run --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or you can execute the main script:

```bash
uv run --env-file .env python app/main.py
```

The tracked `.env.example` file contains placeholders only. Put real local secrets in an untracked `backend/.env`.

For local non-Docker runs, Redis must be available at `redis://localhost:6379/0` unless `REDIS_URL` is overridden.

### Development (VS Code)

If you are using Visual Studio Code:

- Use `Docker Compose: Up` for the compose-first workflow
- Use `Backend: Uvicorn (Legacy)` only for direct local backend debugging

## Testing

Run backend tests from the `backend` directory:

```bash
uv run pytest
```
