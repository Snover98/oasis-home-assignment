# Project: Oasis Home Assignment - NHI Ticket System

This project contains a FastAPI backend, a React frontend, and Redis-backed application state.

## Development

See [README.md](README.md) for the main project overview and startup instructions.

### Preferred Runtime

Use Docker Compose from the repository root:

```bash
docker compose up --build
```

This starts:
- frontend on `http://localhost:5173`
- backend on `http://localhost:8000`
- redis on `localhost:6379`

### Legacy Local Run

Backend:

```bash
cd backend
uv sync
uv run --env-file .env uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Redis must be available unless `REDIS_URL` is overridden.

## Python Standards

- Style: Follow PEP 8.
- Docstrings: Add or update docstrings for new or modified functions.
- Testing: This project includes automated backend and frontend tests. Add or update tests with behavior changes.
- Type hints: Use builtins where possible and prefer `|` over `typing.Union`.
- `main` function: code under `if __name__ == "__main__":` should call a `main()` function.
- Use the `uv` package manager for Python code.

## TypeScript Standards

### Naming Conventions

- Files: `kebab-case`
- Types and interfaces: `PascalCase`
- Functions and variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Enums: `PascalCase`

### Type Safety

- `strict: true` is enabled.
- Avoid `any`; prefer `unknown` with narrowing.
- Define explicit return types for exported functions.
- Use `interface` for public API definitions and `type` for unions/intersections.

### Best Practices

- Prefer `const` over `let`; never use `var`.
- Prefer `undefined` over `null` unless an external API requires `null`.
- Use optional chaining and nullish coalescing.
- Prefer `async/await` over `.then()` chains.

## Testing

Backend:

```bash
cd backend
uv run pytest
```

Frontend e2e:

```bash
cd frontend
npm run test:e2e
```

Frontend component tests:

```bash
cd frontend
npm run test:component
```

## Tool Usage Guidelines

When using documentation and code example retrieval:

- Resolve the Context7 library ID before querying docs unless a valid `/org/project` ID is already provided.
- Keep queries specific so the retrieved guidance is directly useful.
