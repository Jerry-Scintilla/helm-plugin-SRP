"""ESI killmail URL 解析 + killmail 数据拉取工具。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

# ESI killmail URL 格式：
#   https://esi.evetech.net/killmails/{id}/{hash}
#   https://esi.evetech.net/latest/killmails/{id}/{hash}/
_ESI_URL_RE = re.compile(
    r"esi\.evetech\.net/(?:latest/)?killmails?/(\d+)/([0-9a-f]{40,})",
    re.IGNORECASE,
)
_ESI_BASE = "https://esi.evetech.net/latest"


def parse_esi_url(url: str) -> tuple[int, str]:
    """
    解析 ESI killmail URL，返回 (killmail_id, killmail_hash)。
    格式不匹配时抛出 ValueError。
    """
    m = _ESI_URL_RE.search(url)
    if not m:
        raise ValueError(
            "无效的 ESI killmail URL，"
            "格式应为 https://esi.evetech.net/killmails/{id}/{hash}"
        )
    return int(m.group(1)), m.group(2)


async def fetch_esi_killmail(killmail_id: int, killmail_hash: str) -> dict[str, Any]:
    """
    通过 ESI 获取完整击杀详情（公开端点，无需 token）。
    ESI: GET /killmails/{killmail_id}/{killmail_hash}/
    """
    url = f"{_ESI_BASE}/killmails/{killmail_id}/{killmail_hash}/"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"User-Agent": "Helm-SRP-Plugin/0.1"})
    resp.raise_for_status()
    return resp.json()


async def resolve_type_name(type_id: int) -> str:
    """通过 ESI universe/types 获取 type_id 对应的名称。"""
    url = f"{_ESI_BASE}/universe/types/{type_id}/"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "Helm-SRP-Plugin/0.1"})
        resp.raise_for_status()
        return resp.json().get("name", f"TypeID:{type_id}")
    except Exception:
        return f"TypeID:{type_id}"


async def get_killmail_info(esi_url: str) -> dict[str, Any]:
    """
    主入口：解析 ESI killmail URL，通过 ESI 拉取数据，返回规范化结果：
    {
        killmail_id, killmail_hash, zkb_url,
        ship_type_id, ship_name,
        victim_character_id,
        killed_at,
        loss_value_raw,   ← 始终为 0（由调用方通过市场模块计算实际价值）
    }

    接受格式：https://esi.evetech.net/killmails/{id}/{hash}
    """
    killmail_id, killmail_hash = parse_esi_url(esi_url)

    esi_km = await fetch_esi_killmail(killmail_id, killmail_hash)
    victim: dict = esi_km.get("victim", {})

    ship_type_id: int = victim.get("ship_type_id", 0)
    victim_character_id: int = victim.get("character_id", 0)
    killed_at_str: str = esi_km.get("killmail_time", "")
    killed_at: datetime | None = None
    if killed_at_str:
        killed_at = datetime.fromisoformat(killed_at_str.replace("Z", "+00:00"))

    ship_name = await resolve_type_name(ship_type_id) if ship_type_id else ""

    items = []
    for raw_item in victim.get("items", []):
        if "type_id" not in raw_item:
            continue
        qty_d = raw_item.get("quantity_destroyed", 0)
        qty_p = raw_item.get("quantity_dropped", 0)
        if qty_d > 0 or qty_p > 0:
            items.append({
                "type_id": raw_item["type_id"],
                "qty_destroyed": qty_d,
                "qty_dropped": qty_p,
            })

    return {
        "killmail_id": killmail_id,
        "killmail_hash": killmail_hash,
        "zkb_url": f"https://zkillboard.com/kill/{killmail_id}/",
        "ship_type_id": ship_type_id,
        "ship_name": ship_name,
        "victim_character_id": victim_character_id,
        "killed_at": killed_at,
        "loss_value_raw": 0.0,
        "items": items,
    }


async def fetch_character_losses(
    character_id: int,
    start_time: datetime,
    end_time: datetime,
    db,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """
    通过 ESI /characters/{id}/killmails/recent/ 拉取角色在时间窗口内的损失记录。
    需要角色已授权 esi-killmails.read_killmails.v1；未授权时返回空列表。

    返回列表每项格式与 get_killmail_info 输出一致（ship_name 为空，调用方补全）。
    loss_value_raw 固定为 0.0，实际补损金额由调用方通过市场模块计算。
    """
    import asyncio
    from helm_plugin_srp.services import esi as esi_svc

    # 获取有效 token（角色未绑定或未授权 scope 时静默跳过该角色）
    try:
        token, _ = await esi_svc.get_valid_token(character_id, db)
    except ValueError:
        return []

    losses: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        refs = await esi_svc.get_character_killmails_page(character_id, token, page)
        if not refs:
            break

        # 并发拉取本页所有完整 killmail
        tasks = [fetch_esi_killmail(r["killmail_id"], r["killmail_hash"]) for r in refs]
        results: list[Any] = await asyncio.gather(*tasks, return_exceptions=True)

        reached_before_window = False
        for ref, km_data in zip(refs, results):
            if isinstance(km_data, Exception):
                continue

            km_time_str: str = km_data.get("killmail_time", "")
            if not km_time_str:
                continue
            km_time = datetime.fromisoformat(km_time_str.replace("Z", "+00:00"))

            if km_time > end_time:
                continue
            if km_time < start_time:
                # ESI 按 killmail_id 倒序，本条之后均更早，可终止
                reached_before_window = True
                break

            victim: dict = km_data.get("victim", {})
            if victim.get("character_id") != character_id:
                # kills（该角色是攻击者）跳过
                continue

            losses.append({
                "killmail_id": ref["killmail_id"],
                "killmail_hash": ref["killmail_hash"],
                "zkb_url": f"https://zkillboard.com/kill/{ref['killmail_id']}/",
                "ship_type_id": victim.get("ship_type_id", 0),
                "ship_name": "",
                "victim_character_id": character_id,
                "killed_at": km_time,
                "loss_value_raw": 0.0,
            })

        if reached_before_window or len(refs) < 1000:
            break

    return losses
