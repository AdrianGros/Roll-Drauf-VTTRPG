"""Capture legacy rows only while their runtime scope is locked."""

from datetime import date, datetime

from sqlalchemy import select

from vtt.creation_engine.kernel.records import refuse
from vtt.models.character import Character
from vtt.models.equipment import Equipment
from vtt.models.inventory_item import InventoryItem
from vtt.models.spell import Spell
from vtt.models.token_state import TokenState


def row_json(row):
    result = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        result[column.name] = value.isoformat() if isinstance(value, (date, datetime)) else value
    return result


def characters(tx):
    query = select(Character).where(Character.deleted_at.is_(None))
    query = query.where(Character.campaign_id == tx.scope.campaign_id) if tx.scope.kind == "campaign" else query.where(
        Character.campaign_id.is_(None), Character.user_id == tx.scope.owner_user_id)
    rows = list(tx.session.scalars(query.order_by(Character.id).with_for_update()))
    if len(rows) > 128:
        refuse("BUDGET_EXCEEDED", "migration requires an explicitly bounded job")
    return rows


def snapshot(tx, character):
    result = {"character": row_json(character)}
    for key, model in (("equipment", Equipment), ("inventory", InventoryItem), ("spells", Spell), ("tokens", TokenState)):
        query = select(model).where(model.character_id == character.id)
        if model is TokenState:
            query = query.where(model.deleted_at.is_(None), model.campaign_id == tx.scope.campaign_id)
        result[key] = [row_json(row) for row in tx.session.scalars(query.order_by(model.id).with_for_update())]
    if sum(len(result[key]) for key in ("equipment", "inventory", "spells", "tokens")) > 128:
        refuse("BUDGET_EXCEEDED", "character migration exceeds interactive instance limit")
    return result
