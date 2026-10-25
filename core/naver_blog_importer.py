from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote_plus, unquote_plus

import httpx

from core.naver_blog_monitor import canonicalize_naver_blog_url


TITLE_LIST_URL = "https://blog.naver.com/PostTitleListAsync.naver"
MOBILE_POST_URL = "https://m.blog.naver.com/{blog_id}/{post_id}"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass(frozen=True)
class ImportedBlogPost:
    title: str
    url: str
    blog_id: str
    post_id: str
    category: str
    published_at: str
    content_summary: str
    content_text: str
    imported_at: str


@dataclass(frozen=True)
class BlogImportResult:
    target_blog_id: str
    found_count: int
    imported_count: int
    failed_count: int
    items: list[ImportedBlogPost]
    failures: list[dict[str, str]]


def build_title_list_url(blog_id: str, page: int, count_per_page: int = 30) -> str:
    normalized_blog_id = blog_id.strip()
    if not normalized_blog_id:
        raise ValueError("blog_id must not be empty")
    return (
        f"{TITLE_LIST_URL}?blogId={quote_plus(normalized_blog_id)}"
        f"&viewdate=&currentPage={page}&categoryNo=0&parentCategoryNo=&countPerPage={count_per_page}"
    )


def parse_title_list_payload(text: str) -> dict:
    # Naver includes escaped apostrophes in pagingHtml, which is not valid JSON.
    sanitized = text.replace("\\'", "'")
    return json.loads(sanitized)


def decode_title(value: str) -> str:
    return unescape(unquote_plus(value or "")).strip()


def normalize_html_text(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def extract_meta_content(html: str, key: str) -> str:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']{re.escape(key)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return normalize_html_text(match.group(1))
    return ""


def extract_blog_date(html: str) -> str:
    match = re.search(r'<p[^>]+class=["\']blog_date["\'][^>]*>(.*?)</p>', html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return normalize_html_text(match.group(1))
    return ""


def extract_smarteditor_text(html: str) -> str:
    spans = re.findall(
        r'<span[^>]+class=["\'][^"\']*se-fs-[^"\']*["\'][^>]*>(.*?)</span>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    lines = [normalize_html_text(span) for span in spans]
    lines = [line for line in lines if line]
    return "\n".join(dedupe_adjacent(lines)).strip()


def dedupe_adjacent(items: list[str]) -> list[str]:
    results = []
    previous = None
    for item in items:
        if item == previous:
            continue
        results.append(item)
        previous = item
    return results


def post_from_title_item(blog_id: str, item: dict, imported_at: str) -> ImportedBlogPost:
    post_id = str(item.get("logNo", "")).strip()
    title = decode_title(str(item.get("title", "")))
    return ImportedBlogPost(
        title=title or post_id,
        url=canonicalize_naver_blog_url(f"https://blog.naver.com/{blog_id}/{post_id}"),
        blog_id=blog_id,
        post_id=post_id,
        category=decode_title(str(item.get("categoryName", ""))) or str(item.get("categoryNo", "")).strip(),
        published_at=str(item.get("addDate", "")).strip(),
        content_summary="",
        content_text="",
        imported_at=imported_at,
    )


def merge_detail(post: ImportedBlogPost, html: str) -> ImportedBlogPost:
    title = extract_meta_content(html, "og:title") or post.title
    summary = extract_meta_content(html, "og:description")
    content_text = extract_smarteditor_text(html)
    published_at = extract_blog_date(html) or post.published_at
    return ImportedBlogPost(
        title=title,
        url=post.url,
        blog_id=post.blog_id,
        post_id=post.post_id,
        category=post.category,
        published_at=published_at,
        content_summary=summary,
        content_text=content_text,
        imported_at=post.imported_at,
    )


class NaverBlogImporter:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def import_blog(
        self,
        blog_id: str,
        *,
        max_posts: int = 1000,
        include_body: bool = True,
    ) -> BlogImportResult:
        normalized_blog_id = blog_id.strip()
        if not normalized_blog_id:
            raise ValueError("blog_id must not be empty")

        max_posts = max(1, min(max_posts, 2000))
        imported_at = datetime.now(timezone.utc).isoformat()
        failures: list[dict[str, str]] = []
        items: list[ImportedBlogPost] = []

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={**DEFAULT_HEADERS, "Referer": f"https://blog.naver.com/{normalized_blog_id}"},
            follow_redirects=True,
        ) as client:
            title_items = await self.fetch_title_items(client, normalized_blog_id, max_posts=max_posts)
            for raw_item in title_items[:max_posts]:
                post = post_from_title_item(normalized_blog_id, raw_item, imported_at)
                if not post.post_id:
                    failures.append({"url": post.url, "error": "missing post id"})
                    continue
                if include_body:
                    try:
                        html = await self.fetch_post_html(client, normalized_blog_id, post.post_id)
                        post = merge_detail(post, html)
                    except Exception as error:  # pragma: no cover - network failures vary.
                        failures.append({"url": post.url, "error": str(error)})
                items.append(post)

        return BlogImportResult(
            target_blog_id=normalized_blog_id,
            found_count=len(items) + len(failures),
            imported_count=len(items),
            failed_count=len(failures),
            items=items,
            failures=failures,
        )

    async def fetch_title_items(
        self,
        client: httpx.AsyncClient,
        blog_id: str,
        *,
        max_posts: int,
    ) -> list[dict]:
        count_per_page = 30
        page = 1
        total_count: int | None = None
        items: list[dict] = []

        while len(items) < max_posts:
            response = await client.get(build_title_list_url(blog_id, page, count_per_page=count_per_page))
            response.raise_for_status()
            payload = parse_title_list_payload(response.text)
            page_items = payload.get("postList") or []
            if not page_items:
                break
            items.extend(page_items)
            if total_count is None:
                total_count = int(str(payload.get("totalCount") or "0") or 0)
            if len(items) >= total_count:
                break
            page += 1

        return items[:max_posts]

    async def fetch_post_html(self, client: httpx.AsyncClient, blog_id: str, post_id: str) -> str:
        response = await client.get(MOBILE_POST_URL.format(blog_id=quote_plus(blog_id), post_id=quote_plus(post_id)))
        response.raise_for_status()
        return response.text
