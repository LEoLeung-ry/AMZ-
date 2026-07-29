"""Optimized Streamlit entry: parallel data loading + selected-page rendering."""

from amz_intelligence import engine as _engine
from amz_intelligence.parallel_loader_v32 import load_all_markets_parallel as _parallel_loader

_engine.load_all_markets = _parallel_loader

from app_v32_fast import *  # noqa: F401,F403,E402
