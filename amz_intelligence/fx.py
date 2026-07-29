from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FxReference:
    reference_date: str
    source_name: str
    source_note: str
    cny_per_currency: Mapping[str, float]


# ECB 2026-07-27 euro reference rates, cross-calculated through EUR/CNY.
# These are comparison rates, not settlement quotes. The UI lets the operator override them.
DEFAULT_FX_REFERENCE = FxReference(
    reference_date="2026-07-27",
    source_name="ECB euro reference rates",
    source_note="以 EUR/CNY 为桥接汇率折算，仅用于跨站比较；经营预算可在侧边栏改成公司固定汇率。",
    cny_per_currency={
        "CNY": 1.0,
        "JPY": 0.04134731984761496,
        "USD": 6.766090086925981,
        "EUR": 7.7059,
        "GBP": 9.01021935363173,
    },
)


def normalize_fx_rates(rates: Mapping[str, float] | None = None) -> dict[str, float]:
    merged = dict(DEFAULT_FX_REFERENCE.cny_per_currency)
    for currency, value in (rates or {}).items():
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number) and number > 0:
            merged[str(currency).upper()] = number
    return merged


def apply_cny_conversion(
    frame: pd.DataFrame,
    rates: Mapping[str, float] | None = None,
    *,
    reference_date: str | None = None,
    source_name: str | None = None,
) -> pd.DataFrame:
    result = frame.copy(deep=False)
    normalized = normalize_fx_rates(rates)
    currencies = result.get("CurrencyCode", pd.Series("", index=result.index)).astype("string")
    fx_rate = currencies.map(normalized).astype("float64")
    result["FXRateCNY"] = fx_rate
    result["FXReferenceDate"] = reference_date or DEFAULT_FX_REFERENCE.reference_date
    result["FXSource"] = source_name or DEFAULT_FX_REFERENCE.source_name

    conversions = {
        "Revenue": "CNYRevenue",
        "ASP": "CNYASP",
        "RevenuePerASIN": "CNYRevenuePerASIN",
        "RevenuePerSearch": "CNYRevenuePerSearch",
        "RevenuePerClick": "CNYRevenuePerClick",
    }
    for source, target in conversions.items():
        values = pd.to_numeric(result.get(source), errors="coerce").astype("float64")
        result[target] = (values * fx_rate).replace([np.inf, -np.inf], np.nan)
    return result
