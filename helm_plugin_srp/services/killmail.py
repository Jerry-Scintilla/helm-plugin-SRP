"""zkillboard URL 解析 + ESI killmail 拉取工具。"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

_ZKB_URL_RE = re.compile(r"zkillboard\.com/kill/(\d+)", re.IGNORECASE)
_ZKB_API = "https://zkillboard.com/api/kills/killID/{killmail_id}/"
_ESI_BASE = "https://esi.evetech.net/latest"

# 常见舰船组 ID（用于描述）
_SHIP_GROUP_NAMES: dict[int, str] = {}


def parse_zkb_url(url: str) -> int:
    """从 zkillboard URL 中提取 killmail_id，解析失败时抛出 ValueError。"""
    m = _ZKB_URL_RE.search(url)
    if not m:
        raise ValueError(f"无效的 zkillboard URL，无法提取 killmail_id：{url}")
    return int(m.group(1))


async def fetch_zkb_killmail(killmail_id: int) -> dict[str, Any]:
    """
    调用 zkillboard API 获取击杀数据，返回包含 killmail_hash 和 zkb.totalValue 的原始数据。
    zkb API 返回格式：[{"killmail_id": ..., "killmail_hash": ..., "zkb": {"totalValue": ...}, ...}]
    """
    url = _ZKB_API.format(killmail_id=killmail_id)
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"User-Agent": "Helm-SRP-Plugin/0.1"})
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"zkillboard 未找到 killmail_id={killmail_id} 的记录")
    return data[0]


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


async def get_killmail_info(zkb_url: str) -> dict[str, Any]:
    """
    主入口：解析 zkillboard URL，拉取 zkb + ESI 数据，返回规范化结果：
    {
        killmail_id, killmail_hash, zkb_url,
        ship_type_id, ship_name,
        victim_character_id,
        killed_at,
        loss_value_raw,   ← zkb.totalValue（ISK）
    }
    """
    killmail_id = parse_zkb_url(zkb_url)
    zkb_data = await fetch_zkb_killmail(killmail_id)

    killmail_hash: str = zkb_data.get("killmail_hash", "")
    loss_value_raw: float = float(zkb_data.get("zkb", {}).get("totalValue", 0.0))

    esi_km = await fetch_esi_killmail(killmail_id, killmail_hash)
    victim: dict = esi_km.get("victim", {})

    ship_type_id: int = victim.get("ship_type_id", 0)
    victim_character_id: int = victim.get("character_id", 0)
    killed_at_str: str = esi_km.get("killmail_time", "")
    killed_at: datetime | None = None
    if killed_at_str:
        killed_at = datetime.fromisoformat(killed_at_str.replace("Z", "+00:00"))

    ship_name = await resolve_type_name(ship_type_id) if ship_type_id else ""

    return {
        "killmail_id": killmail_id,
        "killmail_hash": killmail_hash,
        "zkb_url": zkb_url,
        "ship_type_id": ship_type_id,
        "ship_name": ship_name,
        "victim_character_id": victim_character_id,
        "killed_at": killed_at,
        "loss_value_raw": loss_value_raw,
    }


async def fetch_character_losses(
    character_id: int,
    start_time: datetime,
    end_time: datetime,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """
    从 zkillboard API 拉取指定角色在时间窗口内的损失记录。
    返回列表，每项格式同 get_killmail_info 的输出（不含 ship_name，调用方按需补全）。

    zkb API: GET /api/losses/characterID/{char_id}/
    """
    base_url = f"https://zkillboard.com/api/losses/characterID/{character_id}/"
    losses: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for page in range(1, max_pages + 1):
            resp = await client.get(
                base_url,
                params={"page": page},
                headers={"User-Agent": "Helm-SRP-Plugin/0.1"},
            )
            if resp.status_code == 404:
                break
            resp.raise_for_status()
            page_data: list[dict] = resp.json()
            if not page_data:
                break

            reached_before_window = False
            for entry in page_data:
                km_id: int = entry.get("killmail_id", 0)
                km_hash: str = entry.get("killmail_hash", "")
                zkb_val: float = float(entry.get("zkb", {}).get("totalValue", 0.0))
                km_time_str: str = entry.get("killmail_time", "")
                if not km_time_str:
                    continue
                km_time = datetime.fromisoformat(km_time_str.replace("Z", "+00:00"))

                if km_time > end_time:
                    continue
                if km_time < start_time:
                    reached_before_window = True
                    break

                victim_char_id: int = entry.get("victim", {}).get("character_id", 0)
                if victim_char_id != character_id:
                    # 跳过该角色作为击杀者的记录（zkb losses API 理论上不含此情况）
                    continue

                losses.append({
                    "killmail_id": km_id,
                    "killmail_hash": km_hash,
                    "zkb_url": f"https://zkillboard.com/kill/{km_id}/",
                    "ship_type_id": entry.get("victim", {}).get("ship_type_id", 0),
                    "ship_name": "",
                    "victim_character_id": victim_char_id,
                    "killed_at": km_time,
                    "loss_value_raw": zkb_val,
                })

            if reached_before_window:
                break

    return losses
