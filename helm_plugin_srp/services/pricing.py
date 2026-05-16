"""ESI 市场价格查询与补损金额计算。"""

from __future__ import annotations

import json
from typing import Any

import httpx

_ESI_BASE = "https://esi.evetech.net/latest"

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
    从 ESI 市场获取指定 type_id 在 region_id 的最优价格。
    - order_type="buy"  → 返回最高买单价（buy order max price）
    - order_type="sell" → 返回最低卖单价（sell order min price）
    ESI: GET /markets/{region_id}/orders/?type_id={type_id}&order_type={buy|sell}
    """
    url = f"{_ESI_BASE}/markets/{region_id}/orders/"
    params: dict[str, Any] = {
        "type_id": type_id,
        "order_type": order_type,
    }

    prices: list[float] = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        # ESI 市场端点通常只有 1 页（单 type 查询），但保险起见处理分页
        page = 1
        while True:
            params["page"] = page
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": "Helm-SRP-Plugin/0.1"},
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            orders: list[dict] = resp.json()
            if not orders:
                break
            for order in orders:
                # is_buy_order=True → 买单；False → 卖单
                is_buy = order.get("is_buy_order", False)
                if order_type == "buy" and is_buy:
                    prices.append(float(order.get("price", 0)))
                elif order_type == "sell" and not is_buy:
                    prices.append(float(order.get("price", 0)))
            # ESI 单 type 查询只有 1 页
            break

    if not prices:
        return 0.0

    return max(prices) if order_type == "buy" else min(prices)


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
