"""Configuration CRUD endpoints."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlmodel import delete, select

from app import db as db_module
from app.data_sources import make_source
from app.models.dynamic_pool import DynamicPoolEntry
from app.models.static_pool import StaticPool
from app.models.strategy_param import StrategyParam
from app.models.theme_keyword import ThemeKeyword
from app.schemas import (
    DynamicPoolEntryOut,
    DynamicPoolSyncResult,
    DynamicPoolUpdate,
    StaticPoolEntry,
    StaticPoolReplace,
    StaticPoolUpdate,
    StrategyParams,
    ThemeDictionary,
)

router = APIRouter(tags=["configs"])


# ────────────── Static Pool ──────────────

@router.get("/pool", response_model=list[StaticPoolEntry])
def list_pool() -> list[StaticPoolEntry]:
    with db_module.session_scope() as session:
        rows = list(session.exec(select(StaticPool).order_by(StaticPool.code)).all())
        return [StaticPoolEntry.model_validate(r) for r in rows]


@router.post("/pool", response_model=list[StaticPoolEntry], status_code=status.HTTP_200_OK)
def replace_pool(body: StaticPoolReplace) -> list[StaticPoolEntry]:
    with db_module.session_scope() as session:
        session.exec(delete(StaticPool))
        session.flush()
        now = datetime.utcnow()
        for entry in body.entries:
            session.add(
                StaticPool(
                    code=entry.code,
                    display_name=entry.display_name,
                    enabled=entry.enabled,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.flush()
        rows = list(session.exec(select(StaticPool).order_by(StaticPool.code)).all())
        return [StaticPoolEntry.model_validate(r) for r in rows]


@router.put("/pool/{code}", response_model=StaticPoolEntry)
def update_pool_entry(code: str, body: StaticPoolUpdate) -> StaticPoolEntry:
    with db_module.session_scope() as session:
        entry = session.get(StaticPool, code)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"StaticPool entry not found: {code}")
        if body.enabled is not None:
            entry.enabled = body.enabled
        if body.display_name is not None:
            entry.display_name = body.display_name
        entry.updated_at = datetime.utcnow()
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return StaticPoolEntry.model_validate(entry)


@router.delete("/pool/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pool_entry(code: str) -> None:
    with db_module.session_scope() as session:
        entry = session.get(StaticPool, code)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"StaticPool entry not found: {code}")
        session.delete(entry)


# ────────────── Themes ──────────────

@router.get("/themes", response_model=ThemeDictionary)
def list_themes() -> ThemeDictionary:
    with db_module.session_scope() as session:
        rows = list(
            session.exec(
                select(ThemeKeyword).order_by(ThemeKeyword.theme, ThemeKeyword.keyword)
            ).all()
        )
        themes: dict[str, list[str]] = {}
        for row in rows:
            themes.setdefault(row.theme, []).append(row.keyword)
        return ThemeDictionary(themes=themes)


@router.put("/themes", response_model=ThemeDictionary)
def replace_themes(body: ThemeDictionary) -> ThemeDictionary:
    with db_module.session_scope() as session:
        session.exec(delete(ThemeKeyword))
        session.flush()
        for theme, keywords in body.themes.items():
            for kw in keywords:
                session.add(ThemeKeyword(theme=theme, keyword=kw))
        session.flush()
        rows = list(
            session.exec(
                select(ThemeKeyword).order_by(ThemeKeyword.theme, ThemeKeyword.keyword)
            ).all()
        )
        themes: dict[str, list[str]] = {}
        for row in rows:
            themes.setdefault(row.theme, []).append(row.keyword)
        return ThemeDictionary(themes=themes)


# ────────────── Strategy Params ──────────────

@router.get("/strategy", response_model=StrategyParams)
def get_strategy() -> StrategyParams:
    with db_module.session_scope() as session:
        rows = list(session.exec(select(StrategyParam)).all())
        merged: dict = {}
        for row in rows:
            try:
                merged[row.key] = json.loads(row.value_json)
            except json.JSONDecodeError:
                merged[row.key] = row.value_json
        return StrategyParams(params=merged)


@router.put("/strategy", response_model=StrategyParams)
def update_strategy(body: StrategyParams) -> StrategyParams:
    with db_module.session_scope() as session:
        now = datetime.utcnow()
        for key, value in body.params.items():
            existing = session.get(StrategyParam, key)
            if existing is None:
                session.add(
                    StrategyParam(key=key, value_json=json.dumps(value), updated_at=now)
                )
            else:
                existing.value_json = json.dumps(value)
                existing.updated_at = now
                session.add(existing)
        session.flush()
        rows = list(session.exec(select(StrategyParam)).all())
        merged: dict = {}
        for row in rows:
            try:
                merged[row.key] = json.loads(row.value_json)
            except json.JSONDecodeError:
                merged[row.key] = row.value_json
        return StrategyParams(params=merged)


# ────────────── Dynamic Pool ──────────────


@router.get("/pool/dynamic", response_model=list[DynamicPoolEntryOut])
def list_dynamic_pool() -> list[DynamicPoolEntryOut]:
    with db_module.session_scope() as session:
        rows = list(
            session.exec(select(DynamicPoolEntry).order_by(DynamicPoolEntry.code)).all()
        )
        return [DynamicPoolEntryOut.model_validate(r) for r in rows]


@router.post("/pool/dynamic/sync", response_model=DynamicPoolSyncResult)
def sync_dynamic_pool() -> DynamicPoolSyncResult:
    """Pull the full ETF universe from the active source and UPSERT rows.

    Existing `is_enabled` flags are preserved (sync only refreshes code, name,
    and last_synced_at).
    """
    source = make_source()  # uses ETF_DATA_SOURCE env var
    entries = source.all_etf_entries(datetime.utcnow().date())
    now = datetime.utcnow()
    with db_module.session_scope() as session:
        for code, name in entries:
            existing = session.get(DynamicPoolEntry, code)
            if existing is None:
                session.add(
                    DynamicPoolEntry(
                        code=code,
                        name=name,
                        is_enabled=False,
                        last_synced_at=now,
                    )
                )
            else:
                existing.name = name
                existing.last_synced_at = now
                session.add(existing)
        enabled = len(
            list(
                session.exec(
                    select(DynamicPoolEntry).where(DynamicPoolEntry.is_enabled.is_(True))
                ).all()
            )
        )
        total = len(entries)
        return DynamicPoolSyncResult(synced=total, total=total, enabled=enabled)


@router.patch("/pool/dynamic/{code}", response_model=DynamicPoolEntryOut)
def patch_dynamic_pool(code: str, body: DynamicPoolUpdate) -> DynamicPoolEntryOut:
    with db_module.session_scope() as session:
        entry = session.get(DynamicPoolEntry, code)
        if entry is None:
            raise HTTPException(
                status_code=404, detail=f"DynamicPoolEntry not found: {code}"
            )
        if body.is_enabled is not None:
            entry.is_enabled = body.is_enabled
        session.add(entry)
        session.flush()
        session.refresh(entry)
        return DynamicPoolEntryOut.model_validate(entry)
