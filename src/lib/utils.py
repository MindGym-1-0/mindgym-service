from __future__ import annotations

from uuid import UUID


def cast_row_uuids(row: dict) -> dict:
    row_copy = dict(row)
    if "id" in row_copy and row_copy["id"]:
        row_copy["id"] = UUID(str(row_copy["id"]))
    if "user_id" in row_copy and row_copy["user_id"]:
        row_copy["user_id"] = UUID(str(row_copy["user_id"]))
    return row_copy
