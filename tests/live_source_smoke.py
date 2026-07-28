from __future__ import annotations

import sys

from amz_intelligence.config import MARKETS
from amz_intelligence.engine import apply_strategy_score, load_market


def validate_market(code: str) -> None:
    if code not in MARKETS:
        raise SystemExit(f"Unknown market code: {code}")
    frame, diagnostics = load_market(code)
    if len(frame) < 1_000:
        raise AssertionError(f"{code} returned only {len(frame)} records")
    required = {
        "CategoryID", "Category", "Revenue", "Sales", "ASINCount",
        "DataQualityScore", "EligibleCore", "MarketCode",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise AssertionError(f"{code} missing standardized columns: {sorted(missing)}")
    if diagnostics["prepared_rows"] != len(frame):
        raise AssertionError(f"{code} diagnostics row count mismatch")
    scored = apply_strategy_score(frame, "大单品")
    if scored["OpportunityScore"].isna().any():
        raise AssertionError(f"{code} OpportunityScore contains NA")
    if not scored["OpportunityScore"].between(0, 100).all():
        raise AssertionError(f"{code} OpportunityScore outside 0-100")
    print(
        "LIVE_SOURCE_SMOKE_OK",
        code,
        {"rows": len(frame), "eligible_physical": diagnostics["eligible_physical_rows"]},
    )


if __name__ == "__main__":
    validate_market(sys.argv[1] if len(sys.argv) > 1 else "JP")
