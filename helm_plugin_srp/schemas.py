from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

from helm_plugin_srp.models import SrpStatus


# ── 配置 ──────────────────────────────────────────────────────────────────────

class SrpConfigResponse(BaseModel):
    # ── 共用配置 ──────────────────────────────────────────────────────────────
    price_region_id: int
    price_order_type: str        # "buy" | "sell"
    # ── 常规补损 ──────────────────────────────────────────────────────────────
    coefficient: float
    enabled: bool
    min_loss_value: float
    eligible_ship_groups: list[int]
    full_loss: bool
    # ── PAP 舰队补损 ──────────────────────────────────────────────────────────
    pap_coefficient: float
    pap_enabled: bool
    pap_min_loss_value: float
    pap_full_loss: bool


class SrpConfigUpdateRequest(BaseModel):
    # ── 共用配置 ──────────────────────────────────────────────────────────────
    price_region_id: int | None = None
    price_order_type: str | None = None
    # ── 常规补损 ──────────────────────────────────────────────────────────────
    coefficient: float | None = None
    enabled: bool | None = None
    min_loss_value: float | None = None
    eligible_ship_groups: list[int] | None = None
    full_loss: bool | None = None
    # ── PAP 舰队补损 ──────────────────────────────────────────────────────────
    pap_coefficient: float | None = None
    pap_enabled: bool | None = None
    pap_min_loss_value: float | None = None
    pap_full_loss: bool | None = None

    @field_validator("price_order_type")
    @classmethod
    def validate_order_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("buy", "sell"):
            raise ValueError("price_order_type 必须为 'buy' 或 'sell'")
        return v

    @field_validator("coefficient", "pap_coefficient")
    @classmethod
    def validate_coefficient(cls, v: float | None) -> float | None:
        if v is not None and not (0.0 <= v <= 2.0):
            raise ValueError("coefficient 必须在 0.0 ~ 2.0 之间")
        return v


# ── 预览 ──────────────────────────────────────────────────────────────────────

class KillmailItemDetail(BaseModel):
    type_id: int
    name: str
    icon_url: str | None
    qty_destroyed: int
    qty_dropped: int


class KillmailPreviewResponse(BaseModel):
    killmail_id: int
    ship_type_id: int
    ship_name: str
    ship_icon_url: str | None = None
    items: list[KillmailItemDetail] = []
    loss_value_raw: float
    calculated_value: float
    price_source: str       # 例如 "Jita Buy"
    coefficient: float
    eligible: bool
    ineligible_reason: str | None = None


# ── 申请 ──────────────────────────────────────────────────────────────────────

class SubmitSrpRequest(BaseModel):
    zkb_url: str
    character_id: int
    fleet_action_id: int | None = None
    notes: str | None = None


class SrpRequestResponse(BaseModel):
    id: int
    user_id: int
    character_id: int
    character_name: str
    killmail_id: int
    zkb_url: str
    ship_type_id: int
    ship_name: str
    loss_value_raw: float
    calculated_value: float
    status: SrpStatus
    fleet_action_id: int | None
    notes: str | None
    officer_notes: str | None
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SrpRequestListResponse(BaseModel):
    items: list[SrpRequestResponse]
    total: int


# ── 审核 ──────────────────────────────────────────────────────────────────────

class ReviewSrpRequest(BaseModel):
    officer_notes: str | None = None


# ── 舰队 KM ───────────────────────────────────────────────────────────────────

class FleetKillItem(BaseModel):
    killmail_id: int
    zkb_url: str
    ship_type_id: int
    ship_name: str
    killed_at: datetime
    loss_value_raw: float
    calculated_value: float
    already_submitted: bool


class FleetKillsResponse(BaseModel):
    fleet_action_id: int
    fleet_action_name: str
    window_start: datetime
    window_end: datetime
    items: list[FleetKillItem]


# ── 申请详情（含物品） ────────────────────────────────────────────────────────

class SrpRequestDetail(SrpRequestResponse):
    killmail_hash: str
    ship_icon_url: str | None = None
    items: list[KillmailItemDetail] = []


# ── PAP 舰队列表 ──────────────────────────────────────────────────────────────

class MyPapFleetItem(BaseModel):
    fleet_action_id: int
    fleet_action_name: str
    status: str               # "active" | "ended"
    window_start: datetime
    window_end: datetime | None
    pap_issued_at: datetime
