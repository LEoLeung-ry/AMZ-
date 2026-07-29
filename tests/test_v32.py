from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence import MARKETS, enrich_entry_rules
from amz_intelligence.engine import apply_strategy_score, prepare_market_data
from amz_intelligence.model_v32 import (
    NEUTRAL_PROFILE,
    add_strategy_robustness,
    apply_decision_model_v32,
)


class V32DecisionModelTests(unittest.TestCase):
    def raw_rows(self) -> pd.DataFrame:
        categories = [
            ("啤酒", "Beer", "food-beverage"),
            ("大豆蛋白粉", "Soy Protein Powder", "food-beverage"),
            ("宠物跳蚤药水", "Flea & Tick Treatment", "pet-supplies"),
            ("充电宝", "Power Bank", "electronics"),
            ("日伞", "Parasol", "fashion"),
            ("垃圾袋", "Trash Bags", "home"),
            ("收纳箱", "Storage Boxes", "home"),
            ("男士电动剃须刀", "Electric Shaver", "beauty"),
        ]
        count = len(categories)
        return pd.DataFrame(
            {
                "分类ID": [str(20001 + index) for index in range(count)],
                "中文名称": [item[0] for item in categories],
                "分类名称": [item[1] for item in categories],
                "根类目": [item[2] for item in categories],
                "Node Path": [f"root > {item[2]} > {item[1]}" for item in categories],
                "近12个月销量": [100000 + index * 5000 for index in range(count)],
                "近12个月净销售额": [5000000000 - index * 200000000 for index in range(count)],
                "近12个月搜索量": [2000000 + index * 100000 for index in range(count)],
                "近12个月点击量": [500000 + index * 20000 for index in range(count)],
                "近12个月浏览量": [1000000 + index * 30000 for index in range(count)],
                "平均价格": [50000 - index * 1000 for index in range(count)],
                "ASIN数量": [200 + index * 10 for index in range(count)],
                "最受欢迎关键词": [item[1].casefold() for item in categories],
                "最受欢迎关键词值": [100000 - index * 3000 for index in range(count)],
                "价格转化率最大值": ["100-200"] * count,
                "4星及以上评分数量": [150] * count,
                "3星评分数量": [20] * count,
                "2星评分数量": [10] * count,
                "1星评分数量": [5] * count,
            }
        )

    def model(self) -> pd.DataFrame:
        prepared, _ = prepare_market_data(self.raw_rows(), MARKETS["JP"])
        enriched = enrich_entry_rules(prepared)
        opportunity = apply_strategy_score(enriched, "蓝海切入")
        neutral = apply_decision_model_v32(opportunity, profile=NEUTRAL_PROFILE)
        return add_strategy_robustness(enriched, neutral)

    def test_neutral_mode_disables_company_preference(self) -> None:
        scored = self.model()
        self.assertFalse(scored["CompanyFitApplied"].any())
        self.assertTrue(scored["CompanyFitScore"].eq(100).all())
        self.assertTrue(scored["ProfileInfluence"].str.contains("不使用历史聊天").all())
        expected = (scored["OpportunityScore"] * scored["EntryMultiplier"]).round(1)
        pd.testing.assert_series_equal(
            scored["FinalPriorityScore"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    def test_obvious_rule_warnings_stay_out_of_default_ranking(self) -> None:
        scored = self.model().set_index("Category")
        self.assertEqual(scored.loc["啤酒", "EntryClass"], "D")
        self.assertEqual(scored.loc["大豆蛋白粉", "EntryClass"], "C")
        self.assertEqual(scored.loc["宠物跳蚤药水", "EntryClass"], "D")
        self.assertFalse(bool(scored.loc["啤酒", "DefaultBusinessEligible"]))
        self.assertFalse(bool(scored.loc["大豆蛋白粉", "DefaultBusinessEligible"]))
        self.assertIn("不等于已确认可售", scored.loc["日伞", "RuleVerificationStatus"])

    def test_strategy_robustness_is_bounded_and_complete(self) -> None:
        scored = self.model()
        required = {
            "ConsensusPriorityScore",
            "ConservativePriorityScore",
            "OptimisticPriorityScore",
            "StrategyPriorityRange",
            "StrategyAgreementScore",
            "StrategySupportCount",
            "StrategyRobustnessLabel",
            "EvidenceCoverageScore",
            "SourceMetricAgreementScore",
        }
        self.assertTrue(required.issubset(scored.columns))
        self.assertTrue(scored["ConsensusPriorityScore"].between(0, 100).all())
        self.assertTrue(scored["ConservativePriorityScore"].between(0, 100).all())
        self.assertTrue(scored["OptimisticPriorityScore"].between(0, 100).all())
        self.assertTrue(scored["StrategyAgreementScore"].between(0, 100).all())
        self.assertTrue(scored["StrategySupportCount"].between(0, 5).all())
        self.assertTrue(scored["EvidenceCoverageScore"].between(0, 100).all())
        self.assertTrue(
            (scored["ConservativePriorityScore"] <= scored["ConsensusPriorityScore"]).all()
        )
        self.assertTrue(
            (scored["ConsensusPriorityScore"] <= scored["OptimisticPriorityScore"]).all()
        )


if __name__ == "__main__":
    unittest.main()
