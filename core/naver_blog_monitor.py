from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import quote_plus
from urllib.parse import urlparse

from playwright.async_api import Page

from core.browser_helper import BrowserSettings, browser_session


NAVER_BLOG_SEARCH_URL = "https://search.naver.com/search.naver?where=blog&sm=tab_opt&nso=so:dd,p:all&query={query}"
NAVER_DESKTOP_INTEGRATED_SEARCH_URL = "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query={query}"
NAVER_MOBILE_INTEGRATED_SEARCH_URL = "https://m.search.naver.com/search.naver?where=m&sm=mtp_hty.top&query={query}"
NAVER_MOBILE_BLOG_SEARCH_URL = "https://m.search.naver.com/search.naver?where=m_blog&sm=mtb_opt&nso=so:dd,p:all&query={query}"
NAVER_BLOG_SECTION_SEARCH_URL = "https://section.blog.naver.com/Search/Post.naver?pageNo=1&rangeType=ALL&orderBy=sim&keyword={query}"

SEARCH_SURFACE_LABELS = {
    "desktop": "PC 통합검색",
    "desktop_blog": "PC 블로그탭",
    "mobile": "모바일 통합검색",
    "mobile_blog": "모바일 블로그탭",
    "blog_section": "네이버 블로그 섹션",
}

DEFAULT_RANK_SURFACES = ("desktop", "mobile", "desktop_blog", "mobile_blog", "blog_section")
DEFAULT_BLOG_SURFACES = ("desktop", "desktop_blog", "blog_section", "mobile", "mobile_blog")

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)


@dataclass(frozen=True)
class BlogPost:
    id: str
    title: str
    url: str
    summary: str
    collected_at: str


@dataclass(frozen=True)
class BlogRankResult:
    keyword: str
    target_blog_id: str
    surface: str
    rank: int | None
    post: BlogPost | None
    checked_count: int
    collected_at: str

    @property
    def in_range(self) -> bool:
        return self.rank is not None

    @property
    def result_url(self) -> str:
        return build_search_url(self.keyword, self.surface)


def build_blog_search_url(keyword: str) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")
    return NAVER_BLOG_SEARCH_URL.format(query=quote_plus(normalized_keyword))


def build_mobile_blog_search_url(keyword: str) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")
    return NAVER_MOBILE_BLOG_SEARCH_URL.format(query=quote_plus(normalized_keyword))


def build_blog_section_search_url(keyword: str) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")
    return NAVER_BLOG_SECTION_SEARCH_URL.format(query=quote_plus(normalized_keyword))


def build_mobile_integrated_search_url(keyword: str) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")
    return NAVER_MOBILE_INTEGRATED_SEARCH_URL.format(query=quote_plus(normalized_keyword))


def build_desktop_integrated_search_url(keyword: str) -> str:
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        raise ValueError("keyword must not be empty")
    return NAVER_DESKTOP_INTEGRATED_SEARCH_URL.format(query=quote_plus(normalized_keyword))


def build_search_url(keyword: str, surface: str) -> str:
    if surface == "desktop":
        return build_desktop_integrated_search_url(keyword)
    if surface == "desktop_blog":
        return build_blog_search_url(keyword)
    if surface == "mobile":
        return build_mobile_integrated_search_url(keyword)
    if surface == "mobile_blog":
        return build_mobile_blog_search_url(keyword)
    if surface == "blog_section":
        return build_blog_section_search_url(keyword)
    raise ValueError(f"Unsupported search surface: {surface}")


def settings_for_surface(settings: BrowserSettings, surface: str) -> BrowserSettings:
    if not surface.startswith("mobile"):
        return settings

    return replace(
        settings,
        user_agent=MOBILE_USER_AGENT,
        viewport_width=390,
        viewport_height=844,
    )


def make_post_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def canonicalize_naver_blog_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc not in {"blog.naver.com", "m.blog.naver.com"}:
        return url

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return url

    return f"https://blog.naver.com/{parts[0]}/{parts[1]}"


def is_blog_post_url(url: str) -> bool:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return parsed.netloc in {"blog.naver.com", "m.blog.naver.com"} and len(parts) >= 2 and parts[1].isdigit()


def post_belongs_to_blog(url: str, blog_id: str) -> bool:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    return (
        parsed.netloc in {"blog.naver.com", "m.blog.naver.com"}
        and len(parts) >= 2
        and parts[0].lower() == blog_id.lower()
    )


def post_matches_url(url: str, target_url: str) -> bool:
    return canonicalize_naver_blog_url(url) == canonicalize_naver_blog_url(target_url)


def blog_id_from_post_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc in {"blog.naver.com", "m.blog.naver.com"} and parts:
        return parts[0]
    return ""


def dedupe_posts(posts: Iterable[BlogPost]) -> list[BlogPost]:
    seen: set[str] = set()
    results: list[BlogPost] = []
    for post in posts:
        if post.id in seen:
            continue
        seen.add(post.id)
        results.append(post)
    return results


async def extract_blog_posts(page: Page, *, limit: int = 5) -> list[BlogPost]:
    collected_at = datetime.now(timezone.utc).isoformat()
    raw_posts = await page.evaluate(
        """
        ({ limit }) => {
          const anchors = [...document.querySelectorAll('a[href*="blog.naver.com"]')];
          const postUrlPattern = /^https:\\/\\/(m\\.)?blog\\.naver\\.com\\/[^/?#]+\\/\\d+/;
          const posts = [];

          for (const anchor of anchors) {
            const href = anchor.href;
            const title = (anchor.innerText || anchor.textContent || '').trim();

            if (!href || !postUrlPattern.test(href) || !title || title.length < 2) {
              continue;
            }

            if (/^\\d+$/.test(title) || title.includes('blog.naver.com') || title.includes('naver.com›')) {
              continue;
            }

            const container = anchor.closest('li, article, section, div') || anchor.parentElement;
            const text = container ? (container.innerText || container.textContent || '') : title;
            const summary = text
              .replace(title, '')
              .replace(/\\s+/g, ' ')
              .trim()
              .slice(0, 300);

            posts.push({ title, url: href, summary });

            if (posts.length >= limit * 3) {
              break;
            }
          }

          return posts;
        }
        """,
        {"limit": limit},
    )

    posts = [
        BlogPost(
            id=make_post_id(canonicalize_naver_blog_url(item["url"])),
            title=item["title"],
            url=canonicalize_naver_blog_url(item["url"]),
            summary=item["summary"],
            collected_at=collected_at,
        )
        for item in raw_posts
    ]
    return dedupe_posts(posts)[:limit]


class NaverBlogMonitor:
    def __init__(self, settings: BrowserSettings | None = None) -> None:
        self.settings = settings or BrowserSettings()

    async def search(self, keyword: str, *, limit: int = 5) -> list[BlogPost]:
        return await self.search_surface(keyword, surface="desktop_blog", limit=limit)

    async def search_surface(self, keyword: str, *, surface: str = "desktop", limit: int = 5) -> list[BlogPost]:
        url = build_search_url(keyword, surface)
        effective_settings = settings_for_surface(self.settings, surface)
        async with browser_session(settings=effective_settings) as session:
            await session.page.goto(url, wait_until="domcontentloaded")
            await session.page.wait_for_timeout(1000)
            return await extract_blog_posts(session.page, limit=limit)

    async def search_all(
        self,
        keyword: str,
        *,
        surfaces: tuple[str, ...] = DEFAULT_BLOG_SURFACES,
        limit: int = 5,
    ) -> dict[str, list[BlogPost]]:
        results: dict[str, list[BlogPost]] = {}
        for surface in surfaces:
            results[surface] = await self.search_surface(keyword, surface=surface, limit=limit)
        return results

    async def rank_keyword(
        self,
        keyword: str,
        target_blog_id: str,
        *,
        limit: int = 30,
        surface: str = "desktop",
    ) -> BlogRankResult:
        if not target_blog_id.strip():
            raise ValueError("target_blog_id must not be empty")

        url = build_search_url(keyword, surface)
        effective_settings = settings_for_surface(self.settings, surface)
        async with browser_session(settings=effective_settings) as session:
            await session.page.goto(url, wait_until="domcontentloaded")
            await session.page.wait_for_timeout(1000)
            posts = await extract_blog_posts(session.page, limit=limit)

        for index, post in enumerate(posts, start=1):
            if post_belongs_to_blog(post.url, target_blog_id):
                return BlogRankResult(
                    keyword=keyword,
                    target_blog_id=target_blog_id,
                    surface=surface,
                    rank=index,
                    post=post,
                    checked_count=len(posts),
                    collected_at=datetime.now(timezone.utc).isoformat(),
                )

        return BlogRankResult(
            keyword=keyword,
            target_blog_id=target_blog_id,
            surface=surface,
            rank=None,
            post=None,
            checked_count=len(posts),
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

    async def rank_keyword_all(
        self,
        keyword: str,
        target_blog_id: str,
        *,
        limit: int = 30,
        surfaces: tuple[str, ...] = DEFAULT_RANK_SURFACES,
    ) -> list[BlogRankResult]:
        results: list[BlogRankResult] = []
        for surface in surfaces:
            results.append(
                await self.rank_keyword(
                    keyword,
                    target_blog_id,
                    limit=limit,
                    surface=surface,
                )
            )
        return results

    async def rank_post_url(
        self,
        keyword: str,
        post_url: str,
        *,
        limit: int = 30,
        surface: str = "desktop",
    ) -> BlogRankResult:
        normalized_url = canonicalize_naver_blog_url(post_url.strip())
        if not normalized_url:
            raise ValueError("post_url must not be empty")

        target_blog_id = blog_id_from_post_url(normalized_url)
        url = build_search_url(keyword, surface)
        effective_settings = settings_for_surface(self.settings, surface)
        async with browser_session(settings=effective_settings) as session:
            await session.page.goto(url, wait_until="domcontentloaded")
            await session.page.wait_for_timeout(1000)
            posts = await extract_blog_posts(session.page, limit=limit)

        for index, post in enumerate(posts, start=1):
            if post_matches_url(post.url, normalized_url):
                return BlogRankResult(
                    keyword=keyword,
                    target_blog_id=target_blog_id,
                    surface=surface,
                    rank=index,
                    post=post,
                    checked_count=len(posts),
                    collected_at=datetime.now(timezone.utc).isoformat(),
                )

        return BlogRankResult(
            keyword=keyword,
            target_blog_id=target_blog_id,
            surface=surface,
            rank=None,
            post=None,
            checked_count=len(posts),
            collected_at=datetime.now(timezone.utc).isoformat(),
        )

    async def rank_post_url_all(
        self,
        keyword: str,
        post_url: str,
        *,
        limit: int = 30,
        surfaces: tuple[str, ...] = DEFAULT_RANK_SURFACES,
    ) -> list[BlogRankResult]:
        results: list[BlogRankResult] = []
        for surface in surfaces:
            results.append(
                await self.rank_post_url(
                    keyword,
                    post_url,
                    limit=limit,
                    surface=surface,
                )
            )
        return results


def format_posts_for_discord(keyword: str, posts: list[BlogPost]) -> str:
    if not posts:
        return f"`{keyword}` 검색 결과에서 블로그 글을 찾지 못했습니다."

    lines = [f"`{keyword}` 최신 블로그 결과 {len(posts)}개"]
    for index, post in enumerate(posts, start=1):
        lines.append(f"{index}. {post.title}\n{post.url}")
    return "\n".join(lines)


def format_rank_for_discord(result: BlogRankResult) -> str:
    surface_label = SEARCH_SURFACE_LABELS.get(result.surface, result.surface)
    if not result.in_range:
        return (
            f"[{surface_label}] `{result.keyword}` 검색 결과 {result.checked_count}개 안에서 "
            f"`{result.target_blog_id}` 블로그 글을 찾지 못했습니다.\n"
            f"결과 화면: {result.result_url}"
        )

    assert result.post is not None
    return (
        f"[{surface_label}] `{result.keyword}` 현재 순위: {result.rank}위\n"
        f"{result.post.title}\n"
        f"글 URL: {result.post.url}\n"
        f"결과 화면: {result.result_url}"
    )


def format_rank_results_for_discord(results: list[BlogRankResult]) -> str:
    if not results:
        return "순위 확인 결과가 없습니다."
    return "\n\n".join(format_rank_for_discord(result) for result in results)
