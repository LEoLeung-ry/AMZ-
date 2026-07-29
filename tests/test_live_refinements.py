from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence import MARKETS, enrich_entry_rules
from amz_intelligence.engine import prepare_market_data


class LiveRuleRefinementTests(unittest.TestCase):
    def test_refined_live_categories_are_flagged(self) -> None:
        categories = [
            ("产前维生素", "Prenatal Vitamins", "health", "C"),
            ("乳清蛋白", "Molkenproteine", "health", "C"),
            ("地毯清洗机", "Carpet Cleaning Machines", "home", "B"),
            ("立式吸尘器", "Upright Vacuums", "home", "B"),
            ("洗碗机60cm", "Geschirrspüler 60cm", "home", "B"),
            ("机器人割草机", "Mähroboter", "garden", "B"),
            ("漱口水", "Mouthwash", "beauty", "B"),
            ("口腔护理用品", "Oral Care Supplies", "health", "B"),
            ("磁性/钛/锗配件", "磁気・チタン・ゲルマニウムアクセサリー", "health", "B"),
        ]
        count = len(categories)
        raw = pd.DataFrame(
            {
                "分类ID": [str(30001 + index) for index in range(count)],
                "中文名称": [item[0] for item in categories],
                "分类名称": [item[1] for item in categories],
                "根类目": [item[2] for item in categories],
                "近12个月销量": [100000] * count,
                "近12个月净销售额": [3000000000] * count,
                "近12个月搜索量": [2000000] * count,
                "近12个月点击量": [500000] * count,
                "近12个月浏览量": [1000000] * count,
                "平均价格": [30000] * count,
                "ASIN数量": [200] * count,
                "最受欢迎关键词": [item[1].casefold() for item in categories],
                "最受欢迎关键词值": [100000] * count,
                "4星及以上评分数量": [150] * count,
                "3星评分数量": [20] * count,
                "2星评分数量": [10] * count,
                "1星评分数量": [5] * count,
            }
        )
        prepared, _ = prepare_market_data(raw, MARKETS["JP"])
        scored = enrich_entry_rules(prepared).set_index("Category")
        for category, _, _, expected_class in categories:
            self.assertEqual(scored.loc[category, "BaseEntryClass"], expected_class, category)


if __name__ == "__main__":
    unittest.main()
