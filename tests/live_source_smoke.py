from __future__ import annotations

import sys

from amz_intelligence import apply_business_model
from amz_intelligence.config import MARKETS
from amz_intelligence.engine import apply_strategy_score, load_market


def validate_market(code: str) -> None:
    if code not in MARKETS:
        raise SystemExit(f"Unknown market code: {code}")
    frame, diagnostics = load_market(code)
    if len(frame) < 1_000:
        raise AssertionError(f"{code} returned only {len(frame)} records")
    required = {
        "CategoryID",
        "Category",
        "Revenue",
        "Sales",
        "ASINCount",
        "DataQualityScore",
        "EligibleCore",
        "MarketCode",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise AssertionError(f"{code} missing standardized columns: {sorted(missing)}")
    if diagnostics["prepared_rows"] != len(frame):
        raise AssertionError(f"{code} diagnostics row count mismatch")
    opportunity = apply_strategy_score(frame, "大单品")
    scored = apply_business_model(opportunity, profile="当前公司画像")
    score_columns = ["OpportunityScore", "FinalPriorityScore", "CompanyFitScore", "CrossBorderFriendliness"]
    for column in score_columns:
        if scored[column].isna().any():
            raise AssertionError(f"{code} {column} contains NA")
        if not scored[column].between(0, 100).all():
            raise AssertionError(f"{code} {column} outside 0-100")
    if scored["CNYRevenue"].isna().all():
        raise AssertionError(f"{code} CNY conversion is entirely missing")
    if not scored["EntryClass"].isin(["A", "B", "C", "D"]).all():
        raise AssertionError(f"{code} has invalid EntryClass")
    if not scored["DefaultBusinessEligible"].dtype == bool:
        raise AssertionError(f"{code} business eligibility is not boolean")
    print(
        "LIVE_SOURCE_SMOKE_OK",
        code,
        {
            "rows": len(frame),
            "eligible_physical": diagnostics["eligible_physical_rows"],
            "business_eligible": int(scored["DefaultBusinessEligible"].sum()),
            "entry_counts": scored["EntryClass"].value_counts().to_dict(),
        },
    )


if __name__ == "__main__":
    validate_market(sys.argv[1] if len(sys.argv) > 1 else "JP")
