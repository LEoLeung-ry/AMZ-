from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence import MARKETS, enrich_entry_rules
from amz_intelligence.engine import prepare_market_data


class FinalEntryRefinementTests(unittest.TestCase):
    def test_final_refinements_are_classified(self) -> None:
        categories = [
            ("安全套", "Condoms", "health", "C"),
            ("消毒液", "Disinfectants", "health", "C"),
            ("戒烟", "Smoking Cessation", "health", "D"),
            ("助消化", "Verdauungshilfen", "health", "C"),
            ("热泵烘干机", "Wärmepumpentrockner", "home", "B"),
            ("健身自行车", "Fitnessbikes", "sports", "B"),
            ("控制器", "Controllers", "video-games", "B"),
        ]
        count = len(categories)
        raw = pd.DataFrame(
            {
                "分类ID": [str(40001 + index) for index in range(count)],
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
        classified = enrich_entry_rules(prepared).set_index("Category")
        for category, _, _, expected_class in categories:
            self.assertEqual(classified.loc[category, "BaseEntryClass"], expected_class, category)


if __name__ == "__main__":
    unittest.main()
