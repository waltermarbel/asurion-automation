# Service: dashboard (Planned)

> Status: NOT IMPLEMENTED – This is the design contract.

## Role

Web UI for:

- Monitoring ingest, valuation, and claim queues.
- Reviewing `MANUAL_REVIEW` devices.
- Exporting CSV reports of payouts, per-policy performance, etc.

## Proposed Stack

- Frontend: Any SPA (React / Vue / Svelte).
- Backend: Serves static assets, calls `api_gateway` for data.
- Port: `3000` internal.

## Core Screens

1. **Overview**

   - Cards for counts: INGESTED / VALUATED / MANUAL_REVIEW / CLAIMED.
   - Recent activity pulled from `system_log`.

2. **Devices**

   - Table with filters: brand, category, status.
   - Actions: re-run valuation, mark as resolved.

3. **Claims**

   - Table: device, payout, PDF filename, status.
   - Link to download claim PDF.

4. **Logs**
   - Recent `system_log` entries with search filter.

## Healthcheck

Expose `GET /healthz`:

- Returns `200 OK` JSON when the UI server is up.
- In production, may also proxy `api_gateway` health.

Docker healthcheck (when implemented):

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fsS http://localhost:3000/healthz || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
```
