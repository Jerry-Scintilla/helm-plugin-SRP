"""SRP MCP Tool Provider — 将补损功能暴露给 MCP 客户端（AI 代理）。"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from helm_mcp.protocols import MCPToolDef, MCPToolProvider

from helm_plugin_srp.models import SrpRequest, SrpStatus
from helm_plugin_srp.schemas import SrpConfigResponse, SrpRequestResponse
from helm_plugin_srp.services import killmail as km_svc
from helm_plugin_srp.services import pricing as price_svc


def _has_permission(user, perm: str) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    perms: list = getattr(user, "permissions", []) or []
    return perm in perms


class SrpMCPToolProvider:
    """实现 MCPToolProvider 协议，将 SRP 补损功能注册为 MCP 工具。"""

    # ── 工具声明 ──────────────────────────────────────────────────────────────

    def get_mcp_tools(self) -> list[MCPToolDef]:
        return [
            MCPToolDef(
                name="srp_get_config",
                description=(
                    "查看舰船补损（SRP）系统当前配置，"
                    "包括价格星域、价格类型（buy/sell）、补损系数、启用开关、最低损失 ISK 和可补损舰船组。"
                ),
                input_schema={"type": "object", "properties": {}, "required": []},
                required_permission="srp.admin",
            ),
            MCPToolDef(
                name="srp_preview_killmail",
                description=(
                    "预览 zkillboard 链接对应的补损金额和资格，提交申请前用于确认。"
                    "返回舰船名称、原始损失价值、计算后补损金额、是否符合资格。"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "zkb_url": {
                            "type": "string",
                            "description": "zkillboard 击杀链接，如 https://zkillboard.com/kill/12345/",
                        },
                    },
                    "required": ["zkb_url"],
                },
                required_permission="srp.submit",
            ),
            MCPToolDef(
                name="srp_submit_request",
                description="提交一条舰船补损申请。角色必须属于当前用户，击杀受害者必须是该角色。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "zkb_url": {
                            "type": "string",
                            "description": "zkillboard 击杀链接",
                        },
                        "character_id": {
                            "type": "integer",
                            "description": "受损角色的 EVE 角色 ID",
                        },
                        "fleet_action_id": {
                            "type": "integer",
                            "description": "关联的舰队行动 ID（可选）",
                        },
                        "notes": {
                            "type": "string",
                            "description": "申请备注（可选）",
                        },
                    },
                    "required": ["zkb_url", "character_id"],
                },
                required_permission="srp.submit",
            ),
            MCPToolDef(
                name="srp_list_requests",
                description=(
                    "列出舰船补损申请，支持按状态和角色过滤。"
                    "补损官（srp.officer）可查看所有人的申请，普通用户只能查看自己的。"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pending", "approved", "rejected", "paid"],
                            "description": "按状态过滤（可选）",
                        },
                        "character_id": {
                            "type": "integer",
                            "description": "按角色 ID 过滤（可选）",
                        },
                        "page": {
                            "type": "integer",
                            "default": 1,
                            "description": "页码，从 1 开始",
                        },
                        "page_size": {
                            "type": "integer",
                            "default": 20,
                            "description": "每页条数（1-100）",
                        },
                    },
                    "required": [],
                },
            ),
            MCPToolDef(
                name="srp_get_request",
                description="查看单条补损申请的详细信息。普通用户只能查看自己的申请，补损官可查看任意申请。",
                input_schema={
                    "type": "object",
                    "properties": {
                        "request_id": {
                            "type": "integer",
                            "description": "补损申请 ID",
                        },
                    },
                    "required": ["request_id"],
                },
            ),
            MCPToolDef(
                name="srp_review_request",
                description=(
                    "审核补损申请：批准（approve）、拒绝（reject）或标记为已付款（mark_paid）。"
                    "approve/reject 只能对 pending 状态的申请操作；mark_paid 只能对 approved 状态操作。"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "request_id": {
                            "type": "integer",
                            "description": "补损申请 ID",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["approve", "reject", "mark_paid"],
                            "description": "审核操作",
                        },
                        "officer_notes": {
                            "type": "string",
                            "description": "补损官备注（可选，approve/reject 时生效）",
                        },
                    },
                    "required": ["request_id", "action"],
                },
                required_permission="srp.officer",
            ),
        ]

    # ── 工具分发 ──────────────────────────────────────────────────────────────

    async def call_mcp_tool(
        self,
        name: str,
        args: dict,
        user,
        db: AsyncSession,
    ) -> dict:
        dispatch = {
            "srp_get_config":       self._get_config,
            "srp_preview_killmail": self._preview_killmail,
            "srp_submit_request":   self._submit_request,
            "srp_list_requests":    self._list_requests,
            "srp_get_request":      self._get_request,
            "srp_review_request":   self._review_request,
        }
        if name not in dispatch:
            raise ValueError(f"Unknown tool: {name}")
        return await dispatch[name](args, user, db)

    # ── 工具实现 ──────────────────────────────────────────────────────────────

    async def _get_config(self, args: dict, user, db: AsyncSession) -> dict:
        cfg = await price_svc.load_config(db)
        return SrpConfigResponse(**cfg).model_dump()

    async def _preview_killmail(self, args: dict, user, db: AsyncSession) -> dict:
        try:
            km = await km_svc.get_killmail_info(args["zkb_url"])
        except ValueError as e:
            return {"error": str(e)}
        except httpx.HTTPStatusError as e:
            return {"error": f"外部 API 错误：{e.response.status_code}"}

        cfg = await price_svc.load_config(db)
        eligible, reason = price_svc.check_eligibility(km["loss_value_raw"], km["ship_type_id"], cfg)

        market_price = 0.0
        try:
            market_price = await price_svc.get_best_price(
                km["ship_type_id"], cfg["price_region_id"], cfg["price_order_type"]
            )
        except Exception:
            pass

        base_value = market_price if market_price > 0 else km["loss_value_raw"]
        calculated = price_svc.calculate_srp_value(base_value, cfg["coefficient"])

        return {
            "killmail_id":      km["killmail_id"],
            "ship_type_id":     km["ship_type_id"],
            "ship_name":        km["ship_name"],
            "loss_value_raw":   km["loss_value_raw"],
            "calculated_value": calculated,
            "price_source":     price_svc.price_source_label(cfg["price_region_id"], cfg["price_order_type"]),
            "coefficient":      cfg["coefficient"],
            "eligible":         eligible,
            "ineligible_reason": reason,
        }

    async def _submit_request(self, args: dict, user, db: AsyncSession) -> dict:
        from app.models.character import Character

        zkb_url = args["zkb_url"]
        character_id = args["character_id"]
        fleet_action_id = args.get("fleet_action_id")
        notes = args.get("notes")

        char_result = await db.execute(
            select(Character).where(
                Character.character_id == character_id,
                Character.user_id == user.id,
            )
        )
        char = char_result.scalar_one_or_none()
        if char is None:
            return {"error": "该角色不属于您的账号"}

        try:
            killmail_id, _ = km_svc.parse_esi_url(zkb_url)
        except ValueError as e:
            return {"error": str(e)}

        existing = await db.execute(
            select(SrpRequest).where(SrpRequest.killmail_id == killmail_id)
        )
        if existing.scalar_one_or_none():
            return {"error": "该击杀已存在补损申请，不可重复提交"}

        try:
            km = await km_svc.get_killmail_info(zkb_url)
        except ValueError as e:
            return {"error": str(e)}
        except httpx.HTTPStatusError as e:
            return {"error": f"外部 API 错误：{e.response.status_code}"}

        if km["victim_character_id"] and km["victim_character_id"] != character_id:
            return {"error": "该击杀的受害者不是您指定的角色，请确认 zkillboard 链接是否正确"}

        cfg = await price_svc.load_config(db)
        eligible, reason = price_svc.check_eligibility(km["loss_value_raw"], km["ship_type_id"], cfg)
        if not eligible:
            return {"error": f"不符合补损资格：{reason}"}

        market_price = 0.0
        try:
            market_price = await price_svc.get_best_price(
                km["ship_type_id"], cfg["price_region_id"], cfg["price_order_type"]
            )
        except Exception:
            pass

        base_value = market_price if market_price > 0 else km["loss_value_raw"]
        calculated = price_svc.calculate_srp_value(base_value, cfg["coefficient"])

        srp = SrpRequest(
            user_id=user.id,
            character_id=character_id,
            character_name=char.character_name,
            killmail_id=km["killmail_id"],
            killmail_hash=km["killmail_hash"],
            zkb_url=zkb_url,
            ship_type_id=km["ship_type_id"],
            ship_name=km["ship_name"],
            loss_value_raw=km["loss_value_raw"],
            calculated_value=calculated,
            status=SrpStatus.pending,
            fleet_action_id=fleet_action_id,
            notes=notes,
            created_at=datetime.now(UTC),
        )
        db.add(srp)
        await db.commit()
        await db.refresh(srp)
        return SrpRequestResponse.model_validate(srp).model_dump(mode="json")

    async def _list_requests(self, args: dict, user, db: AsyncSession) -> dict:
        status = args.get("status")
        character_id = args.get("character_id")
        page = max(1, int(args.get("page", 1)))
        page_size = min(100, max(1, int(args.get("page_size", 20))))

        is_officer = _has_permission(user, "srp.officer")
        stmt = select(SrpRequest).order_by(SrpRequest.created_at.desc())

        if not is_officer:
            stmt = stmt.where(SrpRequest.user_id == user.id)

        if status:
            try:
                stmt = stmt.where(SrpRequest.status == SrpStatus(status))
            except ValueError:
                return {"error": f"无效的状态值：{status}"}

        if character_id:
            stmt = stmt.where(SrpRequest.character_id == character_id)

        total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
        total = total_result.scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        items = result.scalars().all()

        return {
            "items": [SrpRequestResponse.model_validate(r).model_dump(mode="json") for r in items],
            "total": total,
        }

    async def _get_request(self, args: dict, user, db: AsyncSession) -> dict:
        request_id = args["request_id"]
        result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
        srp = result.scalar_one_or_none()
        if srp is None:
            return {"error": "申请不存在"}

        if not _has_permission(user, "srp.officer") and srp.user_id != user.id:
            return {"error": "无权查看该申请"}

        return SrpRequestResponse.model_validate(srp).model_dump(mode="json")

    async def _review_request(self, args: dict, user, db: AsyncSession) -> dict:
        request_id = args["request_id"]
        action = args["action"]
        officer_notes = args.get("officer_notes")

        result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
        srp = result.scalar_one_or_none()
        if srp is None:
            return {"error": "申请不存在"}

        now = datetime.now(UTC)

        if action == "approve":
            if srp.status != SrpStatus.pending:
                return {"error": f"申请当前状态为 {srp.status}，无法批准"}
            srp.status = SrpStatus.approved
            srp.reviewed_by_user_id = user.id
            srp.reviewed_at = now
            srp.officer_notes = officer_notes

        elif action == "reject":
            if srp.status != SrpStatus.pending:
                return {"error": f"申请当前状态为 {srp.status}，无法拒绝"}
            srp.status = SrpStatus.rejected
            srp.reviewed_by_user_id = user.id
            srp.reviewed_at = now
            srp.officer_notes = officer_notes

        elif action == "mark_paid":
            if srp.status != SrpStatus.approved:
                return {"error": "只有已批准的申请才能标记为已付款"}
            srp.status = SrpStatus.paid
            srp.reviewed_by_user_id = user.id
            srp.reviewed_at = now

        else:
            return {"error": f"无效的操作：{action}，有效值为 approve / reject / mark_paid"}

        await db.commit()
        await db.refresh(srp)
        return SrpRequestResponse.model_validate(srp).model_dump(mode="json")
