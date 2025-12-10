# Service: db (The Vault)

## Role

PostgreSQL database for Gemini Gem. Single source of truth for:

- `devices` – inventory & status
- `claims` – generated claims
- `policies` / `policy_rules` – coverage logic
- `system_log` – forensic audit trail

## Ports

- Internal: `5432`
- Exposed: `5432` on host (for admin tools like `psql`, DBeaver, etc.)

## Startup

Database is launched via `docker-compose`:

```bash
cd ~/gemini_gem
docker-compose up -d db
```

The init.sql file is automatically executed on first run (schema + seed data).

## Healthcheck

Health is defined in docker-compose.yml:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U gem_admin -d gemini_gem"]
  interval: 10s
  timeout: 5s
  retries: 5
```

You can check status:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

When healthy, db shows healthy in the status.

## Admin Access

Inside the container:

```bash
docker exec -it gemini_gem_db_1 psql -U gem_admin -d gemini_gem
```

(Adjust container name if different.)

Use this to run ad-hoc queries, inspect tables, or debug.
