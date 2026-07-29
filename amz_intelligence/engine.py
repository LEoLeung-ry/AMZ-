from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from typing import Iterable, Mapping

import numpy as np
import pandas as pd
import requests

from .config import (
    COLUMN_ALIASES,
    DIGITAL_HIGH_RISK_ROOTS,
    DIGITAL_HIGH_RISK_TERMS,
    DIGITAL_MEDIUM_RISK_ROOTS,
    FACTOR_LABELS,
    MARKETS,
    ROOT_CATEGORY_GROUPS,
    STRATEGY_PRESETS,
    MarketConfig,
)


class DataLoadError(RuntimeError):
    """Raised when one marketplace source cannot be fetched or parsed."""


def normalize_header(value: object) -> str:
    text = str(value or "").strip().replace("\u3000", " ")
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\s+", "", text)
    return text.casefold()


def _make_unique_headers(values: Iterable[object]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for i, value in enumerate(values):
        base = str(value or "").strip() or f"未命名列_{i + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.append(base if count == 0 else f"{base}_{count + 1}")
    return result


def _header_alias_keys() -> set[str]:
    keys: set[str] = set()
    for aliases in COLUMN_ALIASES.values():
        keys.update(normalize_header(alias) for alias in aliases)
    return keys


def _detect_header_row(raw: pd.DataFrame, scan_rows: int = 30) -> int:
    required_alias_groups = (
        COLUMN_ALIASES["category_id"],
        COLUMN_ALIASES["sales"],
        COLUMN_ALIASES["revenue"],
        COLUMN_ALIASES["asin_count"],
    )
    all_keys = _header_alias_keys()
    best_row = 0
    best_score = -1
    for row_idx in range(min(scan_rows, len(raw))):
        row_keys = {normalize_header(v) for v in raw.iloc[row_idx].tolist() if str(v).strip()}
        broad_score = sum(1 for key in row_keys if key in all_keys)
        required_score = sum(
            1
            for group in required_alias_groups
            if any(normalize_header(alias) in row_keys for alias in group)
        )
        score = required_score * 100 + broad_score
        if score > best_score:
            best_row = row_idx
            best_score = score
    if best_score < 300:
        raise DataLoadError("未能识别表头：至少需要类目ID、销量、销售额等核心字段。")
    return best_row


def parse_csv_payload(content: bytes) -> tuple[pd.DataFrame, dict[str, object]]:
    """Parse a published sheet defensively and detect a displaced header row."""
    stripped = content.lstrip()
    if not stripped:
        raise DataLoadError("数据源返回空内容。")
    if stripped.startswith(b"<"):
        preview = stripped[:160].decode("utf-8", errors="ignore")
        raise DataLoadError(f"数据源返回了网页而不是 CSV：{preview}")

    last_error: Exception | None = None
    raw: pd.DataFrame | None = None
    used_encoding = ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            raw = pd.read_csv(
                BytesIO(content),
                header=None,
                dtype="string",
                keep_default_na=False,
                encoding=encoding,
                engine="python",
                on_bad_lines="skip",
            )
            used_encoding = encoding
            break
        except Exception as exc:  # pragma: no cover - only used for malformed remote sources
            last_error = exc
    if raw is None:
        raise DataLoadError(f"CSV 解析失败：{last_error}")

    raw = raw.dropna(how="all").reset_index(drop=True)
    if raw.empty:
        raise DataLoadError("CSV 中没有可读取的数据行。")

    header_row = _detect_header_row(raw)
    headers = _make_unique_headers(raw.iloc[header_row].tolist())
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = headers
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.dropna(how="all").reset_index(drop=True)

    # Remove accidental repeated header rows inside exported sheets.
    normalized_headers = [normalize_header(v) for v in headers]
    if not df.empty:
        repeated = pd.Series(False, index=df.index)
        for col, normalized in zip(headers, normalized_headers):
            repeated |= df[col].astype("string").map(normalize_header).eq(normalized)
        # A row is considered a repeated header only if several columns match their own header.
        matches = pd.DataFrame(
            {
                col: df[col].astype("string").map(normalize_header).eq(norm)
                for col, norm in zip(headers, normalized_headers)
            }
        ).sum(axis=1)
        df = df.loc[matches < 3].reset_index(drop=True)

    metadata = {
        "encoding": used_encoding,
        "header_row": int(header_row + 1),
        "raw_rows": int(len(raw)),
        "parsed_rows": int(len(df)),
        "columns": headers,
    }
    return df, metadata


def find_column(columns: Iterable[object], alias_key: str) -> str | None:
    candidates = COLUMN_ALIASES[alias_key]
    normalized_columns = [(str(col), normalize_header(col)) for col in columns]
    for candidate in candidates:
        key = normalize_header(candidate)
        for original, normalized in normalized_columns:
            if normalized == key:
                return original
        for original, normalized in normalized_columns:
            if normalized.startswith(key):
                return original
    return None


def text_series(df: pd.DataFrame, source: str | None) -> pd.Series:
    if source is None:
        return pd.Series("", index=df.index, dtype="string")
    return (
        df[source]
        .astype("string")
        .str.strip()
        .replace({"<NA>": "", "nan": "", "None": ""})
        .fillna("")
    )


def numeric_series(df: pd.DataFrame, source: str | None) -> pd.Series:
    if source is None:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    series = df[source]
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("，", "", regex=False)
        .str.replace("¥", "", regex=False)
        .str.replace("￥", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace(r"[^0-9eE+\-.]", "", regex=True)
        .replace({"": pd.NA, "-": pd.NA, ".": pd.NA, "+": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce").astype("float64")


def normalize_category_id(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip().replace(",", "")
    if not text or text.casefold() in {"nan", "none", "<na>"}:
        return ""
    try:
        number = Decimal(text)
        if not number.is_finite():
            return ""
        integral = number.to_integral_value()
        if number == integral and integral >= 0:
            return format(integral, "f")
    except (InvalidOperation, ValueError):
        pass
    match = re.search(r"(?<!\d)(\d{5,14})(?!\d)", text)
    return match.group(1) if match else text


def _category_id_from_link(link: str) -> str:
    if not link:
        return ""
    patterns = (
        r"/node/(\d{5,14})(?:[/?#]|$)",
        r"/b\?node=(\d{5,14})(?:[&#]|$)",
        r"/(\d{5,14})(?:[/?#]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    return ""


def standardize_root(value: object) -> str:
    raw = str(value or "").strip()
    key = normalize_header(raw).replace("_", "-")
    if not key:
        return "未分类"
    for standard, aliases in ROOT_CATEGORY_GROUPS.items():
        normalized_aliases = {normalize_header(alias).replace("_", "-") for alias in aliases}
        if key in normalized_aliases:
            return standard
    return raw


def infer_digital_risk(root_raw: str, category_text: str) -> str:
    root_key = normalize_header(root_raw).replace("_", "-")
    text = category_text.casefold()
    if root_key in DIGITAL_HIGH_RISK_ROOTS or any(term in text for term in DIGITAL_HIGH_RISK_TERMS):
        return "高"
    if root_key in DIGITAL_MEDIUM_RISK_ROOTS:
        return "中"
    return "低"


def _safe_divide(numerator: pd.Series, denominator: pd.Series, multiplier: float = 1.0) -> pd.Series:
    n = pd.to_numeric(numerator, errors="coerce").astype("float64")
    d = pd.to_numeric(denominator, errors="coerce").astype("float64")
    valid = d.gt(0).fillna(False)
    result = pd.Series(np.nan, index=n.index, dtype="float64")
    result.loc[valid] = (n.loc[valid] / d.loc[valid]) * multiplier
    return result.replace([np.inf, -np.inf], np.nan)


def _valid_source_or_calculated(source: pd.Series, calculated: pd.Series) -> pd.Series:
    src = pd.to_numeric(source, errors="coerce").astype("float64")
    valid = src.gt(0).fillna(False)
    return src.where(valid, calculated)


def build_category_key(df: pd.DataFrame) -> pd.Series:
    ids = df["CategoryID"].fillna("").astype(str).str.strip()
    fallback = (
        df["RootStandard"].fillna("未分类").astype(str)
        + "|"
        + df["CategoryCN"].fillna("").astype(str)
        + "|"
        + df["CategoryLocal"].fillna("").astype(str)
    )
    stable = ids.where(ids.ne(""), fallback)
    return df["MarketCode"].astype(str) + "_" + stable


def _percentile(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    valid_count = int(values.notna().sum())
    if valid_count <= 1:
        base = pd.Series(0.5, index=series.index, dtype="float64")
    else:
        base = values.rank(method="average", pct=True).fillna(0.5).astype("float64")
    return base if higher_is_better else 1.0 - base


def _group_percentile(
    df: pd.DataFrame,
    column: str,
    group_columns: list[str],
    higher_is_better: bool = True,
) -> pd.Series:
    result = pd.Series(0.5, index=df.index, dtype="float64")
    for _, index in df.groupby(group_columns, dropna=False, observed=True).groups.items():
        result.loc[index] = _percentile(df.loc[index, column], higher_is_better)
    return result


def _weighted_average(parts: Mapping[str, tuple[pd.Series, float]], index: pd.Index) -> pd.Series:
    numerator = pd.Series(0.0, index=index, dtype="float64")
    denominator = pd.Series(0.0, index=index, dtype="float64")
    for _, (series, weight) in parts.items():
        values = pd.to_numeric(series, errors="coerce").astype("float64")
        valid = values.notna()
        numerator.loc[valid] += values.loc[valid] * weight
        denominator.loc[valid] += weight
    result = pd.Series(0.5, index=index, dtype="float64")
    valid_denominator = denominator.gt(0)
    result.loc[valid_denominator] = numerator.loc[valid_denominator] / denominator.loc[valid_denominator]
    return result.clip(0, 1)


def _factor_scores(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    p = lambda column, higher=True: _group_percentile(df, column, group_columns, higher)

    market = _weighted_average(
        {
            "revenue": (p("Revenue"), 0.45),
            "sales": (p("Sales"), 0.20),
            "search": (p("SearchVolume"), 0.35),
        },
        df.index,
    )
    demand = _weighted_average(
        {
            "search": (p("SearchVolume"), 0.40),
            "clicks": (p("Clicks"), 0.30),
            "views": (p("Views"), 0.20),
            "top_keyword": (p("TopKeywordValue"), 0.10),
        },
        df.index,
    )
    access = _weighted_average(
        {
            "revenue_per_asin": (p("RevenuePerASIN"), 0.35),
            "units_per_asin": (p("UnitsPerASIN"), 0.20),
            "search_per_asin": (p("SearchPerASIN"), 0.25),
            "asin_count": (p("ASINCount", False), 0.20),
        },
        df.index,
    )
    price_quality = (
        _group_percentile(df, "SourcePriceQuality", group_columns)
        if pd.to_numeric(df["SourcePriceQuality"], errors="coerce").notna().sum() > 1
        else pd.Series(np.nan, index=df.index, dtype="float64")
    )
    monetization = _weighted_average(
        {
            "asp": (p("ASP"), 0.30),
            "revenue_per_click": (p("RevenuePerClick"), 0.22),
            "revenue_per_search": (p("RevenuePerSearch"), 0.18),
            "revenue_per_asin": (p("RevenuePerASIN"), 0.18),
            "source_price_quality": (price_quality, 0.12),
        },
        df.index,
    )

    reliable_clicks = df["Clicks"].ge(100).fillna(False)
    reliable_views = df["Views"].ge(100).fillna(False)
    click_yield = df["ClickYieldPct"].where(reliable_clicks)
    ctr = df["CTRPct"].where(reliable_views)
    revenue_per_click = df["RevenuePerClick"].where(reliable_clicks)
    efficiency = _weighted_average(
        {
            "click_yield": (_group_percentile(df.assign(_v=click_yield), "_v", group_columns), 0.45),
            "ctr": (_group_percentile(df.assign(_v=ctr), "_v", group_columns), 0.25),
            "revenue_per_click": (
                _group_percentile(df.assign(_v=revenue_per_click), "_v", group_columns),
                0.30,
            ),
        },
        df.index,
    )

    source_pain = pd.to_numeric(df["SourcePain"], errors="coerce")
    if source_pain.notna().sum() > 1:
        source_pain_pct = _group_percentile(df, "SourcePain", group_columns)
    else:
        source_pain_pct = pd.Series(np.nan, index=df.index, dtype="float64")
    pain = _weighted_average(
        {
            "low_rating_share": (_group_percentile(df, "LowRatingShare", group_columns), 0.75),
            "source_pain": (source_pain_pct, 0.25),
        },
        df.index,
    )

    return pd.DataFrame(
        {
            "MarketFactor": (market * 100).round(1),
            "DemandFactor": (demand * 100).round(1),
            "AccessFactor": (access * 100).round(1),
            "MonetizationFactor": (monetization * 100).round(1),
            "EfficiencyFactor": (efficiency * 100).round(1),
            "PainFactor": (pain * 100).round(1),
        },
        index=df.index,
    )


def prepare_market_data(
    raw: pd.DataFrame,
    market: MarketConfig,
    *,
    fetch_metadata: Mapping[str, object] | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if raw.empty:
        raise DataLoadError(f"{market.name} 数据为空。")

    resolved = {key: find_column(raw.columns, key) for key in COLUMN_ALIASES}
    missing_required = [
        label
        for key, label in (
            ("sales", "近12个月销量"),
            ("revenue", "近12个月净销售额"),
            ("asin_count", "ASIN数量"),
        )
        if resolved[key] is None
    ]
    if missing_required:
        raise DataLoadError(f"{market.name} 缺少核心字段：{'、'.join(missing_required)}")

    df = pd.DataFrame(index=raw.index)
    df["MarketCode"] = market.code
    df["Market"] = market.name
    df["MarketFlag"] = market.flag
    df["CurrencyCode"] = market.currency_code
    df["CurrencySymbol"] = market.currency_symbol
    df["SnapshotLabel"] = market.snapshot_label

    df["CategoryCN"] = text_series(raw, resolved["category_cn"])
    df["CategoryLocal"] = text_series(raw, resolved["category_local"])
    df["RootRaw"] = text_series(raw, resolved["root_raw"]).replace("", "未分类")
    df["RootStandard"] = df["RootRaw"].map(standardize_root)
    df["NodePath"] = text_series(raw, resolved["node_path"])
    df["Link"] = text_series(raw, resolved["link"])

    raw_ids = text_series(raw, resolved["category_id"])
    df["CategoryID"] = raw_ids.map(normalize_category_id)
    link_ids = df["Link"].map(_category_id_from_link)
    df["CategoryID"] = df["CategoryID"].where(df["CategoryID"].ne(""), link_ids)

    df["Category"] = df["CategoryCN"].where(df["CategoryCN"].ne(""), df["CategoryLocal"])
    fallback_name = "类目ID " + df["CategoryID"].where(df["CategoryID"].ne(""), "未识别")
    df["Category"] = df["Category"].where(df["Category"].ne(""), fallback_name)

    df["Sales"] = numeric_series(raw, resolved["sales"])
    df["Revenue"] = numeric_series(raw, resolved["revenue"])
    df["SearchVolume"] = numeric_series(raw, resolved["search_volume"])
    df["Clicks"] = numeric_series(raw, resolved["clicks"])
    df["Views"] = numeric_series(raw, resolved["views"])
    df["SearchConversionSource"] = numeric_series(raw, resolved["search_conversion"])
    df["CTRSource"] = numeric_series(raw, resolved["ctr"])
    df["ASPSource"] = numeric_series(raw, resolved["asp"])
    df["TopKeyword"] = text_series(raw, resolved["top_keyword"])
    df["TopKeywordValue"] = numeric_series(raw, resolved["top_keyword_value"])
    df["ASINCount"] = numeric_series(raw, resolved["asin_count"])
    df["PriceBand"] = text_series(raw, resolved["price_band"])
    df["Rating4Plus"] = numeric_series(raw, resolved["rating_4_plus"])
    df["Rating3"] = numeric_series(raw, resolved["rating_3"])
    df["Rating2"] = numeric_series(raw, resolved["rating_2"])
    df["Rating1"] = numeric_series(raw, resolved["rating_1"])
    df["SourceSalesDensity"] = numeric_series(raw, resolved["source_sales_density"])
    df["SourceUnitDensity"] = numeric_series(raw, resolved["source_unit_density"])
    df["SourceSearchSupply"] = numeric_series(raw, resolved["source_search_supply"])
    df["SourcePriceQuality"] = numeric_series(raw, resolved["source_price_quality"])
    df["SourcePain"] = numeric_series(raw, resolved["source_pain"])
    df["SnapshotDateRaw"] = text_series(raw, resolved["snapshot_date"])
    parsed_snapshot = pd.to_datetime(df["SnapshotDateRaw"], errors="coerce")
    if parsed_snapshot.notna().sum() == 0:
        label_match = re.search(r"(20\d{2}-\d{2}-\d{2})", market.snapshot_label)
        if label_match:
            parsed_snapshot = pd.Series(
                pd.Timestamp(label_match.group(1)), index=df.index, dtype="datetime64[ns]"
            )
        else:
            fetched_at = str((fetch_metadata or {}).get("fetched_at", ""))
            fetched_date = pd.to_datetime(fetched_at, errors="coerce")
            parsed_snapshot = pd.Series(fetched_date, index=df.index, dtype="datetime64[ns]")
    df["SnapshotDate"] = parsed_snapshot

    calculated_asp = _safe_divide(df["Revenue"], df["Sales"])
    df["ASP"] = _valid_source_or_calculated(df["ASPSource"], calculated_asp)
    df["ClickYieldPct"] = _valid_source_or_calculated(
        df["SearchConversionSource"], _safe_divide(df["Sales"], df["Clicks"], 100)
    )
    df["CTRPct"] = _valid_source_or_calculated(
        df["CTRSource"], _safe_divide(df["Clicks"], df["Views"], 100)
    )
    df["RevenuePerASIN"] = _valid_source_or_calculated(
        df["SourceSalesDensity"], _safe_divide(df["Revenue"], df["ASINCount"])
    )
    df["UnitsPerASIN"] = _valid_source_or_calculated(
        df["SourceUnitDensity"], _safe_divide(df["Sales"], df["ASINCount"])
    )
    df["SearchPerASIN"] = _valid_source_or_calculated(
        df["SourceSearchSupply"], _safe_divide(df["SearchVolume"], df["ASINCount"])
    )
    df["ClicksPerASIN"] = _safe_divide(df["Clicks"], df["ASINCount"])
    df["RevenuePerSearch"] = _safe_divide(df["Revenue"], df["SearchVolume"])
    df["RevenuePerClick"] = _safe_divide(df["Revenue"], df["Clicks"])
    df["TopKeywordShare"] = _safe_divide(df["TopKeywordValue"], df["SearchVolume"])

    rating_columns = ["Rating4Plus", "Rating3", "Rating2", "Rating1"]
    df["RatingBucketTotal"] = df[rating_columns].sum(axis=1, min_count=1)
    df["LowRatingShare"] = _safe_divide(
        df[["Rating3", "Rating2", "Rating1"]].sum(axis=1, min_count=1),
        df["RatingBucketTotal"],
    )
    df["HighRatingShare"] = _safe_divide(df["Rating4Plus"], df["RatingBucketTotal"])

    category_text = (
        df["CategoryCN"].fillna("").astype(str)
        + " "
        + df["CategoryLocal"].fillna("").astype(str)
        + " "
        + df["TopKeyword"].fillna("").astype(str)
    )
    df["DigitalRisk"] = [
        infer_digital_risk(root, text)
        for root, text in zip(df["RootRaw"].astype(str), category_text.astype(str))
    ]

    flags: list[list[str]] = [[] for _ in range(len(df))]

    def add_flag(mask: pd.Series, label: str) -> None:
        safe = mask.fillna(False).to_numpy(dtype=bool)
        for i in np.flatnonzero(safe):
            flags[i].append(label)

    add_flag(df["CategoryCN"].eq("") & df["CategoryLocal"].eq(""), "名称缺失")
    add_flag(df["CategoryID"].eq(""), "类目ID缺失")
    add_flag(df["Sales"].le(0), "销量非正")
    add_flag(df["Revenue"].le(0), "销售额非正")
    add_flag(df["ASINCount"].le(0), "ASIN数量非正")
    add_flag(df["SearchVolume"].lt(100), "搜索量分母过小")
    add_flag(df["Clicks"].lt(100), "点击量分母过小")
    add_flag(df["Views"].lt(100), "浏览量分母过小")
    add_flag(df["ClickYieldPct"].gt(500), "点击产出效率极端")
    add_flag(df["CTRPct"].gt(100), "点击率极端")
    add_flag(df["Revenue"].lt(0) | df["Sales"].lt(0) | df["ASINCount"].lt(0), "负值")
    add_flag(
        df["RatingBucketTotal"].gt(np.maximum(df["ASINCount"].fillna(0) * 2, 100)),
        "评分桶口径异常",
    )
    add_flag(df["DigitalRisk"].eq("高"), "数字商品高风险")

    df["DataFlags"] = ["；".join(items) if items else "正常" for items in flags]
    df["DataFlagCount"] = [len(items) for items in flags]

    quality = pd.Series(100.0, index=df.index, dtype="float64")
    quality -= np.where((df["Sales"].le(0) | df["Revenue"].le(0)).fillna(True), 35, 0)
    quality -= np.where(df["ASINCount"].le(0).fillna(True), 20, 0)
    quality -= np.where((df["CategoryCN"].eq("") & df["CategoryLocal"].eq("")), 15, 0)
    quality -= np.where(df["CategoryID"].eq(""), 10, 0)
    quality -= np.where(df["Clicks"].lt(100).fillna(True), 5, 0)
    quality -= np.where(df["Views"].lt(100).fillna(True), 5, 0)
    quality -= np.where(df["SearchVolume"].lt(100).fillna(True), 5, 0)
    quality -= np.where(df["ClickYieldPct"].gt(500).fillna(False), 5, 0)
    quality -= np.where(df["CTRPct"].gt(100).fillna(False), 5, 0)
    quality -= np.where(df["DigitalRisk"].eq("高"), 10, 0)
    df["DataQualityScore"] = quality.clip(0, 100).round(1)
    df["ConfidenceFactor"] = df["DataQualityScore"]

    eligible_core = (
        df["Sales"].gt(0)
        & df["Revenue"].gt(0)
        & df["ASINCount"].gt(0)
        & df["Category"].ne("")
    ).fillna(False)
    df["EligibleCore"] = eligible_core.astype(bool)
    df["EligiblePhysical"] = (eligible_core & df["DigitalRisk"].ne("高")).astype(bool)

    # Supply an Amazon category link when the source lacks one.
    can_build_link = df["Link"].eq("") & df["CategoryID"].ne("") & df["RootRaw"].ne("未分类")
    built_links = (
        "https://www."
        + market.amazon_domain
        + "/gp/bestsellers/"
        + df["RootRaw"].astype(str)
        + "/"
        + df["CategoryID"].astype(str)
    )
    df["Link"] = df["Link"].where(~can_build_link, built_links)

    df["CategoryKey"] = build_category_key(df)
    before_dedup = len(df)
    df = df.sort_values(["EligibleCore", "Revenue"], ascending=[False, False])
    df = df.drop_duplicates(subset=["CategoryKey"], keep="first").reset_index(drop=True)
    duplicate_rows = before_dedup - len(df)

    global_factors = _factor_scores(df, ["MarketCode"])
    root_factors = _factor_scores(df, ["MarketCode", "RootStandard"])
    for column in global_factors.columns:
        df[column] = global_factors[column]
        df[f"{column}Root"] = root_factors[column]

    df["DemandSupplySignal"] = (
        0.45 * df["DemandFactor"]
        + 0.35 * df["AccessFactor"]
        + 0.20 * df["EfficiencyFactor"]
    ).round(1)
    df["DemandSupplyGap"] = (df["DemandFactor"] - (100 - df["AccessFactor"])).round(1)

    for categorical_column in (
        "MarketCode",
        "Market",
        "MarketFlag",
        "CurrencyCode",
        "CurrencySymbol",
        "SnapshotLabel",
        "RootRaw",
        "RootStandard",
        "DigitalRisk",
    ):
        df[categorical_column] = df[categorical_column].astype("category")

    diagnostics = {
        "market": asdict(market),
        "resolved_columns": resolved,
        "source_rows": int(len(raw)),
        "prepared_rows": int(len(df)),
        "duplicates_removed": int(duplicate_rows),
        "eligible_core_rows": int(df["EligibleCore"].sum()),
        "eligible_physical_rows": int(df["EligiblePhysical"].sum()),
        "missing_both_names": int(((df["CategoryCN"] == "") & (df["CategoryLocal"] == "")).sum()),
        "negative_revenue_rows": int(df["Revenue"].lt(0).sum()),
        "zero_sales_rows": int(df["Sales"].le(0).sum()),
        "zero_asin_rows": int(df["ASINCount"].le(0).sum()),
        "digital_high_risk_rows": int(df["DigitalRisk"].eq("高").sum()),
        "quality_median": float(df["DataQualityScore"].median()) if not df.empty else np.nan,
        "fetch_metadata": dict(fetch_metadata or {}),
    }
    return df, diagnostics


def apply_strategy_score(
    df: pd.DataFrame,
    strategy: str = "大单品",
    *,
    root_blend: float = 0.25,
    custom_weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    if strategy not in STRATEGY_PRESETS and custom_weights is None:
        raise ValueError(f"未知策略：{strategy}")
    weights = dict(custom_weights or STRATEGY_PRESETS[strategy])
    total = sum(max(0.0, float(v)) for v in weights.values())
    if total <= 0:
        raise ValueError("策略权重之和必须大于 0。")
    weights = {k: max(0.0, float(v)) / total for k, v in weights.items()}

    result = df.copy(deep=False)
    root_blend = float(np.clip(root_blend, 0.0, 1.0))
    raw_score = pd.Series(0.0, index=result.index, dtype="float64")
    contributions: dict[str, pd.Series] = {}
    for factor, weight in weights.items():
        if factor not in result.columns:
            continue
        global_value = pd.to_numeric(result[factor], errors="coerce").fillna(50.0)
        root_column = f"{factor}Root"
        if root_column in result.columns and factor != "ConfidenceFactor":
            root_value = pd.to_numeric(result[root_column], errors="coerce").fillna(global_value)
            blended_value = global_value * (1 - root_blend) + root_value * root_blend
        else:
            blended_value = global_value
        contribution = blended_value * weight
        contributions[factor] = contribution
        raw_score += contribution

    confidence = pd.to_numeric(result["DataQualityScore"], errors="coerce").fillna(0).clip(0, 100)
    confidence_multiplier = 0.70 + 0.30 * (confidence / 100)
    final_score = raw_score * confidence_multiplier

    result["Strategy"] = strategy
    result["RawOpportunityScore"] = raw_score.round(1)
    result["OpportunityScore"] = final_score.clip(0, 100).round(1)
    result["OpportunityLevel"] = pd.cut(
        result["OpportunityScore"],
        bins=[-np.inf, 45, 60, 75, np.inf],
        labels=["观察", "B级", "A级", "S级"],
        right=False,
    ).astype("string")

    for factor, contribution in contributions.items():
        result[f"Contribution_{factor}"] = contribution.round(2)

    market_median = result.groupby("MarketCode", observed=True)["Revenue"].transform("median")
    asin_median = result.groupby("MarketCode", observed=True)["ASINCount"].transform("median")
    high_market = result["Revenue"].ge(market_median).fillna(False)
    low_supply = result["ASINCount"].le(asin_median).fillna(False)
    conditions = [
        (high_market & low_supply).to_numpy(dtype=bool),
        (high_market & ~low_supply).to_numpy(dtype=bool),
        (~high_market & low_supply).to_numpy(dtype=bool),
    ]
    result["OpportunityZone"] = np.select(
        conditions,
        ["高规模低供给", "高规模高竞争", "小而精"],
        default="低优先级",
    )
    return result


def fetch_market_source(
    market: MarketConfig,
    *,
    timeout: tuple[float, float] = (10, 60),
) -> tuple[pd.DataFrame, dict[str, object]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; AmazonCategoryIntelligence/3.0)",
        "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = requests.get(market.source_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            raw, parse_metadata = parse_csv_payload(response.content)
            metadata = {
                **parse_metadata,
                "http_status": int(response.status_code),
                "content_type": response.headers.get("content-type", ""),
                "fetched_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "attempt": attempt + 1,
            }
            return raw, metadata
        except Exception as exc:
            last_error = exc
    raise DataLoadError(f"{market.name} 数据读取失败：{last_error}")


def load_market(market_code: str) -> tuple[pd.DataFrame, dict[str, object]]:
    market = MARKETS[market_code]
    raw, fetch_metadata = fetch_market_source(market)
    return prepare_market_data(raw, market, fetch_metadata=fetch_metadata)


def load_all_markets(
    market_codes: Iterable[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, object]], dict[str, str]]:
    frames: list[pd.DataFrame] = []
    diagnostics: dict[str, dict[str, object]] = {}
    errors: dict[str, str] = {}
    for code in market_codes or MARKETS.keys():
        try:
            frame, diag = load_market(code)
            frames.append(frame)
            diagnostics[code] = diag
        except Exception as exc:
            errors[code] = str(exc)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty:
        for categorical_column in (
            "MarketCode",
            "Market",
            "MarketFlag",
            "CurrencyCode",
            "CurrencySymbol",
            "SnapshotLabel",
            "RootRaw",
            "RootStandard",
            "DigitalRisk",
        ):
            combined[categorical_column] = combined[categorical_column].astype("category")
    return combined, diagnostics, errors


def compute_trend_metrics(history: pd.DataFrame) -> pd.DataFrame:
    """Compute time trends when two or more snapshots exist per market/category.

    The current public sources expose one snapshot each. This function is deliberately
    ready for future snapshots and returns an empty frame when no time series exists.
    """
    required = {"MarketCode", "CategoryKey", "SnapshotDate", "Revenue", "SearchVolume", "ASINCount"}
    if not required.issubset(history.columns):
        return pd.DataFrame()
    work = history.copy()
    work["SnapshotDate"] = pd.to_datetime(work["SnapshotDate"], errors="coerce")
    work = work.dropna(subset=["SnapshotDate"])
    if work.empty or not work.duplicated(["MarketCode", "CategoryKey"], keep=False).any():
        return pd.DataFrame()

    work = work.loc[work.duplicated(["MarketCode", "CategoryKey"], keep=False)].copy()
    groups: list[dict[str, object]] = []
    for (market_code, category_key), group in work.groupby(["MarketCode", "CategoryKey"], observed=True):
        group = group.sort_values("SnapshotDate").drop_duplicates("SnapshotDate", keep="last")
        if len(group) < 2:
            continue
        first = group.iloc[0]
        last = group.iloc[-1]

        def growth(column: str) -> float:
            start = float(first[column]) if pd.notna(first[column]) else np.nan
            end = float(last[column]) if pd.notna(last[column]) else np.nan
            if not np.isfinite(start) or start == 0 or not np.isfinite(end):
                return np.nan
            return (end / start - 1) * 100

        revenue_per_asin_first = (
            first["Revenue"] / first["ASINCount"] if pd.notna(first["ASINCount"]) and first["ASINCount"] > 0 else np.nan
        )
        revenue_per_asin_last = (
            last["Revenue"] / last["ASINCount"] if pd.notna(last["ASINCount"]) and last["ASINCount"] > 0 else np.nan
        )
        unit_growth = (
            (revenue_per_asin_last / revenue_per_asin_first - 1) * 100
            if pd.notna(revenue_per_asin_first) and revenue_per_asin_first != 0 and pd.notna(revenue_per_asin_last)
            else np.nan
        )
        search_growth = growth("SearchVolume")
        supply_growth = growth("ASINCount")
        opportunity_momentum = (
            (0 if pd.isna(search_growth) else search_growth)
            - (0 if pd.isna(supply_growth) else supply_growth)
            + (0 if pd.isna(unit_growth) else unit_growth)
        )
        groups.append(
            {
                "MarketCode": market_code,
                "CategoryKey": category_key,
                "Category": last.get("Category", ""),
                "SnapshotCount": len(group),
                "StartDate": first["SnapshotDate"],
                "EndDate": last["SnapshotDate"],
                "RevenueGrowthPct": growth("Revenue"),
                "SearchGrowthPct": search_growth,
                "SupplyGrowthPct": supply_growth,
                "RevenuePerASINGrowthPct": unit_growth,
                "OpportunityMomentum": opportunity_momentum,
            }
        )
    return pd.DataFrame(groups)


def explain_category(row: pd.Series) -> list[str]:
    """Generate transparent, rule-based diagnostic statements for one category."""
    notes: list[str] = []
    score = float(row.get("OpportunityScore", np.nan))
    market = float(row.get("MarketFactor", np.nan))
    access = float(row.get("AccessFactor", np.nan))
    demand = float(row.get("DemandFactor", np.nan))
    monetization = float(row.get("MonetizationFactor", np.nan))
    efficiency = float(row.get("EfficiencyFactor", np.nan))
    pain = float(row.get("PainFactor", np.nan))
    confidence = float(row.get("DataQualityScore", np.nan))

    if np.isfinite(score):
        notes.append(f"当前策略下机会分为 {score:.1f}，属于 {row.get('OpportunityLevel', '未分级')}。")
    if market >= 70:
        notes.append("市场规模位于本站头部，具备做大单品的基础盘。")
    elif market < 35:
        notes.append("市场规模偏小，更适合利基或高毛利打法，不适合单纯追求大体量。")
    if access >= 70:
        notes.append("单ASIN产出和搜索供需关系较好，竞争可进入性偏强。")
    elif access < 35:
        notes.append("供给拥挤或单位产出偏低，进入后可能需要更强差异化与广告预算。")
    if demand >= 70:
        notes.append("搜索、点击与浏览需求处于本站高位，但这只是当前结构强度，不代表时间序列增长。")
    if monetization >= 70:
        notes.append("价格与流量变现质量较好，理论上有更高的利润承载空间；实际利润仍需结合采购、物流和广告。")
    if efficiency < 35:
        notes.append("流量效率偏弱，需要检查关键词意图、类目污染或产品转化问题。")
    if pain >= 70:
        notes.append("低评分结构显示较强的产品改良空间，适合继续拆解差评和功能痛点。")
    if row.get("DigitalRisk") == "高":
        notes.append("该节点疑似数字商品、软件或订阅，不应直接进入实体商品选品榜。")
    if confidence < 60:
        notes.append(f"数据置信度仅 {confidence:.0f}，结论应谨慎使用；异常包括：{row.get('DataFlags', '未知')}。")
    return notes
