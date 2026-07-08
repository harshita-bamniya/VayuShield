# Running VayuShield AI Locally

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

That's it. No Python, no Node, no Postgres to install separately.

---

## Start everything

```bash
cd E:\GalaxyWeblinks\Hackathon\vayushield-ai
docker-compose up --build
```

This starts 4 services:
| Service | URL |
|---|---|
| Frontend (React) | http://localhost:5173 |
| Backend API | http://localhost:8000/api/docs |
| TimescaleDB (Postgres) | localhost:5432 |
| Redis | localhost:6379 |

First run takes ~3–5 minutes to pull images and build. Subsequent runs are fast.

---

## Login

Once running, open http://localhost:5173 and sign in with:

```
Email:    admin@vayushield.local
Password: Admin@123
```

---

## Stop everything

```bash
docker-compose down
```

To also wipe the database (fresh start):

```bash
docker-compose down -v
```

---

## Common issues

**Port already in use**
Something else is using port 5173 or 8000. Stop it, or edit the ports in `docker-compose.yml`.

**Frontend shows blank page**
Wait a few more seconds — Vite's dev server starts after the backend. Hard-refresh (Ctrl+Shift+R).

**"relation users does not exist"**
Migrations didn't run. Restart with `docker-compose down -v && docker-compose up --build`.
