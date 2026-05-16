# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation & Reference

**Helm plugin documentation** (authoritative, read this first):
- `C:\Users\jerry\PycharmProjects\Helm-docs\docs\plugin-dev\` — full plugin development guide (01–17)
- `C:\Users\jerry\PycharmProjects\Helm-docs\docs\downloads\helm-plugin-dev\references\api.md` — exact API signatures

If the docs don't answer the question, the Helm source is at `C:\Users\jerry\PycharmProjects\Helm` (read sparingly).

**ESI（EVE Swagger Interface）参考文档**：`C:\Users\jerry\PycharmProjects\Helm\Markdown\esi-docs-main` — 查询 ESI 端点、参数、返回结构时在此查阅。

A complete reference plugin is at `C:\Users\jerry\PycharmProjects\Helm_Plugin\helm-plugin-MCP` — read it to see a real-world example of router, permissions, sidebar, frontend, ExtensionRegistry, and lifecycle hooks all wired together.

## Plugin Architecture

Helm plugins run inside the shared virtualenv of the Helm FastAPI backend. No server restart is needed to install/enable/disable plugins; only Celery tasks require a worker soft-restart.

Every plugin is a pip package with an entry point in group `helm.plugins`:

```toml
[project.entry-points."helm.plugins"]
{name} = "{pkg_name}.plugin:{ClassName}Plugin"
```

The plugin class inherits `HelmPlugin` from `app.plugins.base` and declares its capabilities by overriding methods:

| Method | Provides |
|--------|----------|
| `get_router()` | FastAPI `APIRouter` mounted at `/api/v1/plugins/{name}/` |
| `get_tasks()` | List of module paths for Celery task autodiscovery |
| `get_permissions()` | `PermissionDef` list seeded into RBAC on install |
| `get_esi_scopes()` | EVE SSO OAuth scopes the plugin requires |
| `get_sidebar_items()` | `SidebarItem` entries injected into the UI nav |
| `get_static_dir()` | `Path` to `frontend/dist/` served at `/plugin-ui/{name}/` |
| `get_frontend_dev_url()` | Dev server URL (set `None` before publishing) |
| `on_enable(ctx)` | Called on install/enable — use for ExtensionRegistry registration |
| `on_disable(ctx)` | Called on disable/uninstall — cancel SSE/async resources here |

**Frontend model**: Helm wraps each plugin in an `<iframe sandbox="allow-scripts allow-same-origin allow-forms">`. The iframe loads the plugin's `dist/index.html`, which must load `/plugin-sdk/helm-sdk.js` and call `HelmSDK.init(cb)` to receive `{ token, apiBase }`. Never use `alert()`, `confirm()`, `prompt()`, or `window.open()` — they are blocked by the sandbox.

**Inter-plugin communication**: Use `extension_registry` from `app.plugins.registry`. Providers call `extension_registry.register(point_name, impl, plugin_name)` in `on_enable`; consumers call `extension_registry.get_all(point_name)`.

**Database**: Each plugin manages its own Alembic migrations under `{pkg_name}/migrations/`. Plugin models must define their own `Base = DeclarativeBase()` — never reuse Helm core's Base.

## Local Testing

```bash
# 1. Install in editable mode
pip install -e ./helm-plugin-{name}

# 2. Register with the running backend
curl -X POST http://localhost:8000/api/v1/admin/plugins/install \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"package_name": "helm-plugin-{name}"}'

# 3. Check status
curl http://localhost:8000/api/v1/admin/plugins/{name}/status \
  -H "Authorization: Bearer <jwt>"
# Expected: {"status": "enabled", "is_loaded": true, "router_mounted": true}

# 4. Verify endpoints
curl http://localhost:8000/api/v1/plugins/{name}/{endpoint} \
  -H "Authorization: Bearer <jwt>"

# 5. Frontend (if applicable)
curl http://localhost:8000/plugin-sdk/helm-sdk.js     # → 200
curl http://localhost:8000/plugin-ui/{name}/index.html # → 200
# Browser: http://localhost:5173/plugins/{name}

# Disable / re-enable
curl -X POST http://localhost:8000/api/v1/admin/plugins/{name}/disable -H "Authorization: Bearer <jwt>"
curl -X POST http://localhost:8000/api/v1/admin/plugins/{name}/enable  -H "Authorization: Bearer <jwt>"

# Uninstall
curl -X DELETE "http://localhost:8000/api/v1/admin/plugins/{name}?pip_remove=false" \
  -H "Authorization: Bearer <jwt>"
```

For frontend hot-reload, set `get_frontend_dev_url()` to `"http://localhost:5174"` and run `npm run dev` inside `{pkg_name}/frontend/`. Helm auto-points the iframe at the dev server when `app_env=development`.

## Key Constraints

- Router: use `APIRouter` only — never `FastAPI()`
- Tasks: use `from app.tasks.celery_app import celery_app` — never `Celery()`
- `helm_sdk_version = ">=1.0,<2.0"` must be set on every plugin class
- `SidebarItem.route` must be the full path: `/plugins/{name}`
- Entry point format: `{key} = "{module}.{path}:{ClassName}"` (colon before class name)
- Package data must include `"frontend/dist/**"` if the plugin ships a frontend
