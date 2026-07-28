"""Amazon multi-market category intelligence engine."""

from .config import MARKETS, STRATEGY_PRESETS, FACTOR_LABELS, MarketConfig
from .engine import (
    DataLoadError,
    apply_strategy_score,
    build_category_key,
    compute_trend_metrics,
    load_all_markets,
    load_market,
    prepare_market_data,
)

__all__ = [
    "MARKETS",
    "STRATEGY_PRESETS",
    "FACTOR_LABELS",
    "MarketConfig",
    "DataLoadError",
    "apply_strategy_score",
    "build_category_key",
    "compute_trend_metrics",
    "load_all_markets",
    "load_market",
    "prepare_market_data",
]

from .na_patch import install_na_safe_text_patch
from .csv_patch import install_csv_parser_patch

install_na_safe_text_patch()
install_csv_parser_patch()
