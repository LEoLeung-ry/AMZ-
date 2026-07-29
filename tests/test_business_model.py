from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence import DEFAULT_FX_REFERENCE, MARKETS, apply_business_model
from amz_intelligence.engine import apply_strategy_score, prepare_market_data


class BusinessModelTests(unittest.TestCase):
    def raw_rows(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "分类ID": ["10001", "10002", "10003", "10004", "10005", "10006"],
                "中文名称": [
                    "啤酒",
                    "大豆蛋白粉",
                    "宠物跳蚤药水",
                    "充电宝",
                    "日伞",
                    "男士电动剃须刀",
                ],
                "分类名称": [
                    "Beer",
                    "Soy Protein Powder",
                    "Flea & Tick Treatment",
                    "Power Bank",
                    "Parasol",
                    "Electric Shaver",
                ],
                "根类目": [
                    "food-beverage",
                    "food-beverage",
                    "pet-supplies",
                    "electronics",
                    "fashion",
                    "beauty",
                ],
                "近12个月销量": [100000, 90000, 70000, 120000, 80000, 100000],
                "近12个月净销售额": [5000000000, 4000000000, 3000000000, 3500000000, 1800000000, 2600000000],
                "近12个月搜索量": [2000000, 1800000, 1500000, 2500000, 1300000, 2000000],
                "近12个月点击量": [500000, 450000, 300000, 600000, 300000, 500000],
                "近12个月浏览量": [1000000, 900000, 800000, 1200000, 700000, 1000000],
                "平均价格": [50000, 44444, 42857, 29167, 22500, 26000],
                "ASIN数量": [200, 180, 150, 300, 100, 200],
                "最受欢迎关键词": ["beer", "soy protein", "flea treatment", "power bank", "日傘", "shaver"],
                "最受欢迎关键词值": [100000, 90000, 80000, 120000, 70000, 110000],
                "4星及以上评分数量": [150, 140, 100, 220, 70, 150],
                "3星评分数量": [20, 20, 20, 30, 10, 20],
                "2星评分数量": [10, 10, 10, 20, 8, 10],
                "1星评分数量": [5, 5, 5, 10, 5, 5],
            }
        )

    def scored(self) -> pd.DataFrame:
        prepared, _ = prepare_market_data(self.raw_rows(), MARKETS["JP"])
        opportunity = apply_strategy_score(prepared, "蓝海切入")
        return apply_business_model(opportunity, profile="当前公司画像")

    def test_regulated_categories_are_gated(self) -> None:
        scored = self.scored().set_index("Category")
        self.assertEqual(scored.loc["啤酒", "EntryClass"], "D")
        self.assertEqual(scored.loc["大豆蛋白粉", "EntryClass"], "C")
        self.assertEqual(scored.loc["宠物跳蚤药水", "EntryClass"], "D")
        self.assertFalse(bool(scored.loc["啤酒", "DefaultBusinessEligible"]))
        self.assertFalse(bool(scored.loc["大豆蛋白粉", "DefaultBusinessEligible"]))
        self.assertEqual(float(scored.loc["啤酒", "FinalPriorityScore"]), 0.0)

    def test_target_categories_remain_actionable(self) -> None:
        scored = self.scored().set_index("Category")
        self.assertEqual(scored.loc["充电宝", "EntryClass"], "B")
        self.assertEqual(scored.loc["日伞", "EntryClass"], "A")
        self.assertEqual(scored.loc["男士电动剃须刀", "EntryClass"], "B")
        self.assertTrue(bool(scored.loc["日伞", "DefaultBusinessEligible"]))
        self.assertGreater(float(scored.loc["充电宝", "CompanyFitScore"]), 75)
        self.assertGreater(float(scored.loc["男士电动剃须刀", "CompanyFitScore"]), 75)

    def test_cny_conversion_is_present(self) -> None:
        scored = self.scored()
        row = scored.loc[scored["Category"].eq("日伞")].iloc[0]
        expected = row["Revenue"] * DEFAULT_FX_REFERENCE.cny_per_currency["JPY"]
        self.assertAlmostEqual(float(row["CNYRevenue"]), float(expected), places=4)
        self.assertGreater(float(row["CNYRevenuePerASIN"]), 0)

    def test_capability_only_promotes_one_gate_level(self) -> None:
        prepared, _ = prepare_market_data(self.raw_rows(), MARKETS["JP"])
        opportunity = apply_strategy_score(prepared, "稳健优先")
        promoted = apply_business_model(
            opportunity,
            profile="当前公司画像",
            capability_overrides={"alcohol_license": True},
        ).set_index("Category")
        self.assertEqual(promoted.loc["啤酒", "EntryClass"], "C")


if __name__ == "__main__":
    unittest.main()
