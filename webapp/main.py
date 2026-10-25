from __future__ import annotations

import asyncio
import hashlib
import hmac
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from core.config import AppConfig, load_config
from core.ai_content_advisor import OpenAICompatibleContentAdvisor
from core.content_analyzer import (
    ContentAnalysisRequest,
    OwnerPostContext,
    ReferencePost,
    analyze_content,
    content_analysis_to_dict,
)
from core.naver_blog_importer import NaverBlogImporter
from core.naver_blog_monitor import (
    DEFAULT_BLOG_SURFACES,
    DEFAULT_RANK_SURFACES,
    BlogRankResult,
    NaverBlogMonitor,
    build_search_url,
)
from core.naver_datalab import NaverDatalabClient, shopping_categories_payload
from core.signal_realtime import SignalRealtimeClient
from core.storage import RankHistoryStore, store_from_data_dir


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "webapp" / "static"
SESSION_COOKIE = "bms_session"


def session_token(password: str) -> str:
    return hashlib.sha256(f"bms-session:{password}".encode("utf-8")).hexdigest()


def is_authenticated(request: Request, config: AppConfig) -> bool:
    if not config.app_password:
        return True

    cookie_value = request.cookies.get(SESSION_COOKIE, "")
    return hmac.compare_digest(cookie_value, session_token(config.app_password))


def require_target_blog(config: AppConfig) -> None:
    if not config.has_target_blog:
        raise HTTPException(
            status_code=400,
            detail="TARGET_BLOG_ID or TARGET_BLOG_URL is not configured.",
        )


def browser_busy_http_error() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="다른 브라우저 작업이 진행 중입니다. 잠시 후 다시 시도하세요.",
    )


async def run_browser_task(lock: asyncio.Lock, message: str, operation):
    if lock.locked():
        raise browser_busy_http_error()

    async with lock:
        try:
            return await operation()
        except HTTPException:
            raise
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail=message) from error


def rank_result_to_dict(result: BlogRankResult) -> dict[str, Any]:
    return {
        "keyword": result.keyword,
        "target_blog_id": result.target_blog_id,
        "surface": result.surface,
        "result_url": result.result_url,
        "rank": result.rank,
        "checked_count": result.checked_count,
        "collected_at": result.collected_at,
        "post": None
        if result.post is None
        else {
            "id": result.post.id,
            "title": result.post.title,
            "url": result.post.url,
            "summary": result.post.summary,
            "collected_at": result.post.collected_at,
        },
    }


def blog_post_to_dict(post) -> dict[str, Any]:
    return {
        "id": post.id,
        "title": post.title,
        "url": post.url,
        "summary": post.summary,
        "collected_at": post.collected_at,
    }


def reference_posts_from_payload(payload: dict[str, Any]) -> list[ReferencePost]:
    raw_posts = payload.get("reference_posts", [])
    if not isinstance(raw_posts, list):
        return []

    posts = []
    for item in raw_posts[:50]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        posts.append(
            ReferencePost(
                title=title,
                summary=str(item.get("summary", "")).strip(),
                url=str(item.get("url", "")).strip(),
            )
        )
    return posts


def owner_posts_from_store(store: RankHistoryStore, *, limit: int = 1000) -> list[OwnerPostContext]:
    posts = []
    for item in store.owner_post_contexts(limit=limit):
        posts.append(
            OwnerPostContext(
                post_id=int(item["id"]),
                title=str(item.get("title", "")).strip(),
                url=str(item.get("url", "")).strip(),
                category=str(item.get("category", "")).strip(),
                published_at=str(item.get("published_at", "")).strip(),
                content_summary=str(item.get("content_summary", "")).strip(),
                content_text=str(item.get("content_text", "")).strip(),
                keywords=[
                    str(keyword).strip()
                    for keyword in item.get("keywords", [])
                    if str(keyword).strip()
                ],
            )
        )
    return posts


def post_fields_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in ("url", "title", "category", "published_at", "content_summary"):
        if key in payload:
            fields[key] = str(payload.get(key, "")).strip()

    if "keywords" in payload:
        keywords = payload.get("keywords", [])
        if not isinstance(keywords, list):
            raise HTTPException(status_code=400, detail="keywords must be a list.")
        fields["keywords"] = [str(keyword).strip() for keyword in keywords if str(keyword).strip()]

    return fields


def read_static_text(name: str) -> str:
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def create_app(
    config: AppConfig | None = None,
    monitor: NaverBlogMonitor | None = None,
    datalab_client: NaverDatalabClient | None = None,
    signal_client: SignalRealtimeClient | None = None,
    post_importer: NaverBlogImporter | None = None,
    store: RankHistoryStore | None = None,
    ai_content_advisor: OpenAICompatibleContentAdvisor | None = None,
) -> FastAPI:
    config = config or load_config()
    monitor = monitor or NaverBlogMonitor()
    datalab_client = datalab_client or NaverDatalabClient()
    signal_client = signal_client or SignalRealtimeClient()
    post_importer = post_importer or NaverBlogImporter()
    store = store or store_from_data_dir(config.app_data_dir)
    ai_content_advisor = ai_content_advisor or OpenAICompatibleContentAdvisor.from_config(config)

    app = FastAPI(title="BMS Mobile Web App")
    app.state.config = config
    app.state.monitor = monitor
    app.state.datalab_client = datalab_client
    app.state.signal_client = signal_client
    app.state.post_importer = post_importer
    app.state.store = store
    app.state.ai_content_advisor = ai_content_advisor
    app.state.browser_task_lock = asyncio.Lock()
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if not is_authenticated(request, config):
            return RedirectResponse("/login", status_code=303)
        return HTMLResponse(read_static_text("index.html"))

    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        if is_authenticated(request, config):
            return RedirectResponse("/", status_code=303)
        return HTMLResponse(read_static_text("login.html"))

    @app.get("/manifest.webmanifest")
    async def manifest() -> JSONResponse:
        return JSONResponse(
            {
                "name": "BMS Rank",
                "short_name": "BMS",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#ffffff",
                "theme_color": "#1f6f5b",
                "icons": [
                    {
                        "src": "/static/icon.svg",
                        "sizes": "any",
                        "type": "image/svg+xml",
                    }
                ],
            }
        )

    @app.get("/api/session")
    async def session(request: Request) -> dict[str, Any]:
        return {
            "authenticated": is_authenticated(request, config),
            "target_blog_id": config.target_blog_id,
            "auth_required": bool(config.app_password),
        }

    @app.post("/api/login")
    async def login(request: Request) -> JSONResponse:
        if not config.app_password:
            response = JSONResponse({"ok": True})
            return response

        payload = await request.json()
        password = str(payload.get("password", ""))
        if not hmac.compare_digest(password, config.app_password):
            raise HTTPException(status_code=401, detail="Invalid password.")

        response = JSONResponse({"ok": True})
        response.set_cookie(
            SESSION_COOKIE,
            session_token(config.app_password),
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=60 * 60 * 24 * 30,
        )
        return response

    @app.post("/api/logout")
    async def logout() -> JSONResponse:
        response = JSONResponse({"ok": True})
        response.delete_cookie(SESSION_COOKIE)
        return response

    @app.get("/api/rank")
    async def rank(request: Request, keyword: str) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")

        require_target_blog(config)
        results = await run_browser_task(
            app.state.browser_task_lock,
            "네이버 순위 확인 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
            lambda: monitor.rank_keyword_all(
                normalized_keyword,
                config.target_blog_id,
                limit=30,
                surfaces=DEFAULT_RANK_SURFACES,
            ),
        )
        store.save_results(results)
        return {
            "keyword": normalized_keyword,
            "target_blog_id": config.target_blog_id,
            "results": [rank_result_to_dict(result) for result in results],
        }

    @app.get("/api/blogs")
    async def blogs(request: Request, keyword: str, limit: int = 10) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")

        safe_limit = max(1, min(limit, 30))
        surface_posts = await run_browser_task(
            app.state.browser_task_lock,
            "기준별 상위글 확인 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
            lambda: monitor.search_all(
                normalized_keyword,
                surfaces=DEFAULT_BLOG_SURFACES,
                limit=safe_limit,
            ),
        )
        return {
            "keyword": normalized_keyword,
            "limit": safe_limit,
            "results": [
                {
                    "surface": surface,
                    "result_url": build_search_url(normalized_keyword, surface),
                    "checked_count": len(posts),
                    "posts": [blog_post_to_dict(post) for post in posts],
                }
                for surface, posts in surface_posts.items()
            ],
        }

    @app.get("/api/datalab/shopping-keywords")
    async def datalab_shopping_keywords(
        request: Request,
        category: str = "50000000",
        time_unit: str = "date",
    ) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        try:
            result = await datalab_client.shopping_keywords(category=category, time_unit=time_unit)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail="네이버 데이터랩 인기 키워드를 불러오지 못했습니다.") from error

        payload = result.to_dict()
        payload["categories"] = shopping_categories_payload()
        return payload

    @app.get("/api/signal/realtime-keywords")
    async def signal_realtime_keywords(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        try:
            result = await signal_client.realtime_keywords()
        except ValueError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail="Signal 실시간 검색어를 불러오지 못했습니다.") from error

        return result.to_dict()

    @app.post("/api/content-analysis")
    async def content_analysis(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        request_payload = await request.json()
        keyword = str(request_payload.get("keyword", "")).strip()
        title = str(request_payload.get("title", "")).strip()
        body = str(request_payload.get("body", "")).strip()
        if not keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")
        if not title:
            raise HTTPException(status_code=400, detail="title must not be empty.")
        if not body:
            raise HTTPException(status_code=400, detail="body must not be empty.")

        reference_posts = reference_posts_from_payload(request_payload)
        owner_posts = owner_posts_from_store(store)
        result = analyze_content(
            ContentAnalysisRequest(
                keyword=keyword,
                title=title,
                body=body,
                reference_posts=reference_posts,
                owner_posts=owner_posts,
            )
        )
        payload = content_analysis_to_dict(result)
        if ai_content_advisor is not None:
            try:
                feedback = await ai_content_advisor.advise(
                    ContentAnalysisRequest(
                        keyword=keyword,
                        title=title,
                        body=body,
                        reference_posts=reference_posts,
                        owner_posts=owner_posts,
                    ),
                    result,
                )
                payload["ai_feedback"] = feedback.to_dict()
            except Exception:
                payload["ai_feedback"] = None
        else:
            payload["ai_feedback"] = None
        return payload

    @app.get("/api/history")
    async def history(
        request: Request,
        keyword: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        normalized_keyword = keyword.strip() if keyword else None
        rows = store.recent(keyword=normalized_keyword, limit=limit)
        return {"items": rows}

    @app.get("/api/trends")
    async def trends(request: Request, keyword: str, limit: int = 200) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")

        return {
            "keyword": normalized_keyword,
            "items": store.trend(normalized_keyword, limit=limit),
        }

    @app.get("/api/watch-keywords")
    async def watch_keywords(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        return {"items": store.watch_keyword_summaries()}

    @app.get("/api/today-summary")
    async def today_summary(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        return {"items": store.watch_keyword_summaries()}

    @app.post("/api/watch-keywords")
    async def add_watch_keyword(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        keyword = str(payload.get("keyword", "")).strip()
        if not keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")

        return {"item": store.add_watch_keyword(keyword)}

    @app.delete("/api/watch-keywords/{keyword_id}")
    async def delete_watch_keyword(request: Request, keyword_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        deleted = store.delete_watch_keyword(keyword_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="watch keyword not found.")

        return {"ok": True}

    @app.get("/api/my-posts")
    @app.get("/api/posts")
    async def my_posts(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        return {"items": store.my_post_summaries()}

    @app.post("/api/my-posts")
    @app.post("/api/posts")
    async def add_my_post(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        fields = post_fields_from_payload(payload)
        if not fields.get("url"):
            raise HTTPException(status_code=400, detail="url must not be empty.")

        return {
            "item": store.add_my_post(**fields)
        }

    @app.get("/api/posts/{post_id}")
    async def post_detail(request: Request, post_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        post = store.my_post(post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="post not found.")

        return {"item": post}

    @app.patch("/api/posts/{post_id}")
    async def update_post(request: Request, post_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        fields = post_fields_from_payload(payload)
        try:
            post = store.update_my_post(post_id, **fields)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        if post is None:
            raise HTTPException(status_code=404, detail="post not found.")

        return {"item": post}

    @app.post("/api/posts/{post_id}/keywords")
    async def add_post_keyword(request: Request, post_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = await request.json()
        keyword = str(payload.get("keyword", "")).strip()
        keyword_type = str(payload.get("keyword_type", "target")).strip() or "target"
        if not keyword:
            raise HTTPException(status_code=400, detail="keyword must not be empty.")

        try:
            item = store.add_post_keyword(post_id, keyword, keyword_type)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        if item is None:
            raise HTTPException(status_code=404, detail="post not found.")

        return {"item": item}

    @app.post("/api/posts/import-target-blog")
    async def import_target_blog_posts(request: Request) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        require_target_blog(config)
        payload = await request.json()
        max_posts = int(payload.get("max_posts", 1000) or 1000)
        include_body = bool(payload.get("include_body", True))
        update_existing = bool(payload.get("update_existing", True))
        max_posts = max(1, min(max_posts, 2000))

        import_result = await run_browser_task(
            app.state.browser_task_lock,
            "내 블로그 글을 가져오는 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
            lambda: post_importer.import_blog(
                config.target_blog_id,
                max_posts=max_posts,
                include_body=include_body,
            ),
        )

        store_result = store.import_my_blog_posts(import_result.items, update_existing=update_existing)
        return {
            "target_blog_id": import_result.target_blog_id,
            "found_count": import_result.found_count,
            "imported_count": store_result["imported_count"],
            "created_count": store_result["created_count"],
            "updated_count": store_result["updated_count"],
            "skipped_count": store_result["skipped_count"],
            "failed_count": import_result.failed_count,
            "failures": import_result.failures[:10],
            "items": store.my_post_summaries(),
        }

    @app.delete("/api/posts/{post_id}/keywords/{keyword_id}")
    async def delete_post_keyword(request: Request, post_id: int, keyword_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        deleted = store.delete_post_keyword(post_id, keyword_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="post keyword not found.")

        return {"ok": True}

    @app.post("/api/my-posts/{post_id}/check")
    async def check_my_post(request: Request, post_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        post = store.my_post(post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="post not found.")

        keywords = [item["keyword"] for item in post["keywords"]]
        if not keywords:
            raise HTTPException(status_code=400, detail="post has no keywords.")

        async def check_post_keywords() -> list[dict[str, Any]]:
            checked: list[dict[str, Any]] = []
            for keyword in keywords:
                results = await monitor.rank_post_url_all(
                    keyword,
                    post["url"],
                    limit=30,
                    surfaces=DEFAULT_RANK_SURFACES,
                )
                store.save_post_rank_results(post_id, results)
                checked.append(
                    {
                        "keyword": keyword,
                        "results": [rank_result_to_dict(result) for result in results],
                    }
                )
            return checked

        checked = await run_browser_task(
            app.state.browser_task_lock,
            "글 순위 확인 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.",
            check_post_keywords,
        )

        return {
            "item": store.my_post(post_id),
            "checked": checked,
        }

    @app.delete("/api/my-posts/{post_id}")
    @app.delete("/api/posts/{post_id}")
    async def delete_my_post(request: Request, post_id: int) -> dict[str, Any]:
        if not is_authenticated(request, config):
            raise HTTPException(status_code=401, detail="Authentication required.")

        deleted = store.delete_my_post(post_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="post not found.")

        return {"ok": True}

    return app
