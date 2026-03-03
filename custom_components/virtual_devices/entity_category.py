"""Helpers for parsing Home Assistant entity categories."""
from __future__ import annotations

import logging

from homeassistant.helpers.entity import EntityCategory

_LOGGER = logging.getLogger(__name__)

_ENTITY_CATEGORY_MAP: dict[str, EntityCategory] = {
    "config": EntityCategory.CONFIG,
    "diagnostic": EntityCategory.DIAGNOSTIC,
}


def parse_entity_category(
    value: str | None,
    *,
    default: EntityCategory | None = EntityCategory.DIAGNOSTIC,
    context: str = "entity",
) -> EntityCategory | None:
    """Convert a string category into a Home Assistant EntityCategory."""
    if value is None:
        return default

    category = _ENTITY_CATEGORY_MAP.get(value.strip().lower())
    if category is not None:
        return category

    default_value = default.value if default is not None else "none"
    _LOGGER.warning(
        "Invalid entity_category '%s' for %s; using %s",
        value,
        context,
        default_value,
    )
    return default
