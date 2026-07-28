from __future__ import annotations

import sys
import requests

from amz_intelligence.config import MARKETS

code = sys.argv[1]
config = MARKETS[code]
response = requests.get(
    config.source_url,
    headers={
        "User-Agent": "Mozilla/5.0 (compatible; AmazonCategoryIntelligence/3.0)",
        "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
    },
    timeout=(10, 60),
)
print(code, response.status_code, response.headers.get("content-type"), len(response.content), response.url)
response.raise_for_status()
if len(response.content) < 1_000:
    raise AssertionError(f"{code} source response is too small: {len(response.content)} bytes")
if response.content.lstrip().startswith(b"<"):
    raise AssertionError(f"{code} returned HTML instead of CSV")
