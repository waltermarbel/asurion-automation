# Service: api_gateway (Planned)

> Status: NOT IMPLEMENTED – This is the design contract.

## Role

HTTP API layer in front of Gemini Gem to:

- Expose inventory (`devices`) and claims (`claims`) over REST/JSON.
- Provide endpoints for:
  - Repair shops to submit device JSON.
  - Admins to review and approve manual review items.
- Act as evolution point towards multi-tenant, multi-policy CaaS.

## Proposed Stack

- Language: Node.js (Express / Fastify) or Python (FastAPI).
- Port: `8080` internal, optionally exposed to host or behind a reverse proxy.

## Proposed Endpoints

- `GET /healthz`
  Returns API health + DB connectivity.

- `POST /v1/devices`
  Accepts one or more devices in JSON; inserts into `devices` table (or queues them).

- `GET /v1/devices/:device_id`
  Fetch single device status and pricing.

- `GET /v1/claims/:claim_id`
  Fetch claim metadata and generated PDF filename.

- `POST /v1/claims/:device_id/trigger`
  Manually trigger claim generation for a specific device.

## Healthcheck

When implemented, docker healthcheck should probe:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fsS http://localhost:8080/healthz || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```

This keeps the pattern consistent across the microservices.
