"""Stable Streamlit entry point.

Do not import the UI module as a normal Python module here. Streamlit reruns this
entry script for every session and widget interaction, while imported modules can
remain cached in ``sys.modules``. A top-level ``from app import *`` can therefore
render once and then produce a blank page on refresh. ``runpy.run_path`` executes
the UI script on every Streamlit rerun in a fresh namespace.
"""

from __future__ import annotations

import runpy

from amz_intelligence import model_v32
from amz_intelligence.robustness_lowmem import add_strategy_robustness_lowmem


# Reduce peak memory while preserving the same aggregate robustness fields.
model_v32.add_strategy_robustness = add_strategy_robustness_lowmem

# Execute, rather than import, so every browser refresh and widget rerun renders UI.
runpy.run_path("app_v32_responsive.py", run_name="__main__")
