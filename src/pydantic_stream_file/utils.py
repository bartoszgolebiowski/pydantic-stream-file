from __future__ import annotations

from typing import Any, Collection


def clean_null_values(
    data: dict[str, Any],
    null_values: Collection[str],
) -> dict[str, Any]:
    """Coerce sentinel string values to None in a dictionary."""
    if not null_values:
        return data

    null_set = set(null_values) if not isinstance(null_values, set) else null_values
    cleaned: dict[str, Any] = {}
    for key, val in data.items():
        if isinstance(val, str) and val in null_set:
            cleaned[key] = None
        else:
            cleaned[key] = val
    return cleaned
