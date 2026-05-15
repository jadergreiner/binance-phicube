from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, TypeVar, cast

T = TypeVar("T")

_SECRET_KEYS = {"api_key", "api_secret", "token", "access_token", "refresh_token", "secret"}
_SENSITIVE_POLICY: str = "omit"
_ADAPTERS: dict[type[Any], Any] = {}


class Serializable(Protocol):
    def to_dict(self) -> dict[str, Any]: ...


def set_sensitive_policy(policy: str) -> None:
    if policy not in {"omit", "mask"}:
        raise ValueError("policy must be 'omit' or 'mask'")
    global _SENSITIVE_POLICY
    _SENSITIVE_POLICY = policy


def register_adapter(type_: type[Any], adapter: Any) -> None:
    _ADAPTERS[type_] = adapter


def clear_adapters() -> None:
    _ADAPTERS.clear()


def _is_sensitive(name: str) -> bool:
    lowered = name.lower()
    return lowered in _SECRET_KEYS or lowered.endswith("_token") or lowered.endswith("_secret")


def _adapt(value: Any) -> Any:
    for adapter_type, adapter in _ADAPTERS.items():
        if isinstance(value, adapter_type):
            return adapter(value)
    return value


def _serialize_value(value: Any, field_name: str, seen: set[int]) -> Any:
    if _is_sensitive(field_name):
        if _SENSITIVE_POLICY == "omit":
            return None
        return "***"

    value = _adapt(value)

    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value
    if isinstance(value, list):
        return [_serialize_value(item, field_name, seen) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item, field_name, seen) for item in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v, str(k), seen) for k, v in value.items()}

    object_id = id(value)
    if object_id in seen:
        raise ValueError("cyclic_reference_detected")

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            try:
                return to_dict(_seen=seen)
            except TypeError:
                return to_dict()
        finally:
            pass

    raise TypeError(f"unsupported_serialization_type: {type(value).__name__}")


def auto_dict(cls: type[T]) -> type[T]:
    if not is_dataclass(cls):
        raise TypeError(f"@auto_dict requires a dataclass, got {cls.__name__}")

    if getattr(cls, "to_dict", None) is not None:
        return cls

    field_list = fields(cls)

    def to_dict(self: Any, _seen: set[int] | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        seen: set[int] = _seen if _seen is not None else set()
        object_id = id(self)
        if object_id in seen:
            raise ValueError("cyclic_reference_detected")
        seen.add(object_id)
        for f in field_list:
            serialized = _serialize_value(getattr(self, f.name), f.name, seen)
            if serialized is None and _is_sensitive(f.name) and _SENSITIVE_POLICY == "omit":
                continue
            result[f.name] = serialized
        seen.remove(object_id)
        return result

    setattr(cls, "to_dict", to_dict)
    return cast(type[T], cls)
