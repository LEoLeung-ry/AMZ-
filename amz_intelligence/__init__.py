"""Amazon multi-market category intelligence engine."""

from .config import FACTOR_LABELS, MARKETS, STRATEGY_PRESETS, MarketConfig
from .business_rules import (
    CAPABILITY_LABELS,
    ENTRY_LABELS,
    PROFILE_CAPABILITY_DEFAULTS,
    PROFILE_DEFAULTS,
    apply_business_model,
    enrich_entry_rules,
    profile_capabilities,
)
from .engine import (
    DataLoadError,
    apply_strategy_score,
    build_category_key,
    compute_trend_metrics,
    load_all_markets,
    load_market,
    prepare_market_data,
)
from .fx import DEFAULT_FX_REFERENCE, apply_cny_conversion, normalize_fx_rates

__all__ = [
    "MARKETS",
    "STRATEGY_PRESETS",
    "FACTOR_LABELS",
    "MarketConfig",
    "CAPABILITY_LABELS",
    "ENTRY_LABELS",
    "PROFILE_DEFAULTS",
    "PROFILE_CAPABILITY_DEFAULTS",
    "DEFAULT_FX_REFERENCE",
    "DataLoadError",
    "apply_business_model",
    "enrich_entry_rules",
    "profile_capabilities",
    "apply_cny_conversion",
    "normalize_fx_rates",
    "apply_strategy_score",
    "build_category_key",
    "compute_trend_metrics",
    "load_all_markets",
    "load_market",
    "prepare_market_data",
]

from .entry_rules_patch import install_supplemental_entry_rules
from .na_patch import install_na_safe_text_patch
from .csv_patch import install_csv_parser_patch

install_supplemental_entry_rules()
install_na_safe_text_patch()
install_csv_parser_patch()
