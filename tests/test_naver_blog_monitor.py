import unittest
from unittest.mock import AsyncMock, Mock, patch

from core.naver_blog_monitor import (
    BlogPost,
    BlogRankResult,
    NaverBlogMonitor,
    build_desktop_integrated_search_url,
    build_mobile_integrated_search_url,
    build_mobile_blog_search_url,
    build_blog_section_search_url,
    build_blog_search_url,
    build_search_url,
    canonicalize_naver_blog_url,
    dedupe_posts,
    extract_blog_posts,
    format_rank_for_discord,
    format_rank_results_for_discord,
    post_belongs_to_blog,
    settings_for_surface,
    format_posts_for_discord,
)
from core.browser_helper import BrowserSettings


class NaverBlogMonitorTests(unittest.TestCase):
    def test_build_blog_search_url_encodes_keyword(self):
        url = build_blog_search_url("성수 맛집")

        self.assertIn("where=blog", url)
        self.assertIn("query=%EC%84%B1%EC%88%98+%EB%A7%9B%EC%A7%91", url)

    def test_build_blog_search_url_rejects_empty_keyword(self):
        with self.assertRaises(ValueError):
            build_blog_search_url("   ")

    def test_build_mobile_blog_search_url_encodes_keyword(self):
        url = build_mobile_blog_search_url("성수 맛집")

        self.assertIn("m.search.naver.com", url)
        self.assertIn("where=m_blog", url)
        self.assertIn("query=%EC%84%B1%EC%88%98+%EB%A7%9B%EC%A7%91", url)

    def test_build_blog_section_search_url_encodes_keyword(self):
        url = build_blog_section_search_url("성수 맛집")

        self.assertIn("section.blog.naver.com/Search/Post.naver", url)
        self.assertIn("keyword=%EC%84%B1%EC%88%98+%EB%A7%9B%EC%A7%91", url)

    def test_build_mobile_integrated_search_url_encodes_keyword(self):
        url = build_mobile_integrated_search_url("성수 맛집")

        self.assertIn("m.search.naver.com", url)
        self.assertIn("where=m", url)
        self.assertIn("query=%EC%84%B1%EC%88%98+%EB%A7%9B%EC%A7%91", url)

    def test_build_desktop_integrated_search_url_encodes_keyword(self):
        url = build_desktop_integrated_search_url("성수 맛집")

        self.assertIn("search.naver.com", url)
        self.assertIn("where=nexearch", url)
        self.assertIn("query=%EC%84%B1%EC%88%98+%EB%A7%9B%EC%A7%91", url)

    def test_build_search_url_rejects_unknown_surface(self):
        with self.assertRaises(ValueError):
            build_search_url("성수 맛집", "unknown")

    def test_settings_for_surface_uses_mobile_browser_shape(self):
        settings = settings_for_surface(BrowserSettings(), "mobile")

        self.assertIn("Mobile", settings.user_agent)
        self.assertEqual(settings.viewport, {"width": 390, "height": 844})

    def test_post_belongs_to_blog_matches_blog_id(self):
        self.assertTrue(post_belongs_to_blog("https://blog.naver.com/myblog/12345", "myblog"))
        self.assertTrue(post_belongs_to_blog("https://m.blog.naver.com/myblog/12345", "myblog"))
        self.assertFalse(post_belongs_to_blog("https://blog.naver.com/other/12345", "myblog"))

    def test_canonicalize_naver_blog_url_converts_mobile_url(self):
        self.assertEqual(
            canonicalize_naver_blog_url("https://m.blog.naver.com/myblog/12345?x=1"),
            "https://blog.naver.com/myblog/12345",
        )

    def test_dedupe_posts_keeps_first_match(self):
        first = BlogPost("same", "first", "https://blog.naver.com/a", "", "now")
        second = BlogPost("same", "second", "https://blog.naver.com/a", "", "now")

        self.assertEqual(dedupe_posts([first, second]), [first])

    def test_format_posts_for_discord(self):
        post = BlogPost("id", "제목", "https://blog.naver.com/test/1", "요약", "now")

        message = format_posts_for_discord("테스트", [post])

        self.assertIn("`테스트` 최신 블로그 결과 1개", message)
        self.assertIn("https://blog.naver.com/test/1", message)

    def test_format_rank_for_discord_in_range(self):
        post = BlogPost("id", "제목", "https://blog.naver.com/myblog/1", "", "now")
        result = BlogRankResult("키워드", "myblog", "desktop", 2, post, 10, "now")

        message = format_rank_for_discord(result)

        self.assertIn("[PC 통합검색]", message)
        self.assertIn("현재 순위: 2위", message)
        self.assertIn("글 URL: https://blog.naver.com/myblog/1", message)
        self.assertIn("결과 화면: https://search.naver.com/search.naver", message)
        self.assertIn("where=nexearch", message)

    def test_format_rank_for_discord_out_of_range_includes_result_url(self):
        result = BlogRankResult("키워드", "myblog", "desktop_blog", None, None, 30, "now")

        message = format_rank_for_discord(result)

        self.assertIn("[PC 블로그탭]", message)
        self.assertIn("찾지 못했습니다.", message)
        self.assertIn("결과 화면: https://search.naver.com/search.naver", message)
        self.assertIn("where=blog", message)

    def test_format_rank_results_for_discord_combines_surfaces(self):
        post = BlogPost("id", "제목", "https://blog.naver.com/myblog/1", "", "now")
        results = [
            BlogRankResult("키워드", "myblog", "desktop", 1, post, 10, "now"),
            BlogRankResult("키워드", "myblog", "mobile", None, None, 0, "now"),
        ]

        message = format_rank_results_for_discord(results)

        self.assertIn("[PC 통합검색]", message)
        self.assertIn("[모바일 통합검색]", message)


class ExtractBlogPostsTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_blog_posts_limits_and_dedupes(self):
        page = AsyncMock()
        page.evaluate = AsyncMock(
            return_value=[
                {"title": "첫 글", "url": "https://blog.naver.com/a/1", "summary": "요약"},
                {"title": "첫 글 중복", "url": "https://blog.naver.com/a/1", "summary": "요약"},
                {"title": "둘째 글", "url": "https://m.blog.naver.com/b/2", "summary": ""},
            ]
        )

        posts = await extract_blog_posts(page, limit=2)

        self.assertEqual(len(posts), 2)
        self.assertEqual(posts[0].title, "첫 글")
        self.assertEqual(posts[1].title, "둘째 글")
        self.assertEqual(posts[1].url, "https://blog.naver.com/b/2")


class FakeBrowserSession:
    def __init__(self):
        self.page = Mock()
        self.page.goto = AsyncMock()
        self.page.wait_for_timeout = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class NaverBlogMonitorAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_uses_blog_search_without_surface_variable(self):
        session = FakeBrowserSession()
        expected = [BlogPost("id", "제목", "https://blog.naver.com/a/1", "", "now")]

        with (
            patch("core.naver_blog_monitor.browser_session", return_value=session) as browser_session,
            patch("core.naver_blog_monitor.extract_blog_posts", AsyncMock(return_value=expected)),
        ):
            posts = await NaverBlogMonitor().search("예시 키워드", limit=1)

        self.assertEqual(posts, expected)
        browser_session.assert_called_once()
        session.page.goto.assert_awaited_once()

    async def test_search_surface_uses_requested_surface(self):
        session = FakeBrowserSession()
        expected = [BlogPost("id", "제목", "https://blog.naver.com/a/1", "", "now")]

        with (
            patch("core.naver_blog_monitor.browser_session", return_value=session),
            patch("core.naver_blog_monitor.extract_blog_posts", AsyncMock(return_value=expected)),
        ):
            posts = await NaverBlogMonitor().search_surface("예시 키워드", surface="blog_section", limit=1)

        self.assertEqual(posts, expected)
        called_url = session.page.goto.await_args.args[0]
        self.assertIn("section.blog.naver.com/Search/Post.naver", called_url)


if __name__ == "__main__":
    unittest.main()
