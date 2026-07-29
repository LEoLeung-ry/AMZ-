from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from .config import STRATEGY_PRESETS


STRATEGY_COLUMN_NAMES: dict[str, str] = {
    "大单品": "MassProduct",
    "蓝海切入": "BlueOcean",
    "高客单精品": "Premium",
    "结构性需求机会": "DemandGap",
    "稳健优先": "Balanced",
}


def _numeric_array(
    frame: pd.DataFrame,
    column: str,
    *,
    default: float,
) -> np.ndarray:
    if column not in frame.columns:
        return np.full(len(frame), default, dtype="float64")
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype="float64", na_value=np.nan)
    return np.where(np.isfinite(values), values, default)


def _opportunity_array(
    frame: pd.DataFrame,
    strategy: str,
    *,
    root_blend: float,
) -> np.ndarray:
    weights: Mapping[str, float] = STRATEGY_PRESETS[strategy]
    total = sum(max(0.0, float(value)) for value in weights.values())
    normalized = {
        factor: max(0.0, float(weight)) / total
        for factor, weight in weights.items()
        if float(weight) > 0
    }

    blend = float(np.clip(root_blend, 0.0, 1.0))
    raw = np.zeros(len(frame), dtype="float64")
    for factor, weight in normalized.items():
        global_value = _numeric_array(frame, factor, default=50.0)
        root_column = f"{factor}Root"
        if factor != "ConfidenceFactor" and root_column in frame.columns:
            root_value = _numeric_array(frame, root_column, default=np.nan)
            root_value = np.where(np.isfinite(root_value), root_value, global_value)
            value = global_value * (1.0 - blend) + root_value * blend
        else:
            value = global_value
        raw += value * weight

    confidence = np.clip(_numeric_array(frame, "DataQualityScore", default=0.0), 0.0, 100.0)
    confidence_multiplier = 0.70 + 0.30 * (confidence / 100.0)
    return np.clip(raw * confidence_multiplier, 0.0, 100.0)


def add_strategy_robustness_lowmem(
    factor_frame: pd.DataFrame,
    decision_frame: pd.DataFrame,
    *,
    root_blend: float = 0.25,
) -> pd.DataFrame:
    """Compute five-strategy sensitivity without creating five full DataFrame copies.

    The original implementation repeatedly called ``apply_strategy_score`` and retained
    large temporary DataFrames. On Streamlit Community Cloud this can create a high peak
    memory footprint. This implementation calculates only the numeric arrays required for
    the robustness aggregates, while preserving the same public aggregate fields.
    """

    result = decision_frame.copy(deep=False)
    strategy_names = list(STRATEGY_COLUMN_NAMES)
    row_count = len(result)
    strategy_count = len(strategy_names)

    opportunity_matrix = np.empty((row_count, strategy_count), dtype="float64")
    priority_matrix = np.empty((row_count, strategy_count), dtype="float64")

    entry_multiplier = np.clip(
        _numeric_array(result, "EntryMultiplier", default=0.0),
        0.0,
        1.0,
    )
    fit_applied = (
        result.get("CompanyFitApplied", pd.Series(False, index=result.index))
        .fillna(False)
        .astype(bool)
        .to_numpy()
    )
    fit_score = np.clip(_numeric_array(result, "CompanyFitScore", default=100.0), 0.0, 100.0)
    fit_multiplier = np.where(fit_applied, fit_score / 100.0, 1.0)

    for position, strategy in enumerate(strategy_names):
        opportunity = _opportunity_array(factor_frame, strategy, root_blend=root_blend)
        priority = np.clip(opportunity * entry_multiplier * fit_multiplier, 0.0, 100.0)
        opportunity_matrix[:, position] = opportunity
        priority_matrix[:, position] = priority

    result["StrategyOpportunityMedian"] = np.median(opportunity_matrix, axis=1).round(1)
    result["StrategyOpportunityMin"] = np.min(opportunity_matrix, axis=1).round(1)
    result["StrategyOpportunityMax"] = np.max(opportunity_matrix, axis=1).round(1)
    result["StrategyOpportunityRange"] = (
        result["StrategyOpportunityMax"] - result["StrategyOpportunityMin"]
    ).round(1)

    result["ConsensusPriorityScore"] = np.median(priority_matrix, axis=1).round(1)
    result["ConservativePriorityScore"] = np.min(priority_matrix, axis=1).round(1)
    result["OptimisticPriorityScore"] = np.max(priority_matrix, axis=1).round(1)
    result["StrategyPriorityRange"] = (
        result["OptimisticPriorityScore"] - result["ConservativePriorityScore"]
    ).round(1)
    result["StrategyAgreementScore"] = (
        100.0 - result["StrategyPriorityRange"]
    ).clip(0.0, 100.0).round(1)

    eligible = (
        result.get("DefaultBusinessEligible", pd.Series(False, index=result.index))
        .fillna(False)
        .astype(bool)
    )
    support = pd.Series(0, index=result.index, dtype="int64")
    market_codes = result.get("MarketCode", pd.Series("", index=result.index))
    if eligible.any():
        eligible_index = result.index[eligible]
        eligible_markets = market_codes.loc[eligible_index]
        for position in range(strategy_count):
            values = pd.Series(priority_matrix[:, position], index=result.index)
            ranks = (
                values.loc[eligible_index]
                .groupby(eligible_markets, observed=True)
                .rank(method="min", pct=True, ascending=False)
            )
            support.loc[eligible_index] += ranks.le(0.20).fillna(False).astype("int64")
    result["StrategySupportCount"] = support

    high = result["StrategySupportCount"].ge(4) & result["StrategyPriorityRange"].le(15)
    medium = result["StrategySupportCount"].ge(3) & result["StrategyPriorityRange"].le(25)
    result["StrategyRobustnessLabel"] = np.select(
        [high, medium],
        ["高共识", "中共识"],
        default="策略敏感",
    )
    return result
