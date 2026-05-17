"""市场价格查询（复用 Helm 核心服务）与补损金额计算。"""

from __future__ import annotations

import json
from typing import Any

# 星域 ID → 可读名称映射（常用星域）
_REGION_NAMES: dict[int, str] = {
    10000002: "Jita（The Forge）",
    10000043: "Amarr（Domain）",
    10000032: "Dodixie（Sinq Laison）",
    10000042: "Hek（Metropolis）",
    10000030: "Rens（Heimatar）",
}


async def get_best_price(
    type_id: int,
    region_id: int,
    order_type: str,  # "buy" | "sell"
) -> float:
    """
    通过 Helm 核心市场服务查询最优价格（带 Redis 缓存，TTL 1h）。
    - order_type="buy"  → MarketPrice.best_buy（最高买单价）
    - order_type="sell" → MarketPrice.best_sell（最低卖单价）
    """
    from app.services.market import get_market_prices

    prices = await get_market_prices([type_id], region_id=region_id)
    mp = prices.get(type_id)
    if mp is None:
        return 0.0
    return float(mp.best_buy or 0.0) if order_type == "buy" else float(mp.best_sell or 0.0)


async def get_items_value(
    items: list[dict],
    region_id: int,
    order_type: str,
) -> float:
    """
    批量查询物品市场价，返回全部物品的总价值。
    items 格式：[{type_id, qty_destroyed, qty_dropped}, ...]
    计价依据：qty_destroyed（装备损毁数量），不计 qty_dropped（掉落的可回收）。
    """
    if not items:
        return 0.0

    from app.services.market import get_market_prices

    type_ids = list({i["type_id"] for i in items})
    prices = await get_market_prices(type_ids, region_id=region_id)

    total = 0.0
    for item in items:
        mp = prices.get(item["type_id"])
        if mp is None:
            continue
        unit_price = float(mp.best_buy or 0.0) if order_type == "buy" else float(mp.best_sell or 0.0)
        total += unit_price * item["qty_destroyed"]
    return total


def calculate_srp_value(raw_value: float, coefficient: float) -> float:
    """根据系数计算实际补损金额，四舍五入到 ISK 整数。"""
    return round(raw_value * coefficient, 2)


def price_source_label(region_id: int, order_type: str) -> str:
    """返回价格来源的可读说明，例如 'Jita（The Forge）Buy'。"""
    region_name = _REGION_NAMES.get(region_id, f"Region {region_id}")
    return f"{region_name} {'Buy' if order_type == 'buy' else 'Sell'}"


async def load_config(db) -> dict[str, Any]:
    """
    从数据库读取 srp_configs，返回解析后的配置字典。
    调用方传入 AsyncSession。
    """
    from sqlalchemy import select
    from helm_plugin_srp.models import SrpConfig, DEFAULT_CONFIG

    result = await db.execute(select(SrpConfig))
    rows = result.scalars().all()
    cfg: dict[str, str] = {row.key: row.value for row in rows}

    return {
        "price_region_id":     int(cfg.get("price_region_id",  DEFAULT_CONFIG["price_region_id"])),
        "price_order_type":    cfg.get("price_order_type",      DEFAULT_CONFIG["price_order_type"]),
        "coefficient":         float(cfg.get("coefficient",     DEFAULT_CONFIG["coefficient"])),
        "enabled":             cfg.get("enabled",               DEFAULT_CONFIG["enabled"]) == "true",
        "min_loss_value":      float(cfg.get("min_loss_value",  DEFAULT_CONFIG["min_loss_value"])),
        "eligible_ship_groups": json.loads(cfg.get("eligible_ship_groups", DEFAULT_CONFIG["eligible_ship_groups"])),
        "full_loss":           cfg.get("full_loss",             DEFAULT_CONFIG["full_loss"]) == "true",
    }


def check_eligibility(
    loss_value_raw: float,
    ship_type_id: int,
    config: dict[str, Any],
) -> tuple[bool, str | None]:
    """
    检查该损失是否符合补损资格。
    返回 (eligible: bool, reason: str | None)
    """
    if not config["enabled"]:
        return False, "SRP 系统当前已关闭"
    if loss_value_raw < config["min_loss_value"]:
        min_isk = f"{config['min_loss_value']:,.0f}"
        return False, f"损失价值不足最低要求 {min_isk} ISK"
    groups: list[int] = config["eligible_ship_groups"]
    # eligible_ship_groups 为空 = 全部舰船可补损，不为空则需要匹配
    # 注：ship_type_id 与 ship_group_id 不同；完整实现需 ESI /universe/types/{id}/ 查 group_id
    # 此处留为扩展点，MVP 阶段 eligible_ship_groups 为空时直接通过
    if groups:
        # TODO: 需要查 ESI 确认 ship_type_id 的 group_id 是否在 groups 中
        pass
    return True, None
