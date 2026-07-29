from __future__ import annotations

import re

import numpy as np
import pandas as pd


BROAD_EXACT_NAMES: frozenset[str] = frozenset(
    {
        # English
        "system",
        "systems",
        "strips",
        "powder",
        "powders",
        "products",
        "supplies",
        "parts",
        "other",
        "others",
        "miscellaneous",
        "grass",
        # Chinese
        "系统",
        "条",
        "粉末",
        "产品",
        "用品",
        "零件",
        "其他",
        "其它",
        "杂项",
        "草",
        # Japanese
        "システム",
        "ストリップ",
        "粉末",
        "製品",
        "用品",
        "部品",
        "その他",
        "草",
        # German
        "system",
        "systeme",
        "streifen",
        "pulver",
        "produkte",
        "teile",
        "sonstige",
        "gras",
    }
)


def _normalized_text(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.casefold()
        .str.replace(r"[\s\-_/]+", " ", regex=True)
        .str.strip(" .,:;|()[]{}")
    )


def _node_depth(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()

    def depth(value: str) -> float:
        if not value:
            return np.nan
        segments = [part.strip() for part in re.split(r"\s*(?:>|›|»|→|/|\\)\s*", value) if part.strip()]
        return float(len(segments)) if segments else np.nan

    return text.map(depth).astype("float64")


def add_actionability_v32(frame: pd.DataFrame) -> pd.DataFrame:
    """Add a transparent warning for labels too broad to be product-development targets.

    This does not change the market score or A/B/C/D rule class. It is a separate
    operational filter. Users can turn the filter off and inspect the node manually.
    """

    result = frame.copy()
    category = _normalized_text(result.get("Category", pd.Series("", index=result.index)))
    local = _normalized_text(result.get("CategoryLocal", pd.Series("", index=result.index)))
    node_path = result.get("NodePath", pd.Series("", index=result.index)).astype("string").fillna("")
    depth = _node_depth(node_path)

    exact_generic = category.isin(BROAD_EXACT_NAMES) | local.isin(BROAD_EXACT_NAMES)
    missing_names = category.eq("") & local.eq("")
    path_available = node_path.str.strip().ne("")
    shallow_path = path_available & depth.le(2)

    result["NodePathDepth"] = depth
    result["BroadNodeWarning"] = (exact_generic | missing_names).fillna(False).astype(bool)
    result["ShallowNodeWarning"] = shallow_path.fillna(False).astype(bool)
    result["ActionabilityStatus"] = np.select(
        [
            result["BroadNodeWarning"],
            result["ShallowNodeWarning"],
            path_available & depth.ge(4),
        ],
        [
            "名称过宽：需查看Node Path后再决定",
            "层级偏浅：可能是父级/聚合节点",
            "层级较具体",
        ],
        default="具体度待人工确认",
    )
    result["ActionabilityScore"] = np.select(
        [
            result["BroadNodeWarning"],
            result["ShallowNodeWarning"],
            path_available & depth.ge(4),
            path_available & depth.eq(3),
        ],
        [30.0, 55.0, 90.0, 78.0],
        default=68.0,
    ).astype("float64")
    return result
