"""Shared exception helpers for API validation handlers."""

from __future__ import annotations

from fastapi import HTTPException
from pydantic import ValidationError


def raise_400(exc: ValidationError) -> None:
    """Extracts Pydantic validation errors and reformats them into a 400 Bad Request."""
    # include_context=False prevents raw Python Exception objects from breaking JSON serialization
    raise HTTPException(
        status_code=400, 
        detail=exc.errors(include_url=False, include_context=False)
    ) from None