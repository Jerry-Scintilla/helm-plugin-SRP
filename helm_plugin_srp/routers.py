from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import get_current_user, require_permission
from app.models.character import Character
from app.models.user import User

from helm_plugin_srp.models import DEFAULT_CONFIG, SrpConfig, SrpRequest, SrpStatus
from helm_plugin_srp.schemas import (
    FleetKillItem,
    FleetKillsResponse,
    KillmailPreviewResponse,
    ReviewSrpRequest,
    SrpConfigResponse,
    SrpConfigUpdateRequest,
    SrpRequestListResponse,
    SrpRequestResponse,
    SubmitSrpRequest,
)
from helm_plugin_srp.services import killmail as km_svc
from helm_plugin_srp.services import pricing as price_svc

router = APIRouter()


# ── 内部工具 ──────────────────────────────────────────────────────────────────

async def _load_config(db: AsyncSession) -> dict:
    return await price_svc.load_config(db)


async def _get_config_row(db: AsyncSession, key: str) -> SrpConfig | None:
    result = await db.execute(select(SrpConfig).where(SrpConfig.key == key))
    return result.scalar_one_or_none()


async def _upsert_config(db: AsyncSession, key: str, value: str) -> None:
    row = await _get_config_row(db, key)
    if row:
        row.value = value
        row.updated_at = datetime.now(UTC)
    else:
        db.add(SrpConfig(key=key, value=value, updated_at=datetime.now(UTC)))


def _has_permission(user: User, perm: str) -> bool:
    """检查 user 是否拥有指定权限（is_superuser 全部放行）。"""
    if getattr(user, "is_superuser", False):
        return True
    perms: list = getattr(user, "permissions", []) or []
    return perm in perms


async def _verify_character_ownership(
    character_id: int,
    current_user: User,
    db: AsyncSession,
) -> Character:
    result = await db.execute(
        select(Character).where(
            Character.character_id == character_id,
            Character.user_id == current_user.id,
        )
    )
    char = result.scalar_one_or_none()
    if char is None:
        raise HTTPException(status_code=403, detail="该角色不属于您的账号")
    return char


# ── GET /config ───────────────────────────────────────────────────────────────

@router.get("/config", response_model=SrpConfigResponse, summary="查看补损配置")
async def get_config(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("srp.admin")),
):
    cfg = await _load_config(db)
    return SrpConfigResponse(**cfg)


# ── PUT /config ───────────────────────────────────────────────────────────────

@router.put("/config", response_model=SrpConfigResponse, summary="更新补损配置")
async def update_config(
    body: SrpConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("srp.admin")),
):
    updates: dict[str, str] = {}
    if body.price_region_id is not None:
        updates["price_region_id"] = str(body.price_region_id)
    if body.price_order_type is not None:
        updates["price_order_type"] = body.price_order_type
    if body.coefficient is not None:
        updates["coefficient"] = str(body.coefficient)
    if body.enabled is not None:
        updates["enabled"] = "true" if body.enabled else "false"
    if body.min_loss_value is not None:
        updates["min_loss_value"] = str(body.min_loss_value)
    if body.eligible_ship_groups is not None:
        updates["eligible_ship_groups"] = json.dumps(body.eligible_ship_groups)

    for key, val in updates.items():
        await _upsert_config(db, key, val)
    await db.commit()

    cfg = await _load_config(db)
    return SrpConfigResponse(**cfg)


# ── GET /killmail/preview ─────────────────────────────────────────────────────

@router.get(
    "/killmail/preview",
    response_model=KillmailPreviewResponse,
    summary="预览补损金额（提交前检查）",
)
async def preview_killmail(
    url: str = Query(..., description="zkillboard 链接，如 https://zkillboard.com/kill/12345/"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("srp.submit")),
):
    try:
        km = await km_svc.get_killmail_info(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"外部 API 错误：{e.response.status_code}")

    cfg = await _load_config(db)
    eligible, reason = price_svc.check_eligibility(km["loss_value_raw"], km["ship_type_id"], cfg)

    # 尝试从市场获取实时价格（作为参考；实际补损用 zkb 原始价）
    market_price = 0.0
    try:
        market_price = await price_svc.get_best_price(
            km["ship_type_id"],
            cfg["price_region_id"],
            cfg["price_order_type"],
        )
    except Exception:
        pass

    # 若市场价格存在则用市场价，否则回退到 zkb 原始价
    base_value = market_price if market_price > 0 else km["loss_value_raw"]
    calculated = price_svc.calculate_srp_value(base_value, cfg["coefficient"])

    return KillmailPreviewResponse(
        killmail_id=km["killmail_id"],
        ship_type_id=km["ship_type_id"],
        ship_name=km["ship_name"],
        loss_value_raw=km["loss_value_raw"],
        calculated_value=calculated,
        price_source=price_svc.price_source_label(cfg["price_region_id"], cfg["price_order_type"]),
        coefficient=cfg["coefficient"],
        eligible=eligible,
        ineligible_reason=reason,
    )


# ── POST /requests ────────────────────────────────────────────────────────────

@router.post("/requests", response_model=SrpRequestResponse, status_code=201, summary="提交补损申请")
async def submit_request(
    body: SubmitSrpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("srp.submit")),
):
    char = await _verify_character_ownership(body.character_id, current_user, db)

    # 检查是否重复提交
    existing = await db.execute(
        select(SrpRequest).where(SrpRequest.killmail_id == km_svc.parse_zkb_url(body.zkb_url))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该击杀已存在补损申请，不可重复提交")

    try:
        km = await km_svc.get_killmail_info(body.zkb_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"外部 API 错误：{e.response.status_code}")

    # 确认受害者是申请角色
    if km["victim_character_id"] and km["victim_character_id"] != body.character_id:
        raise HTTPException(
            status_code=400,
            detail="该击杀的受害者不是您指定的角色，请确认 zkillboard 链接是否正确",
        )

    cfg = await _load_config(db)
    eligible, reason = price_svc.check_eligibility(km["loss_value_raw"], km["ship_type_id"], cfg)
    if not eligible:
        raise HTTPException(status_code=400, detail=f"不符合补损资格：{reason}")

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
        user_id=current_user.id,
        character_id=body.character_id,
        character_name=char.character_name,
        killmail_id=km["killmail_id"],
        killmail_hash=km["killmail_hash"],
        zkb_url=body.zkb_url,
        ship_type_id=km["ship_type_id"],
        ship_name=km["ship_name"],
        loss_value_raw=km["loss_value_raw"],
        calculated_value=calculated,
        status=SrpStatus.pending,
        fleet_action_id=body.fleet_action_id,
        notes=body.notes,
        created_at=datetime.now(UTC),
    )
    db.add(srp)
    await db.commit()
    await db.refresh(srp)
    return SrpRequestResponse.model_validate(srp)


# ── GET /requests ─────────────────────────────────────────────────────────────

@router.get("/requests", response_model=SrpRequestListResponse, summary="查询补损申请列表")
async def list_requests(
    status: str | None = Query(None, description="按状态过滤：pending/approved/rejected/paid"),
    character_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_officer = _has_permission(current_user, "srp.officer")
    stmt = select(SrpRequest).order_by(SrpRequest.created_at.desc())

    if not is_officer:
        # 普通用户只能看自己的
        stmt = stmt.where(SrpRequest.user_id == current_user.id)

    if status:
        try:
            stmt = stmt.where(SrpRequest.status == SrpStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的状态值：{status}")

    if character_id:
        stmt = stmt.where(SrpRequest.character_id == character_id)

    total_result = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_result.scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return SrpRequestListResponse(
        items=[SrpRequestResponse.model_validate(r) for r in items],
        total=total,
    )


# ── GET /requests/{id} ────────────────────────────────────────────────────────

@router.get("/requests/{request_id}", response_model=SrpRequestResponse, summary="查看申请详情")
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
    srp = result.scalar_one_or_none()
    if srp is None:
        raise HTTPException(status_code=404, detail="申请不存在")

    is_officer = _has_permission(current_user, "srp.officer")
    if not is_officer and srp.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该申请")

    return SrpRequestResponse.model_validate(srp)


# ── POST /requests/{id}/approve ───────────────────────────────────────────────

@router.post("/requests/{request_id}/approve", response_model=SrpRequestResponse, summary="批准补损申请")
async def approve_request(
    request_id: int,
    body: ReviewSrpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("srp.officer")),
):
    result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
    srp = result.scalar_one_or_none()
    if srp is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if srp.status != SrpStatus.pending:
        raise HTTPException(status_code=400, detail=f"申请当前状态为 {srp.status}，无法批准")

    srp.status = SrpStatus.approved
    srp.reviewed_by_user_id = current_user.id
    srp.reviewed_at = datetime.now(UTC)
    srp.officer_notes = body.officer_notes
    await db.commit()
    await db.refresh(srp)
    return SrpRequestResponse.model_validate(srp)


# ── POST /requests/{id}/reject ────────────────────────────────────────────────

@router.post("/requests/{request_id}/reject", response_model=SrpRequestResponse, summary="拒绝补损申请")
async def reject_request(
    request_id: int,
    body: ReviewSrpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("srp.officer")),
):
    result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
    srp = result.scalar_one_or_none()
    if srp is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if srp.status != SrpStatus.pending:
        raise HTTPException(status_code=400, detail=f"申请当前状态为 {srp.status}，无法拒绝")

    srp.status = SrpStatus.rejected
    srp.reviewed_by_user_id = current_user.id
    srp.reviewed_at = datetime.now(UTC)
    srp.officer_notes = body.officer_notes
    await db.commit()
    await db.refresh(srp)
    return SrpRequestResponse.model_validate(srp)


# ── POST /requests/{id}/mark_paid ─────────────────────────────────────────────

@router.post("/requests/{request_id}/mark_paid", response_model=SrpRequestResponse, summary="标记为已付款")
async def mark_paid(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("srp.officer")),
):
    result = await db.execute(select(SrpRequest).where(SrpRequest.id == request_id))
    srp = result.scalar_one_or_none()
    if srp is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if srp.status != SrpStatus.approved:
        raise HTTPException(status_code=400, detail="只有已批准的申请才能标记为已付款")

    srp.status = SrpStatus.paid
    srp.reviewed_by_user_id = current_user.id
    srp.reviewed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(srp)
    return SrpRequestResponse.model_validate(srp)


# ── GET /fleet/{fleet_action_id}/kills ────────────────────────────────────────

@router.get(
    "/fleet/{fleet_action_id}/kills",
    response_model=FleetKillsResponse,
    summary="查询玩家在舰队行动期间的损失（快捷补损）",
)
async def get_fleet_kills(
    fleet_action_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("srp.submit")),
):
    """
    通过 fleet-action 插件的内部 REST API 获取行动时间窗口，
    再从 zkillboard 拉取当前用户角色在该窗口内的损失记录。
    """
    # 1. 查询 fleet-action 行动信息
    action_info = await _fetch_fleet_action(fleet_action_id, current_user)
    window_start: datetime = action_info["created_at"]
    window_end: datetime = action_info.get("ended_at") or datetime.now(UTC)
    action_name: str = action_info.get("name", f"行动#{fleet_action_id}")

    # 2. 获取当前用户的角色
    chars_result = await db.execute(
        select(Character).where(Character.user_id == current_user.id)
    )
    characters = chars_result.scalars().all()
    if not characters:
        return FleetKillsResponse(
            fleet_action_id=fleet_action_id,
            fleet_action_name=action_name,
            window_start=window_start,
            window_end=window_end,
            items=[],
        )

    # 3. 查询已提交的 killmail_id（避免重复）
    submitted_result = await db.execute(
        select(SrpRequest.killmail_id).where(
            SrpRequest.fleet_action_id == fleet_action_id
        )
    )
    submitted_ids: set[int] = {row[0] for row in submitted_result.all()}

    # 4. 从 zkb 拉取各角色的损失
    cfg = await _load_config(db)
    all_kills: list[FleetKillItem] = []

    for char in characters:
        try:
            losses = await km_svc.fetch_character_losses(
                char.character_id, window_start, window_end
            )
        except Exception:
            continue

        for loss in losses:
            market_price = 0.0
            try:
                market_price = await price_svc.get_best_price(
                    loss["ship_type_id"],
                    cfg["price_region_id"],
                    cfg["price_order_type"],
                )
            except Exception:
                pass

            base_value = market_price if market_price > 0 else loss["loss_value_raw"]
            calculated = price_svc.calculate_srp_value(base_value, cfg["coefficient"])

            # 补全 ship_name
            if not loss["ship_name"] and loss["ship_type_id"]:
                try:
                    loss["ship_name"] = await km_svc.resolve_type_name(loss["ship_type_id"])
                except Exception:
                    pass

            all_kills.append(
                FleetKillItem(
                    killmail_id=loss["killmail_id"],
                    zkb_url=loss["zkb_url"],
                    ship_type_id=loss["ship_type_id"],
                    ship_name=loss["ship_name"],
                    killed_at=loss["killed_at"],
                    loss_value_raw=loss["loss_value_raw"],
                    calculated_value=calculated,
                    already_submitted=loss["killmail_id"] in submitted_ids,
                )
            )

    all_kills.sort(key=lambda k: k.killed_at, reverse=True)
    return FleetKillsResponse(
        fleet_action_id=fleet_action_id,
        fleet_action_name=action_name,
        window_start=window_start,
        window_end=window_end,
        items=all_kills,
    )


async def _fetch_fleet_action(fleet_action_id: int, current_user: User) -> dict:
    """
    调用 fleet-action 插件的内部 API 获取行动详情。
    使用 Helm 内部 HTTP 请求（localhost），携带用户 JWT 进行权限验证。
    """
    # fleet-action 的 GET /actions/{id} 需要 fleet-action.read 权限
    # 这里使用内部 HTTP 请求（或直接查询 fleet_action 模型）
    try:
        from fleet_action.models import FleetAction
        from sqlalchemy import select as sa_select
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                sa_select(FleetAction).where(FleetAction.id == fleet_action_id)
            )
            action = result.scalar_one_or_none()

        if action is None:
            raise HTTPException(status_code=404, detail=f"舰队行动 #{fleet_action_id} 不存在")

        return {
            "id": action.id,
            "name": action.name,
            "created_at": action.created_at,
            "ended_at": action.ended_at,
            "status": action.status,
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="fleet-action 插件未安装，无法使用舰队快速补损功能",
        )
