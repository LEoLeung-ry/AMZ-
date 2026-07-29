from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence import DEFAULT_FX_REFERENCE, MARKETS, apply_business_model
from amz_intelligence.engine import apply_strategy_score, prepare_market_data


class BusinessModelTests(unittest.TestCase):
    def raw_rows(self) -> pd.DataFrame:
        categories = [
            ("啤酒", "Beer", "food-beverage"),
            ("大豆蛋白粉", "Soy Protein Powder", "food-beverage"),
            ("宠物跳蚤药水", "Flea & Tick Treatment", "pet-supplies"),
            ("充电宝", "Power Bank", "electronics"),
            ("日伞", "Parasol", "fashion"),
            ("男士电动剃须刀", "Electric Shaver", "beauty"),
            ("呼吸机配件", "CPAP Accessories", "health"),
            ("可重复使用的呼吸器", "Reusable Respirators", "diy"),
            ("蛋白棒", "Protein Bars", "food-beverage"),
            ("胶原蛋白", "Kollagen", "health"),
            ("烟雾探测器", "Smoke Detectors", "diy"),
            ("塔扇", "Tower Fans", "home"),
            ("全自动咖啡机", "Kaffeevollautomaten", "kitchen"),
            ("监控摄像头", "Überwachungskameras", "hi"),
        ]
        count = len(categories)
        return pd.DataFrame(
            {
                "分类ID": [str(10001 + index) for index in range(count)],
                "中文名称": [item[0] for item in categories],
                "分类名称": [item[1] for item in categories],
                "根类目": [item[2] for item in categories],
                "近12个月销量": [100000 + index * 1000 for index in range(count)],
                "近12个月净销售额": [5000000000 - index * 100000000 for index in range(count)],
                "近12个月搜索量": [2000000 + index * 10000 for index in range(count)],
                "近12个月点击量": [500000 + index * 1000 for index in range(count)],
                "近12个月浏览量": [1000000 + index * 2000 for index in range(count)],
                "平均价格": [50000 - index * 500 for index in range(count)],
                "ASIN数量": [200 + index * 5 for index in range(count)],
                "最受欢迎关键词": [item[1].casefold() for item in categories],
                "最受欢迎关键词值": [100000 - index * 1000 for index in range(count)],
                "4星及以上评分数量": [150] * count,
                "3星评分数量": [20] * count,
                "2星评分数量": [10] * count,
                "1星评分数量": [5] * count,
            }
        )

    def scored(self) -> pd.DataFrame:
        prepared, _ = prepare_market_data(self.raw_rows(), MARKETS["JP"])
        opportunity = apply_strategy_score(prepared, "蓝海切入")
        return apply_business_model(opportunity, profile="当前公司画像")

    def test_regulated_categories_are_gated(self) -> None:
        scored = self.scored().set_index("Category")
        expected = {
            "啤酒": "D",
            "大豆蛋白粉": "C",
            "宠物跳蚤药水": "D",
            "呼吸机配件": "C",
            "可重复使用的呼吸器": "C",
            "蛋白棒": "C",
            "胶原蛋白": "C",
        }
        for category, entry_class in expected.items():
            self.assertEqual(scored.loc[category, "EntryClass"], entry_class, category)
            self.assertFalse(bool(scored.loc[category, "DefaultBusinessEligible"]), category)
        self.assertEqual(float(scored.loc["啤酒", "FinalPriorityScore"]), 0.0)

    def test_target_and_conditional_categories(self) -> None:
        scored = self.scored().set_index("Category")
        expected = {
            "充电宝": "B",
            "日伞": "A",
            "男士电动剃须刀": "B",
            "烟雾探测器": "B",
            "塔扇": "B",
            "全自动咖啡机": "B",
            "监控摄像头": "B",
        }
        for category, entry_class in expected.items():
            self.assertEqual(scored.loc[category, "EntryClass"], entry_class, category)
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
