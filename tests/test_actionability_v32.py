from __future__ import annotations

import unittest

import pandas as pd

from amz_intelligence.actionability_v32 import add_actionability_v32


class ActionabilityV32Tests(unittest.TestCase):
    def test_broad_exact_names_are_warned_without_changing_entry_class(self) -> None:
        frame = pd.DataFrame(
            {
                "Category": ["系统", "粉末", "垃圾袋", "收纳箱"],
                "CategoryLocal": ["Systeme", "Powders", "Trash Bags", "Storage Boxes"],
                "NodePath": ["root > home", "", "root > home > bags", "root > home > storage > boxes"],
                "EntryClass": ["A", "A", "A", "A"],
            }
        )
        result = add_actionability_v32(frame)
        self.assertTrue(bool(result.loc[0, "BroadNodeWarning"]))
        self.assertTrue(bool(result.loc[1, "BroadNodeWarning"]))
        self.assertFalse(bool(result.loc[2, "BroadNodeWarning"]))
        self.assertFalse(bool(result.loc[3, "BroadNodeWarning"]))
        self.assertEqual(result.loc[0, "EntryClass"], "A")
        self.assertEqual(float(result.loc[3, "NodePathDepth"]), 4.0)
        self.assertGreater(float(result.loc[3, "ActionabilityScore"]), float(result.loc[0, "ActionabilityScore"]))


if __name__ == "__main__":
    unittest.main()
