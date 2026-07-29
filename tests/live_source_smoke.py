from __future__ import annotations

import sys

from amz_intelligence import enrich_entry_rules
from amz_intelligence.config import MARKETS
from amz_intelligence.engine import apply_strategy_score, load_market
from amz_intelligence.model_v32 import (
    NEUTRAL_PROFILE,
    add_strategy_robustness,
    apply_decision_model_v32,
)


def validate_market(code: str) -> None:
    if code not in MARKETS:
        raise SystemExit(f"Unknown market code: {code}")
    frame, diagnostics = load_market(code)
    if len(frame) < 1_000:
        raise AssertionError(f"{code} returned only {len(frame)} records")
    required = {
        "CategoryID", "Category", "Revenue", "Sales", "ASINCount", "DataQualityScore",
        "EligibleCore", "MarketCode",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise AssertionError(f"{code} missing standardized columns: {sorted(missing)}")
    if diagnostics["prepared_rows"] != len(frame):
        raise AssertionError(f"{code} diagnostics row count mismatch")

    enriched = enrich_entry_rules(frame)
    opportunity = apply_strategy_score(enriched, "大单品")
    decision = apply_decision_model_v32(opportunity, profile=NEUTRAL_PROFILE)
    scored = add_strategy_robustness(enriched, decision)

    score_columns = [
        "OpportunityScore",
        "FinalPriorityScore",
        "ConsensusPriorityScore",
        "ConservativePriorityScore",
        "StrategyAgreementScore",
        "EvidenceCoverageScore",
        "CrossBorderFriendliness",
    ]
    for column in score_columns:
        if scored[column].isna().any():
            raise AssertionError(f"{code} {column} contains NA")
        if not scored[column].between(0, 100).all():
            raise AssertionError(f"{code} {column} outside 0-100")
    if scored["CNYRevenue"].isna().all():
        raise AssertionError(f"{code} CNY conversion is entirely missing")
    if not scored["EntryClass"].isin(["A", "B", "C", "D"]).all():
        raise AssertionError(f"{code} has invalid EntryClass")
    if scored["CompanyFitApplied"].any():
        raise AssertionError(f"{code} neutral mode unexpectedly applied company fit")
    if not scored["CompanyFitScore"].eq(100).all():
        raise AssertionError(f"{code} neutral mode company multiplier is not neutral")
    if not scored["DefaultBusinessEligible"].dtype == bool:
        raise AssertionError(f"{code} business eligibility is not boolean")
    if scored.loc[scored["DefaultBusinessEligible"], "EntryClass"].isin(["C", "D"]).any():
        raise AssertionError(f"{code} C/D category leaked into the default business ranking")
    if not scored["StrategySupportCount"].between(0, 5).all():
        raise AssertionError(f"{code} strategy support outside 0-5")

    text = scored["BusinessText"].astype("string").fillna("")
    accessories = text.str.contains(
        r"glass|mug|cup|rack|holder|coaster|opener|stopper|decanter|corkscrew|case|comb|brush|trap|tool|book|"
        r"storage|container|bowl|mat|scoop|feeder|dispenser|shaker|bottle|envelope|wallet|spreader|applicator|"
        r"collagen mask|collagen cream|collagen serum|胶原面膜|胶原面霜|コラーゲンマスク",
        regex=True,
        case=False,
        na=False,
    )
    known_regulated = text.str.contains(
        r"protein powder|蛋白粉|プロテイン|proteinpulver|eiweißpulver|イソフラボン|瓜氨酸|シトルリン|"
        r"protein bars?|energy bars?|nutrition bars?|蛋白棒|能量棒|プロテインバー|"
        r"collagen|kollagen|胶原蛋白|コラーゲン|"
        r"electrolyte replacements?|omega[- ]?3|lactobacillus|probiotics?|diet shakes?|meal replacement shakes?|"
        r"电解质替代|欧米茄3|乳酸菌|益生菌|减肥奶昔|代餐奶昔|放松剂|焦虑缓解|"
        r"cat food|dog food|pet food|animal feed|猫粮|狗粮|キャットフード|ドッグフード|katzenfutter|hundefutter|trockenfutter|"
        r"gift cards?|gift certificates?|礼品卡|ギフトカード|geschenkkarte|gutschein|"
        r"\bbeer\b|啤酒|ビール|\bbier\b|"
        r"flea.*(?:treat|control|drop|medicine|collar|spray)|跳蚤药|ノミ.*(?:薬|駆除)|floh.*mittel|"
        r"育毛|発毛|生发|hair growth|hair regrowth|hair tonic|"
        r"\bcpap\b|\bbipap\b|sleep apnea|呼吸机配件|schlafapnoe|"
        r"reusable respirator|respirator mask|防毒面具|呼吸防护器|atemschutzmaske|atemschutzgerät",
        regex=True,
        case=False,
        na=False,
    ) & ~accessories
    leaked = scored.loc[known_regulated & scored["DefaultBusinessEligible"]]
    if not leaked.empty:
        examples = leaked[["Category", "CategoryLocal", "RegulatoryFamily", "EntryClass"]].head(10).to_dict("records")
        raise AssertionError(f"{code} known regulated categories leaked into main ranking: {examples}")

    known_conditional = text.str.contains(
        r"\bems\b|electrical muscle stimulation|muscle stimulator|ab belt|腹肌贴|腹筋ベルト|"
        r"fertili[sz]er|草坪肥|園芸肥料|rasendünger|pflanzendünger|"
        r"moth repellent|moth killer|moth trap|防蛾|飞蛾防治|mottenmittel|mottenfalle|"
        r"smoke detector|smoke alarm|烟雾探测器|rauchmelder",
        regex=True,
        case=False,
        na=False,
    ) & ~accessories
    conditional_leaked = scored.loc[known_conditional & scored["EntryClass"].eq("A")]
    if not conditional_leaked.empty:
        examples = conditional_leaked[["Category", "CategoryLocal", "RegulatoryFamily", "EntryClass"]].head(10).to_dict("records")
        raise AssertionError(f"{code} known conditional categories remained A: {examples}")

    top = scored.loc[scored["DefaultBusinessEligible"]].nlargest(5, "ConsensusPriorityScore")
    print(
        "LIVE_TOP5_V32",
        code,
        top[
            [
                "Category",
                "CategoryLocal",
                "EntryClass",
                "ConsensusPriorityScore",
                "ConservativePriorityScore",
                "StrategyAgreementScore",
            ]
        ].to_dict("records"),
    )
    print(
        "LIVE_SOURCE_SMOKE_V32_OK",
        code,
        {
            "rows": len(frame),
            "eligible_physical": diagnostics["eligible_physical_rows"],
            "business_eligible": int(scored["DefaultBusinessEligible"].sum()),
            "entry_counts": scored["EntryClass"].value_counts().to_dict(),
            "high_consensus": int(scored["StrategyRobustnessLabel"].eq("高共识").sum()),
        },
    )


if __name__ == "__main__":
    validate_market(sys.argv[1] if len(sys.argv) > 1 else "JP")
