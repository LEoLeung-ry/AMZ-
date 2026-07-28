from __future__ import annotations

import re

import pandas as pd

from . import engine
from .config import ROOT_CATEGORY_GROUPS


def _safe_scalar_text(value: object) -> str:
    if value is None:
        return ""
    try:
        missing = pd.isna(value)
        if isinstance(missing, bool) and missing:
            return ""
    except Exception:
        pass
    return str(value)


def _normalize_header(value: object) -> str:
    text = _safe_scalar_text(value).strip().replace("\u3000", " ")
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def _make_unique_headers(values) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for index, value in enumerate(values):
        base = _safe_scalar_text(value).strip() or f"未命名列_{index + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append(base if count == 0 else f"{base}_{count + 1}")
    return result


def _standardize_root(value: object) -> str:
    raw = _safe_scalar_text(value).strip()
    key = _normalize_header(raw).replace("_", "-")
    if not key:
        return "未分类"
    for standard, aliases in ROOT_CATEGORY_GROUPS.items():
        normalized_aliases = {_normalize_header(alias).replace("_", "-") for alias in aliases}
        if key in normalized_aliases:
            return standard
    return raw


def install_na_safe_text_patch() -> None:
    """Replace scalar text helpers that must never evaluate pd.NA as bool."""
    engine.normalize_header = _normalize_header
    engine._make_unique_headers = _make_unique_headers
    engine.standardize_root = _standardize_root
