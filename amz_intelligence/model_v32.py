from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from .business_rules import CAPABILITY_LABELS, apply_business_model
from .config import STRATEGY_PRESETS
from .engine import apply_strategy_score


NEUTRAL_PROFILE = "中性模式"
NEUTRAL_PROFILE_LABEL = "中性模式（不使用历史品类偏好）"

STRATEGY_COLUMN_NAMES: dict[str, str] = {
    "大单品": "MassProduct",
    "蓝海切入": "BlueOcean",
    "高客单精品": "Premium",
    "结构性需求机会": "DemandGap",
    "稳健优先": "Balanced",
}

ENTRY_INTERPRETATIONS: dict[str, str] = {
    "A": "A 未识别明显高门槛（不等于已确认可售）",
    "B": "B 识别到常规条件（需产品级复核）",
    "C": "C 高门槛规则预警（默认不进主榜）",
    "D": "D 强限制规则预警（默认排除）",
}


def _positive(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").gt(0).fillna(False)


def _has_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip().ne("")


def _relative_agreement(source: pd.Series, calculated: pd.Series) -> tuple[pd.Series, pd.Series]:
    source_num = pd.to_numeric(source, errors="coerce").astype("float64")
    calculated_num = pd.to_numeric(calculated, errors="coerce").astype("float64")
    available = source_num.notna() & calculated_num.notna() & calculated_num.abs().gt(1e-9)
    tolerance = np.maximum(calculated_num.abs() * 0.05, 0.5)
    agrees = available & source_num.sub(calculated_num).abs().le(tolerance)
    return available.astype(bool), agrees.astype(bool)


def add_observable_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    """Add transparent evidence coverage and source/calculation agreement.

    These fields do not change the market opportunity score. They only expose how much
    observable information is present and whether source ratios agree with recomputation.
    """

    result = frame.copy()
    index = result.index

    checks = pd.DataFrame(
        {
            "category_id": _has_text(result.get("CategoryID", pd.Series("", index=index))),
            "category_name": _has_text(result.get("Category", pd.Series("", index=index))),
            "search": _positive(result.get("SearchVolume", pd.Series(np.nan, index=index))),
            "clicks": _positive(result.get("Clicks", pd.Series(np.nan, index=index))),
            "views": _positive(result.get("Views", pd.Series(np.nan, index=index))),
            "keyword": _has_text(result.get("TopKeyword", pd.Series("", index=index))),
            "ratings": _positive(result.get("RatingBucketTotal", pd.Series(np.nan, index=index))),
            "node_path": _has_text(result.get("NodePath", pd.Series("", index=index))),
            "price_band": _has_text(result.get("PriceBand", pd.Series("", index=index))),
        },
        index=index,
    )
    result["EvidenceFieldCount"] = checks.sum(axis=1).astype("int64")
    result["EvidenceFieldTotal"] = int(checks.shape[1])
    result["EvidenceCoverageScore"] = (checks.mean(axis=1) * 100).round(1)

    calculated_asp = pd.to_numeric(result.get("Revenue"), errors="coerce") / pd.to_numeric(
        result.get("Sales"), errors="coerce"
    ).replace(0, np.nan)
    calculated_yield = (
        pd.to_numeric(result.get("Sales"), errors="coerce")
        / pd.to_numeric(result.get("Clicks"), errors="coerce").replace(0, np.nan)
        * 100
    )
    calculated_ctr = (
        pd.to_numeric(result.get("Clicks"), errors="coerce")
        / pd.to_numeric(result.get("Views"), errors="coerce").replace(0, np.nan)
        * 100
    )

    agreement_pairs = (
        _relative_agreement(result.get("ASPSource", pd.Series(np.nan, index=index)), calculated_asp),
        _relative_agreement(
            result.get("SearchConversionSource", pd.Series(np.nan, index=index)), calculated_yield
        ),
        _relative_agreement(result.get("CTRSource", pd.Series(np.nan, index=index)), calculated_ctr),
    )
    available_count = pd.Series(0, index=index, dtype="int64")
    agreement_count = pd.Series(0, index=index, dtype="int64")
    for available, agrees in agreement_pairs:
        available_count += available.astype("int64")
        agreement_count += agrees.astype("int64")
    result["SourceMetricCheckCount"] = available_count
    agreement_score = pd.Series(np.nan, index=index, dtype="float64")
    has_checks = available_count.gt(0)
    agreement_score.loc[has_checks] = (
        agreement_count.loc[has_checks] / available_count.loc[has_checks] * 100
    )
    result["SourceMetricAgreementScore"] = agreement_score.round(1)

    top_share = pd.to_numeric(result.get("TopKeywordShare"), errors="coerce")
    result["TopKeywordConcentrationPct"] = (top_share * 100).round(2)
    result["TopKeywordConcentrationPercentile"] = (
        top_share.groupby(result.get("MarketCode"), observed=True)
        .rank(method="average", pct=True)
        .mul(100)
        .round(1)
    )
    return result


def _recompute_decision_fields(result: pd.DataFrame) -> pd.DataFrame:
    conditions = [
        result["EntryClass"].eq("D"),
        result["EntryClass"].eq("C"),
        result["FinalPriorityScore"].ge(75),
        result["FinalPriorityScore"].ge(60),
        result["FinalPriorityScore"].ge(45),
    ]
    result["BusinessDecision"] = np.select(
        conditions,
        ["规则预警：强限制", "规则预警：高门槛", "优先研究", "进入验证", "有条件推进"],
        default="观察",
    )
    result["FinalPriorityLevel"] = pd.cut(
        result["FinalPriorityScore"],
        bins=[-np.inf, 20, 45, 60, 75, np.inf],
        labels=["低优先", "观察", "B级", "A级", "S级"],
        right=False,
    ).astype("string")
    return result


def apply_decision_model_v32(
    frame: pd.DataFrame,
    *,
    profile: str = NEUTRAL_PROFILE,
    capability_overrides: Mapping[str, bool] | None = None,
    fx_rates: Mapping[str, float] | None = None,
    fx_reference_date: str | None = None,
    fx_source: str | None = None,
) -> pd.DataFrame:
    """Apply rule warnings, optional company profile and currency conversion.

    Neutral mode deliberately disables historical category preference. Entry rules remain
    as risk warnings because the user explicitly asked that obvious restricted categories
    should not dominate the operating shortlist.
    """

    neutral = profile == NEUTRAL_PROFILE
    base_profile = "普通跨境卖家" if neutral else profile
    capabilities = (
        {key: False for key in CAPABILITY_LABELS}
        if neutral
        else dict(capability_overrides or {})
    )
    result = apply_business_model(
        frame,
        profile=base_profile,
        capability_overrides=capabilities,
        fx_rates=fx_rates,
        fx_reference_date=fx_reference_date,
        fx_source=fx_source,
    )

    result["CompanyFitApplied"] = not neutral
    result["ProfileInfluence"] = (
        "未启用公司画像；不使用历史聊天中的品类偏好"
        if neutral
        else "已启用人工公司画像；结果会受到人工设定影响"
    )
    result["RuleNature"] = "内部关键词/根类目风险预警"
    result["RuleVerificationStatus"] = np.where(
        result["BarrierRuleCode"].astype("string").eq("GENERAL"),
        "未命中高风险规则；不等于已确认可售",
        "未做具体产品和目标国法规核验",
    )
    result["EntryInterpretation"] = (
        result["EntryClass"].astype("string").map(ENTRY_INTERPRETATIONS).fillna("规则状态未知")
    )

    if neutral:
        result["SellerProfile"] = NEUTRAL_PROFILE
        result["CompanyFitScore"] = 100.0
        opportunity = pd.to_numeric(result["OpportunityScore"], errors="coerce").fillna(0).clip(0, 100)
        entry_multiplier = pd.to_numeric(result["EntryMultiplier"], errors="coerce").fillna(0).clip(0, 1)
        result["FinalPriorityScore"] = (opportunity * entry_multiplier).clip(0, 100).round(1)
        result["DefaultBusinessEligible"] = (
            result.get("EligiblePhysical", pd.Series(False, index=result.index))
            .fillna(False)
            .astype(bool)
            & result["EntryClass"].isin(["A", "B"])
        ).astype(bool)
        result = _recompute_decision_fields(result)

    return add_observable_evidence(result)


def add_strategy_robustness(
    factor_frame: pd.DataFrame,
    decision_frame: pd.DataFrame,
    *,
    root_blend: float = 0.25,
) -> pd.DataFrame:
    """Measure how much the ranking changes across the five standard strategies.

    This is a sensitivity analysis, not statistical confidence. It uses only the fields
    already present in the user's category datasets and does not inject new category
    preferences.
    """

    result = decision_frame.copy()
    priority_columns: list[str] = []
    opportunity_columns: list[str] = []
    fit_multiplier = np.where(
        result["CompanyFitApplied"].fillna(False).astype(bool),
        pd.to_numeric(result["CompanyFitScore"], errors="coerce").fillna(0).clip(0, 100) / 100,
        1.0,
    )
    entry_multiplier = pd.to_numeric(result["EntryMultiplier"], errors="coerce").fillna(0).clip(0, 1)

    for strategy, slug in STRATEGY_COLUMN_NAMES.items():
        strategy_scored = apply_strategy_score(factor_frame, strategy, root_blend=root_blend)
        opportunity_column = f"StrategyOpportunity_{slug}"
        priority_column = f"StrategyPriority_{slug}"
        opportunity = pd.to_numeric(strategy_scored["OpportunityScore"], errors="coerce").fillna(0)
        result[opportunity_column] = opportunity.round(1)
        result[priority_column] = (opportunity * entry_multiplier * fit_multiplier).clip(0, 100).round(1)
        opportunity_columns.append(opportunity_column)
        priority_columns.append(priority_column)

    opportunity_matrix = result[opportunity_columns].astype("float64")
    priority_matrix = result[priority_columns].astype("float64")
    result["StrategyOpportunityMedian"] = opportunity_matrix.median(axis=1).round(1)
    result["StrategyOpportunityMin"] = opportunity_matrix.min(axis=1).round(1)
    result["StrategyOpportunityMax"] = opportunity_matrix.max(axis=1).round(1)
    result["StrategyOpportunityRange"] = (
        result["StrategyOpportunityMax"] - result["StrategyOpportunityMin"]
    ).round(1)
    result["ConsensusPriorityScore"] = priority_matrix.median(axis=1).round(1)
    result["ConservativePriorityScore"] = priority_matrix.min(axis=1).round(1)
    result["OptimisticPriorityScore"] = priority_matrix.max(axis=1).round(1)
    result["StrategyPriorityRange"] = (
        result["OptimisticPriorityScore"] - result["ConservativePriorityScore"]
    ).round(1)
    result["StrategyAgreementScore"] = (100 - result["StrategyPriorityRange"]).clip(0, 100).round(1)

    support = pd.Series(0, index=result.index, dtype="int64")
    eligible = result["DefaultBusinessEligible"].fillna(False).astype(bool)
    for column in priority_columns:
        ranks = pd.Series(np.nan, index=result.index, dtype="float64")
        if eligible.any():
            ranks.loc[eligible] = (
                result.loc[eligible]
                .groupby("MarketCode", observed=True)[column]
                .rank(method="min", pct=True, ascending=False)
            )
        support += ranks.le(0.20).fillna(False).astype("int64")
    result["StrategySupportCount"] = support

    high = result["StrategySupportCount"].ge(4) & result["StrategyPriorityRange"].le(15)
    medium = result["StrategySupportCount"].ge(3) & result["StrategyPriorityRange"].le(25)
    result["StrategyRobustnessLabel"] = np.select(
        [high, medium],
        ["高共识", "中共识"],
        default="策略敏感",
    )
    return result
