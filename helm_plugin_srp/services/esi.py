"""ESI 认证辅助：token 管理 + 角色 killmail 列表拉取。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_ESI_BASE = "https://esi.evetech.net/latest"
_KILLMAILS_SCOPE = "esi-killmails.read_killmails.v1"


async def get_valid_token(character_id: int, db: AsyncSession) -> tuple[str, str]:
    """
    获取角色的有效 ESI access token，必要时自动刷新。
    返回 (access_token, refresh_token)。
    角色未找到或缺少 esi-killmails scope 时抛出 ValueError。
    """
    from app.models.character import Character
    from app.esi.oauth import refresh_access_token

    result = await db.execute(
        select(Character).where(Character.character_id == character_id)
    )
    char = result.scalar_one_or_none()
    if char is None:
        raise ValueError(f"角色 {character_id} 未在 Helm 中绑定")

    granted = set((char.scopes or "").split())
    if _KILLMAILS_SCOPE not in granted:
        raise ValueError(f"角色 {character_id} 未授权 {_KILLMAILS_SCOPE}")

    # token 30 秒内过期时提前刷新
    now = datetime.now(UTC)
    if char.token_expires_at is None or char.token_expires_at <= now + timedelta(seconds=30):
        new_tokens = await refresh_access_token(char.refresh_token)
        char.access_token = new_tokens["access_token"]
        char.refresh_token = new_tokens.get("refresh_token", char.refresh_token)
        char.token_expires_at = now + timedelta(seconds=new_tokens.get("expires_in", 1200))
        await db.commit()

    return char.access_token, char.refresh_token


async def get_character_killmails_page(
    character_id: int,
    token: str,
    page: int = 1,
) -> list[dict[str, Any]]:
    """
    GET /characters/{character_id}/killmails/recent/?page={page}
    返回 [{killmail_id, killmail_hash}]，按 killmail_id 倒序（新→旧）。
    页面为空或 404 时返回空列表。
    """
    url = f"{_ESI_BASE}/characters/{character_id}/killmails/recent/"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            url,
            params={"page": page},
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Helm-SRP-Plugin/0.1",
            },
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
    return resp.json() or []
