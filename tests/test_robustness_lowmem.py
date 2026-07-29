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
from amz_intelligence.robustness_lowmem import add_strategy_robustness_lowmem


class LowMemoryRobustnessTests(unittest.TestCase):
    def test_low_memory_aggregates_match_original(self) -> None:
        raw = pd.DataFrame(
            {
                "分类ID": [str(90000 + index) for index in range(12)],
                "中文名称": [
                    "日伞",
                    "垃圾袋",
                    "收纳箱",
                    "充电宝",
                    "电动剃须刀",
                    "塔扇",
                    "啤酒",
                    "蛋白粉",
                    "宠物跳蚤药",
                    "纸巾",
                    "雨伞",
                    "咖啡机",
                ],
                "分类名称": [
                    "Parasol",
                    "Trash Bags",
                    "Storage Boxes",
                    "Power Bank",
                    "Electric Shaver",
                    "Tower Fan",
                    "Beer",
                    "Protein Powder",
                    "Flea Treatment",
                    "Tissues",
                    "Umbrella",
                    "Coffee Machine",
                ],
                "根类目": [
                    "fashion",
                    "home",
                    "home",
                    "electronics",
                    "beauty",
                    "home",
                    "food-beverage",
                    "food-beverage",
                    "pet-supplies",
                    "home",
                    "fashion",
                    "home",
                ],
                "近12个月销量": [80000 + index * 7000 for index in range(12)],
                "近12个月净销售额": [1500000000 + index * 210000000 for index in range(12)],
                "近12个月搜索量": [1000000 + index * 130000 for index in range(12)],
                "近12个月点击量": [250000 + index * 25000 for index in range(12)],
                "近12个月浏览量": [600000 + index * 50000 for index in range(12)],
                "平均价格": [18000 + index * 1200 for index in range(12)],
                "ASIN数量": [100 + index * 20 for index in range(12)],
                "最受欢迎关键词": [f"keyword {index}" for index in range(12)],
                "最受欢迎关键词值": [50000 + index * 4000 for index in range(12)],
                "4星及以上评分数量": [80 + index * 5 for index in range(12)],
                "3星评分数量": [15] * 12,
                "2星评分数量": [8] * 12,
                "1星评分数量": [4] * 12,
            }
        )
        prepared, _ = prepare_market_data(raw, MARKETS["JP"])
        enriched = enrich_entry_rules(prepared)
        opportunity = apply_strategy_score(enriched, "稳健优先")
        decision = apply_decision_model_v32(opportunity, profile=NEUTRAL_PROFILE)

        original = add_strategy_robustness(enriched, decision)
        optimized = add_strategy_robustness_lowmem(enriched, decision)

        columns = [
            "StrategyOpportunityMedian",
            "StrategyOpportunityMin",
            "StrategyOpportunityMax",
            "StrategyOpportunityRange",
            "ConsensusPriorityScore",
            "ConservativePriorityScore",
            "OptimisticPriorityScore",
            "StrategyPriorityRange",
            "StrategyAgreementScore",
            "StrategySupportCount",
            "StrategyRobustnessLabel",
        ]
        for column in columns:
            pd.testing.assert_series_equal(
                optimized[column].reset_index(drop=True),
                original[column].reset_index(drop=True),
                check_names=False,
                check_dtype=False,
            )


if __name__ == "__main__":
    unittest.main()
