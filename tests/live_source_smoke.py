from __future__ import annotations

from amz_intelligence.config import MARKETS
from amz_intelligence.engine import apply_strategy_score, load_all_markets


def main() -> None:
    frame, diagnostics, errors = load_all_markets(tuple(MARKETS))
    if errors:
        raise AssertionError(f"Live source errors: {errors}")
    expected = set(MARKETS)
    actual = set(frame["MarketCode"].astype(str).unique())
    if actual != expected:
        raise AssertionError(f"Expected markets {expected}, got {actual}")
    required = {
        "CategoryID", "Category", "Revenue", "Sales", "ASINCount",
        "DataQualityScore", "EligibleCore", "MarketCode",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise AssertionError(f"Missing standardized columns: {sorted(missing)}")
    for code in expected:
        count = int(frame["MarketCode"].astype(str).eq(code).sum())
        if count < 1_000:
            raise AssertionError(f"{code} returned only {count} records")
        if diagnostics[code]["prepared_rows"] != count:
            raise AssertionError(f"{code} diagnostics row count mismatch")
    scored = apply_strategy_score(frame, "大单品")
    if scored["OpportunityScore"].isna().any():
        raise AssertionError("OpportunityScore contains NA")
    if not scored["OpportunityScore"].between(0, 100).all():
        raise AssertionError("OpportunityScore outside 0-100")
    print("LIVE_SOURCE_SMOKE_OK", {code: diagnostics[code]["prepared_rows"] for code in sorted(expected)})


if __name__ == "__main__":
    main()
