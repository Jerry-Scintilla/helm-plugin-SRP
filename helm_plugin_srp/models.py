from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SrpStatus(str, PyEnum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"
    paid     = "paid"


class SrpRequest(Base):
    """一条舰船补损申请记录。"""

    __tablename__ = "srp_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 申请人（跨 Base 引用 users.id，FK 约束由 migration 维护，ORM 层不声明）
    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    character_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    character_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # 击杀信息
    killmail_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    killmail_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    zkb_url: Mapped[str] = mapped_column(Text, nullable=False)
    ship_type_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ship_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    # 补损金额
    loss_value_raw: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False, default=0)
    calculated_value: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False, default=0)

    # 状态
    status: Mapped[SrpStatus] = mapped_column(
        Enum(SrpStatus, name="srp_status"),
        nullable=False,
        default=SrpStatus.pending,
        index=True,
    )

    # 关联舰队行动（可选）
    fleet_action_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # 损毁物品列表（JSON，格式：[{type_id, qty_destroyed, qty_dropped}, ...]）
    items_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # 备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    officer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 审核信息
    reviewed_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )


class SrpConfig(Base):
    """补损配置键值对。"""

    __tablename__ = "srp_configs"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


# 默认配置值（首次启用时写入）
DEFAULT_CONFIG: dict[str, str] = {
    "price_region_id":    "10000002",  # The Forge (Jita)
    "price_order_type":   "buy",       # "buy" | "sell"
    "coefficient":        "1.0",       # 价值乘数
    "enabled":            "true",      # 系统开关
    "min_loss_value":     "0",         # 最低损失 ISK
    "eligible_ship_groups": "[]",      # 允许补损的舰船组 ID，空=全部
    "full_loss":          "false",     # 是否计算全损（船体+装备）
}
