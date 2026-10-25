import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from core.config import AppConfig
from core.ai_content_advisor import AiContentFeedback
from core.naver_datalab import DatalabKeywordRank, DatalabShoppingKeywords
from core.naver_blog_importer import BlogImportResult, ImportedBlogPost
from core.signal_realtime import SignalRealtimeKeyword, SignalRealtimeKeywords
from core.naver_blog_monitor import BlogPost, BlogRankResult
from core.storage import RankHistoryStore
from webapp.main import create_app, session_token


class FakeMonitor:
    async def search(self, keyword, *, limit):
        return [
            BlogPost(
                id=f"post-{index}",
                title=f"상위 글 {index}",
                url=f"https://blog.naver.com/other/{index}",
                summary=f"요약 {index}",
                collected_at="now",
            )
            for index in range(1, limit + 1)
        ]

    async def search_all(self, keyword, *, surfaces, limit):
        posts = await self.search(keyword, limit=limit)
        return {surface: posts for surface in surfaces}

    async def rank_keyword_all(self, keyword, target_blog_id, *, limit, surfaces):
        post = BlogPost(
            id="post-id",
            title="테스트 글",
            url=f"https://blog.naver.com/{target_blog_id}/123",
            summary="",
            collected_at="now",
        )
        return [
            BlogRankResult(
                keyword,
                target_blog_id,
                surface,
                1 if index == 0 else None,
                post if index == 0 else None,
                limit,
                "now",
            )
            for index, surface in enumerate(surfaces)
        ]

    async def rank_post_url_all(self, keyword, post_url, *, limit, surfaces):
        post = BlogPost(
            id="post-id",
            title="테스트 글",
            url=post_url,
            summary="",
            collected_at="now",
        )
        return [
            BlogRankResult(
                keyword,
                "myblog",
                surface,
                2 if index == 0 else None,
                post if index == 0 else None,
                limit,
                "now",
            )
            for index, surface in enumerate(surfaces)
        ]


class FailingMonitor(FakeMonitor):
    async def rank_keyword_all(self, keyword, target_blog_id, *, limit, surfaces):
        raise RuntimeError("monitor failed")


class FakePostImporter:
    async def import_blog(self, blog_id, *, max_posts, include_body):
        return BlogImportResult(
            target_blog_id=blog_id,
            found_count=2,
            imported_count=2,
            failed_count=0,
            items=[
                ImportedBlogPost(
                    title="가져온 글 1",
                    url=f"https://blog.naver.com/{blog_id}/101",
                    blog_id=blog_id,
                    post_id="101",
                    category="카페",
                    published_at="2026. 04. 20.",
                    content_summary="요약 1",
                    content_text="본문 1",
                    imported_at="now",
                ),
                ImportedBlogPost(
                    title="가져온 글 2",
                    url=f"https://blog.naver.com/{blog_id}/102",
                    blog_id=blog_id,
                    post_id="102",
                    category="맛집",
                    published_at="2026. 04. 19.",
                    content_summary="요약 2",
                    content_text="본문 2",
                    imported_at="now",
                ),
            ],
            failures=[],
        )


class FakeDatalabClient:
    async def shopping_keywords(self, *, category="50000000", time_unit="date"):
        return DatalabShoppingKeywords(
            source="naver_datalab_shopping_insight",
            source_label="네이버 데이터랩 쇼핑인사이트 분야별 인기 검색어",
            category={"id": category, "name": "패션의류"},
            time_unit=time_unit,
            period="2026.04.18.(토)",
            items=[
                DatalabKeywordRank(rank=1, keyword="원피스", url="https://datalab.naver.com/shoppingInsight/sKeyword.naver?keyword=원피스"),
                DatalabKeywordRank(rank=2, keyword="블라우스", url="https://datalab.naver.com/shoppingInsight/sKeyword.naver?keyword=블라우스"),
            ],
            fetched_at="now",
        )


class FakeSignalClient:
    async def realtime_keywords(self):
        return SignalRealtimeKeywords(
            source="signal_realtime",
            source_label="Signal 실시간 검색어",
            now=1776702791523,
            items=[
                SignalRealtimeKeyword(rank=1, keyword="실시간 키워드", state="+", summary_url="https://summary.signal.bz/1"),
                SignalRealtimeKeyword(rank=2, keyword="뉴스 키워드", state="s", summary_url="https://summary.signal.bz/2"),
            ],
            fetched_at="now",
        )


class FakeAiAdvisor:
    async def advise(self, request, result):
        return AiContentFeedback(
            provider="groq",
            model="qwen/qwen3-32b",
            summary="제목과 첫 문단을 정리하면 체감 품질이 바로 올라갑니다.",
            priority_actions=["제목에 핵심 키워드를 압축해 넣기", "첫 문단에서 방문 목적과 결론을 먼저 말하기"],
            title_suggestions=["서촌 카페 스태픽스 직접 다녀온 후기", "서촌 카페 스태픽스 메뉴와 분위기 후기"],
            opening_paragraph="서촌 카페 스태픽스에 직접 다녀왔습니다. 조용한 좌석과 커피 맛은 좋았지만 주말에는 대기 시간이 있었습니다. 방문 전에 메뉴와 주차 정보를 먼저 보고 가면 편합니다.",
            differentiation_point="상위글이 메뉴와 위치를 반복한다면, 이번 글은 좌석 분위기와 방문 시간대 경험을 앞세우세요.",
        )


def make_test_config(app_password: str = "secret", app_data_dir: Path | None = None) -> AppConfig:
    return AppConfig(
        discord_token="",
        target_blog_id="myblog",
        target_blog_url="https://blog.naver.com/myblog",
        tracked_keywords=[],
        app_password=app_password,
        app_host="127.0.0.1",
        app_port=8000,
        app_data_dir=app_data_dir or Path("data"),
        watch_rank_interval_minutes=60,
        ai_provider="groq",
        ai_api_key="",
        ai_model="qwen/qwen3-32b",
        ai_base_url="https://api.groq.com/openai/v1",
    )


class WebAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_root_redirects_to_login_when_unauthenticated(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get("/")

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/login")

    async def test_login_sets_session_cookie(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/login", json={"password": "secret"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies.get("bms_session"), session_token("secret"))

    async def test_rank_requires_authentication(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/rank?keyword=test")

        self.assertEqual(response.status_code, 401)

    async def test_rank_returns_pc_and_mobile_results(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                response = await client.get("/api/rank?keyword=서촌%20스태픽스")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["keyword"], "예시 키워드")
        self.assertEqual(len(payload["results"]), 5)
        self.assertEqual(payload["results"][0]["rank"], 1)
        self.assertIn("where=nexearch", payload["results"][0]["result_url"])
        self.assertIsNone(payload["results"][1]["rank"])
        self.assertIn("m.search.naver.com", payload["results"][1]["result_url"])

    async def test_rank_returns_busy_error_when_browser_task_is_running(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        await app.state.browser_task_lock.acquire()
        transport = httpx.ASGITransport(app=app)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                response = await client.get("/api/rank?keyword=서촌%20스태픽스")
        finally:
            app.state.browser_task_lock.release()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "다른 브라우저 작업이 진행 중입니다. 잠시 후 다시 시도하세요.")

    async def test_rank_returns_friendly_browser_error_message(self):
        app = create_app(config=make_test_config(), monitor=FailingMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.get("/api/rank?keyword=서촌%20스태픽스")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "네이버 순위 확인 중 오류가 발생했습니다. 잠시 후 다시 시도하세요.")

    async def test_history_returns_saved_rank_results(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                await client.get("/api/rank?keyword=서촌%20스태픽스")
                response = await client.get("/api/history?keyword=서촌%20스태픽스")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 5)
        self.assertEqual(payload["items"][0]["keyword"], "예시 키워드")

    async def test_trends_returns_saved_rank_results(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                await client.get("/api/rank?keyword=서촌%20스태픽스")
                response = await client.get("/api/trends?keyword=서촌%20스태픽스")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["keyword"], "예시 키워드")
        self.assertEqual(len(payload["items"]), 5)
        self.assertEqual(payload["items"][0]["surface"], "desktop")

    async def test_blogs_returns_top_posts(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.get("/api/blogs?keyword=서촌%20스태픽스&limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["keyword"], "예시 키워드")
        self.assertEqual(len(payload["results"]), 5)
        self.assertEqual(payload["results"][0]["surface"], "desktop")
        self.assertIn("where=nexearch", payload["results"][0]["result_url"])
        self.assertEqual(len(payload["results"][0]["posts"]), 5)
        self.assertEqual(payload["results"][0]["posts"][0]["title"], "상위 글 1")

    async def test_datalab_shopping_keywords_returns_category_rank(self):
        app = create_app(
            config=make_test_config(),
            monitor=FakeMonitor(),
            datalab_client=FakeDatalabClient(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.get("/api/datalab/shopping-keywords?category=50000000")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "naver_datalab_shopping_insight")
        self.assertEqual(payload["category"]["name"], "패션의류")
        self.assertEqual(payload["items"][0]["keyword"], "원피스")
        self.assertTrue(payload["categories"])

    async def test_signal_realtime_keywords_returns_rank(self):
        app = create_app(
            config=make_test_config(),
            monitor=FakeMonitor(),
            signal_client=FakeSignalClient(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.get("/api/signal/realtime-keywords")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["source"], "signal_realtime")
        self.assertEqual(payload["items"][0]["keyword"], "실시간 키워드")

    async def test_content_analysis_requires_authentication(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/content-analysis",
                json={"keyword": "서촌 카페", "title": "서촌 카페 후기", "body": "본문"},
            )

        self.assertEqual(response.status_code, 401)

    async def test_content_analysis_validates_required_fields(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.post(
                "/api/content-analysis",
                json={"keyword": "서촌 카페", "title": "", "body": "본문"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "title must not be empty.")

    async def test_content_analysis_returns_proxy_score(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.post(
                "/api/content-analysis",
                json={
                    "keyword": "서촌 카페",
                    "title": "서촌 카페 스태픽스 직접 방문 후기",
                    "body": (
                        "방문 목적과 결론\n"
                        "서촌 카페에 직접 방문했고 위치, 주차, 메뉴, 가격을 확인했습니다.\n"
                        "장점은 분위기와 커피 맛이고 단점은 주말 웨이팅입니다.\n"
                        "2026년 4월 기준으로 예약 가능 여부와 영업시간도 확인했습니다."
                    ),
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("내부 프록시 점수", payload["score_label"])
        self.assertEqual(len(payload["checks"]), 7)
        self.assertTrue(payload["priority_actions"])
        self.assertTrue(payload["title_suggestions"])
        self.assertIsNone(payload["ai_feedback"])

    async def test_content_analysis_returns_ai_feedback_when_configured(self):
        app = create_app(
            config=make_test_config(),
            monitor=FakeMonitor(),
            ai_content_advisor=FakeAiAdvisor(),
        )
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.post(
                "/api/content-analysis",
                json={
                    "keyword": "서촌 카페",
                    "title": "서촌 카페 스태픽스 후기",
                    "body": "서촌 카페에 직접 다녀왔고 메뉴와 분위기를 적었습니다.",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["ai_feedback"]["provider"], "groq")
        self.assertTrue(payload["ai_feedback"]["priority_actions"])

    async def test_content_analysis_accepts_reference_posts_for_serp_candidates(self):
        app = create_app(config=make_test_config(), monitor=FakeMonitor())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            client.cookies.set("bms_session", session_token("secret"))
            response = await client.post(
                "/api/content-analysis",
                json={
                    "keyword": "서촌 카페",
                    "title": "서촌 카페 조용한 곳",
                    "body": "서촌 카페에 다녀왔습니다. 창가 자리가 조용했습니다.",
                    "reference_posts": [
                        {
                            "title": "서촌 카페 주차 가능한 곳",
                            "summary": "위치와 주차, 대표 메뉴를 정리했습니다.",
                            "url": "https://blog.naver.com/a/1",
                        },
                        {
                            "title": "서촌 카페 메뉴와 주차 후기",
                            "summary": "영업시간, 웨이팅, 가격 정보를 확인했습니다.",
                            "url": "https://blog.naver.com/b/2",
                        },
                    ],
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("serp_missing_topic_candidates", payload)
        self.assertEqual(payload["serp_missing_topic_candidates"][0]["topic"], "주차")
        self.assertIn("독자 기대 정보 확인용", payload["serp_missing_topic_candidates"][0]["guidance"])

    async def test_content_analysis_uses_stored_owner_posts(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            store.add_my_post(
                url="https://blog.naver.com/myblog/123",
                title="서촌 카페 주차 후기",
                keywords=["서촌 카페"],
                category="카페",
                published_at="2026. 04. 20.",
                content_summary="서촌 카페 주차와 메뉴 가격 정리",
                content_text="서촌 공영주차장, 메뉴판, 가격, 웨이팅 정보를 담았습니다.",
            )
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                response = await client.post(
                    "/api/content-analysis",
                    json={
                        "keyword": "서촌 카페",
                        "title": "서촌 카페 조용한 신상 카페 후기",
                        "body": (
                            "서촌 카페에 다녀왔습니다. 조용한 좌석과 커피 맛을 중심으로 적었습니다.\n"
                            "주차는 근처 공영주차장을 이용했고 메뉴 가격도 확인했습니다."
                        ),
                    },
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["internal_link_candidates"][0]["post_id"], 1)
        self.assertEqual(payload["existing_post_overlap_warnings"][0]["overlap_type"], "target_keyword")

    async def test_watch_keywords_can_be_added_listed_and_deleted(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                create_response = await client.post("/api/watch-keywords", json={"keyword": "예시 키워드"})
                await client.get("/api/rank?keyword=서촌%20스태픽스")
                list_response = await client.get("/api/watch-keywords")
                keyword_id = create_response.json()["item"]["id"]
                delete_response = await client.delete(f"/api/watch-keywords/{keyword_id}")
                list_after_delete_response = await client.get("/api/watch-keywords")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["item"]["keyword"], "예시 키워드")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["items"]), 1)
        self.assertEqual(len(list_response.json()["items"][0]["latest_results"]), 5)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(list_after_delete_response.json()["items"], [])

    async def test_today_summary_returns_watch_keyword_summaries(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                await client.post("/api/watch-keywords", json={"keyword": "예시 키워드"})
                await client.get("/api/rank?keyword=서촌%20스태픽스")
                response = await client.get("/api/today-summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["keyword"], "예시 키워드")
        self.assertEqual(len(payload["items"][0]["changes"]), 5)

    async def test_my_posts_can_be_added_listed_checked_and_deleted(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                create_response = await client.post(
                    "/api/my-posts",
                    json={
                        "url": "https://blog.naver.com/myblog/123",
                        "title": "서촌 카페 후기",
                        "category": "카페",
                        "published_at": "2026-04-20",
                        "content_summary": "주차와 메뉴를 정리한 후기",
                        "keywords": ["서촌 카페"],
                    },
                )
                post_id = create_response.json()["item"]["id"]
                check_response = await client.post(f"/api/my-posts/{post_id}/check")
                list_response = await client.get("/api/my-posts")
                delete_response = await client.delete(f"/api/my-posts/{post_id}")
                list_after_delete_response = await client.get("/api/my-posts")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["item"]["title"], "서촌 카페 후기")
        self.assertEqual(create_response.json()["item"]["blog_id"], "myblog")
        self.assertEqual(create_response.json()["item"]["post_id"], "123")
        self.assertEqual(create_response.json()["item"]["category"], "카페")
        self.assertEqual(check_response.status_code, 200)
        self.assertEqual(len(check_response.json()["checked"]), 1)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()["items"]), 1)
        latest_results = list_response.json()["items"][0]["keyword_summaries"][0]["latest_results"]
        desktop_result = next(result for result in latest_results if result["surface"] == "desktop")
        self.assertEqual(desktop_result["rank"], 2)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(list_after_delete_response.json()["items"], [])

    async def test_posts_api_supports_detail_update_and_keyword_management(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(config=make_test_config(app_data_dir=Path(temp_dir)), monitor=FakeMonitor(), store=store)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                create_response = await client.post(
                    "/api/posts",
                    json={
                        "url": "https://m.blog.naver.com/myblog/123",
                        "title": "서촌 카페 후기",
                        "keywords": ["서촌 카페"],
                    },
                )
                post_id = create_response.json()["item"]["id"]
                detail_response = await client.get(f"/api/posts/{post_id}")
                update_response = await client.patch(
                    f"/api/posts/{post_id}",
                    json={
                        "title": "서촌 카페 주차 후기",
                        "category": "카페",
                        "published_at": "2026-04-20",
                        "content_summary": "주차 중심 후기",
                        "keywords": ["서촌 카페", "서촌 주차 카페"],
                    },
                )
                keyword_response = await client.post(
                    f"/api/posts/{post_id}/keywords",
                    json={"keyword": "스태픽스", "keyword_type": "target"},
                )
                keyword_id = keyword_response.json()["item"]["id"]
                delete_keyword_response = await client.delete(f"/api/posts/{post_id}/keywords/{keyword_id}")
                final_response = await client.get(f"/api/posts/{post_id}")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["item"]["url"], "https://blog.naver.com/myblog/123")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()["item"]
        self.assertEqual(updated["title"], "서촌 카페 주차 후기")
        self.assertEqual(updated["category"], "카페")
        self.assertEqual(updated["published_at"], "2026-04-20")
        self.assertEqual(updated["content_summary"], "주차 중심 후기")
        self.assertEqual(len(updated["keywords"]), 2)
        self.assertEqual(keyword_response.status_code, 200)
        self.assertEqual(keyword_response.json()["item"]["keyword_type"], "target")
        self.assertEqual(delete_keyword_response.status_code, 200)
        self.assertEqual([item["keyword"] for item in final_response.json()["item"]["keywords"]], ["서촌 카페", "서촌 주차 카페"])

    async def test_import_target_blog_posts_uses_configured_blog(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            app = create_app(
                config=make_test_config(app_data_dir=Path(temp_dir)),
                monitor=FakeMonitor(),
                post_importer=FakePostImporter(),
                store=store,
            )
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                client.cookies.set("bms_session", session_token("secret"))
                response = await client.post(
                    "/api/posts/import-target-blog",
                    json={"max_posts": 1000, "include_body": True, "update_existing": True},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["target_blog_id"], "myblog")
        self.assertEqual(payload["created_count"], 2)
        self.assertEqual(payload["updated_count"], 0)
        self.assertEqual(payload["skipped_count"], 0)
        self.assertEqual(payload["failed_count"], 0)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["content_text"], "본문 1")


if __name__ == "__main__":
    unittest.main()
