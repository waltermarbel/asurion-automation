# Service: gem_brain (Worker / Orchestrator)

## Role

Python microservice that runs 3 continuous jobs:

1. **Ingestion Engine** – watches `/app/data/ingest`, inserts JSON entries into `devices`.
2. **Valuation Engine** – auto-fills `retail_price_estimate` via DuckDuckGo scraping and updates `devices`.
3. **Claim Engine** – generates filled PDF claims via PDFOtter and inserts rows into `claims`.

## Dependencies

- Python 3.9 (`python:3.9-slim` base image)
- Libraries from `scripts/requirements.txt`:
  - `psycopg2-binary`
  - `requests`
  - `duckduckgo-search`
  - `schedule`
  - `beautifulsoup4`

## Environment Variables

Configured in `.env` and passed via `docker-compose`:

- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`
- `PDFOTTER_TEMPLATE_ID`
- `PDFOTTER_API_KEY`
- `DRY_RUN` (`True` or `False`)
- `INGEST_DIR` (default `/app/data/ingest`)
- `PDF_OUTPUT_DIR` (default `/app/data/pdfs`)
- `SIGNATURE_FILE` (default `/app/signatures/PC.txt`)

## Startup

```bash
cd ~/gemini_gem
docker-compose up -d gem_brain
```

This will build the image (via Dockerfile) and start the service.

## Healthcheck & Monitoring

### HTTP Health Endpoint

gem_brain exposes an internal HTTP health endpoint:

- URL: `http://<VM_IP>:8000/healthz`
- Method: `GET`
- Response (200):

```json
{
  "status": "ok",
  "last_ingest_ts": "...",
  "last_valuation_ts": "...",
  "last_claim_ts": "...",
  "dry_run": false
}
```

### Container Healthcheck

Defined in docker-compose.yml:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fsS http://localhost:8000/healthz || exit 1"]
  interval: 15s
  timeout: 5s
  retries: 5
```

You can verify:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

When healthy, gem_brain shows healthy.

## Logs

Follow logs:

```bash
cd ~/gemini_gem
docker-compose logs -f gem_brain
```

Watch for:

- [Ingest] events – files processed
- [Valuation] events – prices set or manual review flags
- [Claim] events – PDFs generated or API errors
