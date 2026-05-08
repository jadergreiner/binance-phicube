"""Utilitários de serialização de data/hora para contratos da API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

BRAZIL_TIMEZONE = "America/Sao_Paulo"
_BRAZIL_ZONE = ZoneInfo(BRAZIL_TIMEZONE)


def _coerce_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.replace(tzinfo=UTC)
    return dt


def to_iso8601_utc(value: Any) -> str | None:
    dt = _coerce_datetime(value)
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def to_brazil_datetime_str(value: Any) -> str | None:
    dt = _coerce_datetime(value)
    if dt is None:
        return None
    return dt.astimezone(_BRAZIL_ZONE).strftime("%d/%m/%Y %H:%M:%S")


def enrich_datetime_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    enriched = dict(payload)
    for field in fields:
        iso_value = to_iso8601_utc(enriched.get(field))
        if iso_value is not None:
            enriched[field] = iso_value

        br_value = to_brazil_datetime_str(enriched.get(field))
        if br_value is not None:
            enriched[f"{field}_br"] = br_value
    return enriched
