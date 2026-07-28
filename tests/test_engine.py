from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from amz_intelligence.config import MARKETS
from amz_intelligence.engine import (
    apply_strategy_score,
    compute_trend_metrics,
    parse_csv_payload,
    prepare_market_data,
)


class EngineRegressionTests(unittest.TestCase):
    def synthetic_raw(self) -> pd.DataFrame:
        # Deliberately shuffled columns and nullable values.
        return pd.DataFrame(
            {
                "跳转链接": [
                    "https://www.amazon.co.uk/gp/bestsellers/electronics/30117754031",
                    "https://www.amazon.co.uk/gp/bestsellers/kitchen/16416191",
                    "",
                ],
                "ASIN数量": ["1,250", "80", pd.NA],
                "近12个月净销售额": ["£12,500,000", "£2,000,000", "-50"],
                "中文名称": ["无 SIM 卡手机", "收纳盒", pd.NA],
                "分类名称": ["SIM-Free Phones", "Storage Boxes", pd.NA],
                "分类ID": ["3.0117754031E10", "1.6416191E7", pd.NA],
                "根类目": ["electronics", "kitchen", "software"],
                "近12个月销量": ["100,000", "20,000", pd.NA],
                "近12个月搜索量": ["4,000,000", "800,000", "1"],
                "近12个月点击量": ["200,000", "50,000", pd.NA],
                "近12个月浏览量": ["800,000", "150,000", pd.NA],
                "搜索转化率": ["50%", "40", pd.NA],
                "点击率": ["25", "33.33%", pd.NA],
                "平均价格": ["125", "100", pd.NA],
                "最受欢迎关键词": ["iphone", "storage box", "software"],
                "最受欢迎关键词值": ["500,000", "30,000", "1"],
                "4星及以上评分数量": ["800", "50", "0"],
                "3星评分数量": ["100", "20", "0"],
                "2星评分数量": ["30", "5", "0"],
                "1星评分数量": ["20", "5", "0"],
            }
        )

    def test_displaced_header_detection(self) -> None:
        payload = (
            "说明,这不是表头,\n"
            "分类ID,中文名称,近12个月销量,近12个月净销售额,ASIN数量\n"
            "1.6416191E7,收纳盒,1000,2000000,50\n"
        ).encode("utf-8")
        frame, meta = parse_csv_payload(payload)
        self.assertEqual(meta["header_row"], 2)
        self.assertEqual(frame.iloc[0]["中文名称"], "收纳盒")

    def test_prepare_handles_scientific_ids_and_na(self) -> None:
        prepared, diagnostics = prepare_market_data(
            self.synthetic_raw(), MARKETS["UK"], fetch_metadata={"header_row": 1}
        )
        self.assertIn("30117754031", set(prepared["CategoryID"]))
        self.assertIn("16416191", set(prepared["CategoryID"]))
        self.assertEqual(diagnostics["source_rows"], 3)
        self.assertTrue(prepared["EligibleCore"].dtype == bool)
        self.assertFalse(prepared["CategoryID"].astype(str).str.contains(r"[Ee+]", regex=True).any())

    def test_scoring_is_bounded_and_na_safe(self) -> None:
        prepared, _ = prepare_market_data(self.synthetic_raw(), MARKETS["UK"])
        scored = apply_strategy_score(prepared, "大单品")
        self.assertFalse(scored["OpportunityScore"].isna().any())
        self.assertTrue(scored["OpportunityScore"].between(0, 100).all())
        self.assertTrue(scored["DataQualityScore"].between(0, 100).all())

    def test_trend_requires_two_snapshots(self) -> None:
        prepared, _ = prepare_market_data(self.synthetic_raw().iloc[:2], MARKETS["UK"])
        self.assertTrue(compute_trend_metrics(prepared).empty)
        first = prepared.copy()
        second = prepared.copy()
        first["SnapshotDate"] = pd.Timestamp("2026-01-01")
        second["SnapshotDate"] = pd.Timestamp("2026-02-01")
        second["Revenue"] = second["Revenue"] * 1.10
        second["SearchVolume"] = second["SearchVolume"] * 1.20
        second["ASINCount"] = second["ASINCount"] * 1.05
        history = pd.concat([first, second], ignore_index=True)
        trend = compute_trend_metrics(history)
        self.assertFalse(trend.empty)
        self.assertTrue(np.isfinite(trend["OpportunityMomentum"]).all())


if __name__ == "__main__":
    unittest.main()
