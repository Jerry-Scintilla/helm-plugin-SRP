# helm-plugin-srp

A [Helm](https://github.com/jerrysmh/helm) plugin that adds a full **Ship Replacement Program (SRP)** system to EVE Online fleet organizations — covering request submission, officer review, market-based pricing, PAP fleet quick-submit, and optional AI assistant integration via [helm-plugin-mcp](https://github.com/jerrysmh/helm-plugin-mcp).

> **Status**: Alpha. No official releases yet. Contributions and forks are welcome.

---

## Features

| Feature | Description |
|---------|-------------|
| **ESI Killmail Input** | Accepts official ESI killmail URLs copied directly from in-game (`https://esi.evetech.net/killmails/{id}/{hash}`) |
| **Market Pricing** | Queries EVE market orders (configurable region + buy/sell) to calculate reimbursement value |
| **Preview Before Submit** | Players see ship name, raw loss value, computed payout, and eligibility check before committing |
| **PAP Fleet Quick-Submit** | Fetches the player's PAP records, shows all losses during that fleet window, and allows one-click batch submission |
| **Fleet Action Integration** | Accepts `?fleet_action=<id>` URL parameter for deep-link submission from fleet MOTD |
| **Officer Management UI** | Officers review all requests with status filter (pending / approved / rejected / paid), approve, reject, or mark as paid |
| **Configurable Policy** | Price region, order type (buy/sell), payout coefficient, minimum loss threshold, eligible ship groups |
| **MCP AI Integration** | Optionally exposes 6 tools to AI assistants via `helm-plugin-mcp` |
| **MOTD Fragment** | Provides the `srp.motd_fragment` extension point for `helm-plugin-fleet-action` to auto-insert SRP links in fleet MOTD |

---

## Requirements

- Python >= 3.12
- Helm >= 1.0
- `helm-plugin-fleet-action` *(optional — enables PAP quick-submit tab)*
- `helm-plugin-mcp` *(optional — enables AI assistant tools)*

---

## Installation

```bash
# 1. Install the Python package (editable for development)
pip install -e /path/to/helm-plugin-srp

# 2. Register with the running Helm backend
curl -X POST http://localhost:8000/api/v1/admin/plugins/install \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"package_name": "helm-plugin-srp"}'

# 3. Verify
curl http://localhost:8000/api/v1/admin/plugins/srp/status \
  -H "Authorization: Bearer <jwt>"
# Expected: {"status": "enabled", "is_loaded": true, "router_mounted": true}
```

---

## Quick Start

### 1. Grant permissions

Assign the following permissions to the appropriate roles in Helm's RBAC system:

| Permission | Who needs it |
|------------|--------------|
| `srp.submit` | All line members who may submit requests |
| `srp.officer` | SRP officers who approve/reject requests and mark payments |
| `srp.admin` | Administrators who configure the SRP system |

### 2. Configure payout policy

Navigate to **🛡️ 舰船补损** in the sidebar → **⚙️ 配置** tab (requires `srp.admin`):

| Setting | Default | Description |
|---------|---------|-------------|
| Price Region ID | `10000002` (The Forge / Jita) | EVE market region for price queries |
| Order Type | `buy` | Use buy-order or sell-order prices |
| Coefficient | `1.0` | Multiply market price by this factor for payout |
| Minimum Loss | `0 ISK` | Requests below this value are auto-rejected |
| Eligible Ship Groups | *(all)* | Restrict SRP to specific ship group IDs |

### 3. Submit an SRP request

Open the **🏅 PAP 舰队补损** tab (if you have PAP records) to batch-submit from a fleet, or the **📋 我的申请** tab to submit manually:

1. Paste an ESI killmail URL from in-game: `https://esi.evetech.net/killmails/{id}/{hash}…`
2. Click **预览补损金额** to see the calculated payout
3. Select the character and click **确认提交**

### 4. Review requests (officers)

Open the **🛡️ 补损管理** tab (requires `srp.officer`):

- Use the status dropdown to filter by pending / approved / rejected / paid
- Click **批准** or **拒绝** on pending requests (rejection supports a reason note)
- Click **标记已付款** on approved requests once ISK has been transferred

---

## Permissions

| Permission | Scope | Description |
|------------|-------|-------------|
| `srp.submit` | global | Submit SRP requests and use PAP quick-submit |
| `srp.officer` | global | Approve, reject, and mark requests as paid |
| `srp.admin` | global | View and modify SRP configuration |

---

## ESI Scopes Required

| Scope | Purpose |
|-------|---------|
| `esi-killmails.read_killmails.v1` | Fetch the character's recent kills for PAP quick-submit |

---

## API Endpoints

All endpoints are mounted under `/api/v1/plugins/srp/`:

| Method | Path | Permission | Description |
|--------|------|------------|-------------|
| `GET` | `/me` | authenticated | Current user's SRP permission flags |
| `GET` | `/config` | `srp.admin` | View current SRP configuration |
| `PUT` | `/config` | `srp.admin` | Update SRP configuration |
| `GET` | `/killmail/preview` | `srp.submit` | Preview reimbursement for an ESI killmail URL |
| `POST` | `/requests` | `srp.submit` | Submit a new SRP request |
| `GET` | `/requests` | authenticated | List requests (officers see all, players see own) |
| `GET` | `/requests/{id}` | authenticated | Get request detail |
| `POST` | `/requests/{id}/approve` | `srp.officer` | Approve a pending request |
| `POST` | `/requests/{id}/reject` | `srp.officer` | Reject a pending request |
| `POST` | `/requests/{id}/mark_paid` | `srp.officer` | Mark an approved request as paid |
| `GET` | `/my-pap-fleets` | `srp.submit` | List PAP fleet records for the current user |
| `GET` | `/fleet/{fleet_action_id}/kills` | `srp.submit` | List character losses during a fleet action window |

---

## MCP Tool Integration

When `helm-plugin-mcp` is installed, SRP automatically registers 6 AI-accessible tools:

| Tool | Permission | Description |
|------|------------|-------------|
| `srp_get_config` | `srp.admin` | Retrieve current SRP configuration |
| `srp_preview_killmail` | `srp.submit` | Preview payout for a given killmail |
| `srp_submit_request` | `srp.submit` | Submit an SRP request |
| `srp_list_requests` | authenticated | List requests with optional status / character filter |
| `srp_get_request` | authenticated | Get full detail of a single request |
| `srp_review_request` | `srp.officer` | Approve, reject, or mark a request as paid |

No configuration is needed — the tools appear automatically in the AI client's tool list when the user has the required permissions.

---

## Extension Points

### Provided: `srp.motd_fragment`

Consumed by `helm-plugin-fleet-action` to inject an SRP quick-submit link into the fleet MOTD when PAP is issued:

```
[SRP补损] https://your-helm-host/plugins/srp?fleet_action=<id>
```

### Consumed: `mcp.tool_provider`

Registers `SrpMCPToolProvider` with `helm-plugin-mcp` if it is installed. Import failure (MCP not installed) is silently ignored.

---

## Plugin Structure

```
helm_plugin_srp/
├── plugin.py           # Entry point — permissions, sidebar, lifecycle hooks
├── routers.py          # FastAPI router — all REST endpoints
├── models.py           # SQLAlchemy models (SrpRequest, SrpConfig, SrpStatus)
├── schemas.py          # Pydantic request / response schemas
├── tool_provider.py    # MCP tool provider (SrpMCPToolProvider)
├── services/
│   ├── killmail.py     # ESI killmail URL parsing + data fetching
│   ├── pricing.py      # Market price queries + payout calculation
│   └── esi.py          # ESI OAuth token management + authenticated requests
├── frontend/
│   └── dist/
│       └── index.html  # Single-file frontend (vanilla JS, inline)
└── migrations/         # Alembic database migrations
```

---

## Database

The plugin manages its own tables via Alembic migrations:

| Table | Description |
|-------|-------------|
| `srp_requests` | One row per SRP request — killmail info, computed payout, status, review metadata |
| `srp_configs` | Key-value configuration store |

Migrations run automatically on plugin install/enable via Helm's plugin lifecycle.

---

## Status

**Alpha** — Under active development. No official releases yet. The API and database schema may change without notice.

---

## Contributing

Contributions are welcome. Fork the repository, create a feature branch, and open a pull request.

---

## License

MIT License
