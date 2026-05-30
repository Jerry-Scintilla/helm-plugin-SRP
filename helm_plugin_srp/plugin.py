from __future__ import annotations

from pathlib import Path

from app.plugins.base import HelmPlugin, PermissionDef, PluginContext, SidebarItem
from app.plugins.registry import extension_registry


class SrpPlugin(HelmPlugin):
    name = "srp"
    version = "0.1.1"
    author = "Jerry_Scintilla"
    description = "舰船补损（SRP）管理系统，支持 zkillboard 链接解析、补损官审核和价格配置"
    helm_sdk_version = ">=1.0,<2.0"

    # ── Router ────────────────────────────────────────────────────────────────

    def get_router(self):
        from helm_plugin_srp.routers import router
        return router

    # ── Permissions ───────────────────────────────────────────────────────────

    def get_permissions(self) -> list[PermissionDef]:
        return [
            PermissionDef("srp.submit",  "global", "提交补损申请"),
            PermissionDef("srp.officer", "global", "审核补损申请（补损官）"),
            PermissionDef("srp.admin",   "global", "管理补损配置"),
        ]

    # ── ESI Scopes ────────────────────────────────────────────────────────────

    def get_esi_scopes(self) -> list[str]:
        return ["esi-killmails.read_killmails.v1"]

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def get_sidebar_items(self) -> list[SidebarItem]:
        return [SidebarItem("舰船补损", "/plugins/srp", "🛡️", order=150)]

    # ── Frontend ──────────────────────────────────────────────────────────────

    def get_static_dir(self):
        return Path(__file__).parent / "frontend" / "dist"

    def get_frontend_dev_url(self):
        return None  # 开发时改为 "http://localhost:5174"

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enable(self, ctx: PluginContext) -> None:
        """注册为 srp.motd_fragment 提供者，供 fleet-action 在 MOTD 中插入 SRP 链接。"""
        extension_registry.register("srp.motd_fragment", self, self.name)

        # 兼容 helm-plugin-mcp：将 SRP 工具暴露给 MCP 客户端（AI 代理）
        # MCP 插件未安装时静默跳过，不影响 SRP 正常功能
        try:
            from helm_plugin_srp.tool_provider import SrpMCPToolProvider
            extension_registry.register("mcp.tool_provider", SrpMCPToolProvider(), self.name)
        except ImportError:
            pass

    # ── srp.motd_fragment 实现 ────────────────────────────────────────────────

    def get_motd_fragment(self, fleet_action_id: int) -> str:
        """返回要插入舰队 MOTD 的 SRP 快捷提交链接片段。"""
        try:
            from app.core.config import settings
            base_url = getattr(settings, "public_base_url", "").rstrip("/")
        except Exception:
            base_url = ""
        if not base_url:
            base_url = "http://localhost:5173"
        return f"[SRP补损] {base_url}/plugins/srp?fleet_action={fleet_action_id}"
