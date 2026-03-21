# Oasis NHI Ticket System Frontend

This is the React + TypeScript + Vite frontend for the Oasis NHI Ticket System.

## Development

### Preferred: Docker Compose

From the repository root:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

The frontend will be available at `http://localhost:5173`.

### Legacy Local Run

From the `frontend` directory:

```bash
npm install
cp .env.example .env
npm run dev
```

By default, the frontend talks to the backend at `http://localhost:8000` using `VITE_API_BASE_URL` from `.env`.

## Testing

### End-to-End Tests

```bash
npm run test:e2e
```

### Component Tests

```bash
npm run test:component
```

## Build

```bash
npm run build
```

## Notes

- The frontend expects the backend to be reachable from the browser on `http://localhost:8000`.
- In Docker Compose, the browser still uses `localhost`, even though the frontend container runs inside the compose network.
