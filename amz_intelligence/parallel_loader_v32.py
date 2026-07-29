from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import pandas as pd

from .config import MARKETS
from .engine import load_market


CATEGORICAL_COLUMNS = (
    "MarketCode",
    "Market",
    "MarketFlag",
    "CurrencyCode",
    "CurrencySymbol",
    "SnapshotLabel",
    "RootRaw",
    "RootStandard",
    "DigitalRisk",
)


def load_all_markets_parallel(
    market_codes: Iterable[str] | None = None,
    *,
    max_workers: int = 4,
) -> tuple[pd.DataFrame, dict[str, dict[str, object]], dict[str, str]]:
    """Load independent public market sources concurrently.

    This changes only cold-start latency. It does not change parsing, cleaning, factor
    calculation, scoring or rule classification.
    """

    codes = tuple(market_codes or MARKETS.keys())
    if not codes:
        return pd.DataFrame(), {}, {}

    frames_by_code: dict[str, pd.DataFrame] = {}
    diagnostics: dict[str, dict[str, object]] = {}
    errors: dict[str, str] = {}

    workers = max(1, min(int(max_workers), len(codes)))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="market-loader") as executor:
        futures = {executor.submit(load_market, code): code for code in codes}
        for future in as_completed(futures):
            code = futures[future]
            try:
                frame, diag = future.result()
                frames_by_code[code] = frame
                diagnostics[code] = diag
            except Exception as exc:  # each market remains independently recoverable
                errors[code] = str(exc)

    ordered_frames = [frames_by_code[code] for code in codes if code in frames_by_code]
    combined = pd.concat(ordered_frames, ignore_index=True) if ordered_frames else pd.DataFrame()
    if not combined.empty:
        for column in CATEGORICAL_COLUMNS:
            if column in combined:
                combined[column] = combined[column].astype("category")
    ordered_diagnostics = {code: diagnostics[code] for code in codes if code in diagnostics}
    ordered_errors = {code: errors[code] for code in codes if code in errors}
    return combined, ordered_diagnostics, ordered_errors
