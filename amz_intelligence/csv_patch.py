from __future__ import annotations

import csv
from io import StringIO

import pandas as pd


def robust_parse_csv_payload(content: bytes) -> tuple[pd.DataFrame, dict[str, object]]:
    """Parse ragged published-sheet CSVs without losing a wider header row."""
    from . import engine

    stripped = content.lstrip()
    if not stripped:
        raise engine.DataLoadError("数据源返回空内容。")
    if stripped.startswith(b"<"):
        preview = stripped[:160].decode("utf-8", errors="ignore")
        raise engine.DataLoadError(f"数据源返回了网页而不是 CSV：{preview}")

    last_error: Exception | None = None
    raw: pd.DataFrame | None = None
    used_encoding = ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            text = content.decode(encoding)
            rows = [row for row in csv.reader(StringIO(text)) if any(str(cell).strip() for cell in row)]
            if not rows:
                raise engine.DataLoadError("CSV 中没有可读取的数据行。")
            width = max(len(row) for row in rows)
            raw = pd.DataFrame([row + [""] * (width - len(row)) for row in rows], dtype="string")
            used_encoding = encoding
            break
        except Exception as exc:
            last_error = exc
    if raw is None:
        raise engine.DataLoadError(f"CSV 解析失败：{last_error}")

    raw = raw.dropna(how="all").reset_index(drop=True)
    if raw.empty:
        raise engine.DataLoadError("CSV 中没有可读取的数据行。")
    header_row = engine._detect_header_row(raw)
    headers = engine._make_unique_headers(raw.iloc[header_row].tolist())
    frame = raw.iloc[header_row + 1 :].copy()
    frame.columns = headers
    frame = frame.replace(r"^\s*$", pd.NA, regex=True).dropna(how="all").reset_index(drop=True)

    normalized_headers = [engine.normalize_header(value) for value in headers]
    if not frame.empty:
        matches = pd.DataFrame(
            {
                column: frame[column].astype("string").map(engine.normalize_header).eq(normalized)
                for column, normalized in zip(headers, normalized_headers)
            }
        ).sum(axis=1)
        frame = frame.loc[matches < 3].reset_index(drop=True)

    return frame, {
        "encoding": used_encoding,
        "header_row": int(header_row + 1),
        "raw_rows": int(len(raw)),
        "parsed_rows": int(len(frame)),
        "columns": headers,
    }


def install_csv_parser_patch() -> None:
    from . import engine

    engine.parse_csv_payload = robust_parse_csv_payload
