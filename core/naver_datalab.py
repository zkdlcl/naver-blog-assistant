from __future__ import annotations

import asyncio
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from urllib.parse import urljoin
from urllib.request import Request, urlopen


DATALAB_HOME_URL = "https://datalab.naver.com/"
DATALAB_KEYWORD_URL = "https://datalab.naver.com/shoppingInsight/sKeyword.naver"

SHOPPING_CATEGORIES = {
    "50000000": "패션의류",
    "50000001": "패션잡화",
    "50000002": "화장품/미용",
    "50000003": "디지털/가전",
    "50000004": "가구/인테리어",
    "50000005": "출산/육아",
    "50000006": "식품",
    "50000007": "스포츠/레저",
    "50000008": "생활/건강",
    "50000009": "여가/생활편의",
    "50000010": "면세점",
    "50005542": "도서",
}


@dataclass(frozen=True)
class DatalabKeywordRank:
    rank: int
    keyword: str
    url: str


@dataclass(frozen=True)
class DatalabShoppingKeywords:
    source: str
    source_label: str
    category: dict[str, str]
    time_unit: str
    period: str
    items: list[DatalabKeywordRank]
    fetched_at: str

    def to_dict(self) -> dict:
        return asdict(self)


class NaverDatalabClient:
    async def shopping_keywords(
        self,
        *,
        category: str = "50000000",
        time_unit: str = "date",
    ) -> DatalabShoppingKeywords:
        return await asyncio.to_thread(self.fetch_shopping_keywords, category=category, time_unit=time_unit)

    def fetch_shopping_keywords(
        self,
        *,
        category: str = "50000000",
        time_unit: str = "date",
    ) -> DatalabShoppingKeywords:
        if category not in SHOPPING_CATEGORIES:
            raise ValueError("unsupported shopping category")
        if time_unit != "date":
            raise ValueError("only daily shopping keyword ranks are supported")

        source = self._fetch_home(category)
        return parse_datalab_home(source, category=category, time_unit=time_unit)

    def _fetch_home(self, category: str) -> str:
        request = Request(
            DATALAB_HOME_URL,
            headers={
                "User-Agent": "Mozilla/5.0 BMS/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cookie": f"_datalab_cid={category}",
            },
        )
        with urlopen(request, timeout=10) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")


def parse_datalab_home(source: str, *, category: str, time_unit: str = "date") -> DatalabShoppingKeywords:
    cards = [(period, items) for period, items in parse_keyword_rank_cards(source) if items]
    if not cards:
        raise ValueError("datalab keyword ranks not found")

    period, items = cards[-1]
    return DatalabShoppingKeywords(
        source="naver_datalab_shopping_insight",
        source_label="네이버 데이터랩 쇼핑인사이트 분야별 인기 검색어",
        category={"id": category, "name": SHOPPING_CATEGORIES.get(category, category)},
        time_unit=time_unit,
        period=period,
        items=items[:10],
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )


def parse_keyword_rank_cards(source: str) -> list[tuple[str, list[DatalabKeywordRank]]]:
    cards: list[tuple[str, list[DatalabKeywordRank]]] = []
    block_pattern = re.compile(
        r'<div class="keyword_rank">(.*?)(?=<div class="keyword_rank">|<div class="keyword_notice">|\Z)',
        flags=re.DOTALL,
    )
    for block in block_pattern.findall(source):
        period_match = re.search(r'<span class="title_cell">(.*?)</span>', block, flags=re.DOTALL)
        if not period_match:
            continue

        period = normalize_html_text(period_match.group(1))
        items: list[DatalabKeywordRank] = []
        item_pattern = re.compile(
            r'<a href="(?P<href>[^"]+)" class="list_area">\s*'
            r'<em class="num">(?P<rank>\d+)</em>\s*'
            r'<span class="title">(?P<keyword>.*?)</span>',
            flags=re.DOTALL,
        )
        for match in item_pattern.finditer(block):
            keyword = normalize_html_text(match.group("keyword"))
            if not keyword:
                continue
            items.append(
                DatalabKeywordRank(
                    rank=int(match.group("rank")),
                    keyword=keyword,
                    url=urljoin(DATALAB_HOME_URL, html.unescape(match.group("href"))),
                )
            )
        cards.append((period, items))

    return cards


def normalize_html_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<.*?>", " ", value))).strip()


def shopping_categories_payload() -> list[dict[str, str]]:
    return [{"id": category_id, "name": name} for category_id, name in SHOPPING_CATEGORIES.items()]


def datalab_keywords_to_json(result: DatalabShoppingKeywords) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False)
