from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.request import Request, urlopen


SIGNAL_REALTIME_URL = "https://api.signal.bz/news/realtime"


@dataclass(frozen=True)
class SignalRealtimeKeyword:
    rank: int
    keyword: str
    state: str
    summary_url: str


@dataclass(frozen=True)
class SignalRealtimeKeywords:
    source: str
    source_label: str
    now: int | None
    items: list[SignalRealtimeKeyword]
    fetched_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class SignalRealtimeClient:
    async def realtime_keywords(self) -> SignalRealtimeKeywords:
        return await asyncio.to_thread(self.fetch_realtime_keywords)

    def fetch_realtime_keywords(self) -> SignalRealtimeKeywords:
        request = Request(
            SIGNAL_REALTIME_URL,
            headers={
                "User-Agent": "Mozilla/5.0 BMS/1.0",
                "Accept": "application/json",
                "Referer": "https://www.signal.bz/news/realtime",
            },
        )
        with urlopen(request, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = json.loads(response.read().decode(charset, errors="replace"))
        return parse_signal_realtime(payload)


def parse_signal_realtime(payload: dict) -> SignalRealtimeKeywords:
    items = []
    for item in payload.get("top10", [])[:10]:
        try:
            rank = int(item.get("rank"))
        except (TypeError, ValueError):
            continue
        keyword = str(item.get("keyword", "")).strip()
        if not keyword:
            continue
        items.append(
            SignalRealtimeKeyword(
                rank=rank,
                keyword=keyword,
                state=str(item.get("state", "")).strip(),
                summary_url=str(item.get("summary", "")).strip(),
            )
        )

    if not items:
        raise ValueError("signal realtime keywords not found")

    return SignalRealtimeKeywords(
        source="signal_realtime",
        source_label="Signal 실시간 검색어",
        now=payload.get("now") if isinstance(payload.get("now"), int) else None,
        items=items,
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
