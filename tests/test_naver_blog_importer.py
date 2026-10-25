import unittest
from unittest.mock import AsyncMock

from core.naver_blog_importer import (
    NaverBlogImporter,
    build_title_list_url,
    extract_blog_date,
    extract_meta_content,
    extract_smarteditor_text,
    merge_detail,
    parse_title_list_payload,
    post_from_title_item,
)


class NaverBlogImporterTests(unittest.TestCase):
    def test_build_title_list_url_requires_blog_id(self):
        with self.assertRaises(ValueError):
            build_title_list_url("", 1)

    def test_parse_title_list_payload_handles_naver_escaped_apostrophe(self):
        payload = parse_title_list_payload(
            '{"postList":[],"totalCount":"0","pagingHtml":"<div class=\\\'page\\\'>"}'
        )

        self.assertEqual(payload["postList"], [])
        self.assertEqual(payload["pagingHtml"], "<div class='page'>")

    def test_post_from_title_item_decodes_title_and_builds_url(self):
        post = post_from_title_item(
            "myblog",
            {
                "logNo": "123",
                "title": "%EC%84%9C%EC%B4%8C+%EC%B9%B4%ED%8E%98",
                "categoryName": "%EC%B9%B4%ED%8E%98",
                "addDate": "2026. 04. 20.",
            },
            "now",
        )

        self.assertEqual(post.title, "서촌 카페")
        self.assertEqual(post.url, "https://blog.naver.com/myblog/123")
        self.assertEqual(post.category, "카페")
        self.assertEqual(post.published_at, "2026. 04. 20.")

    def test_extract_mobile_post_detail_fields(self):
        html = """
        <meta property="og:title" content="서촌 카페 후기">
        <meta property="og:description" content="주차와 메뉴 요약">
        <p class="blog_date">2026. 04. 20.</p>
        <div class="se-main-container">
          <p><span class="se-fs-fs16">첫 문단</span></p>
          <p><span class="se-fs-fs16">주차 정보</span></p>
          <p><span class="se-fs-fs16">주차 정보</span></p>
        </div>
        """

        self.assertEqual(extract_meta_content(html, "og:title"), "서촌 카페 후기")
        self.assertEqual(extract_meta_content(html, "og:description"), "주차와 메뉴 요약")
        self.assertEqual(extract_blog_date(html), "2026. 04. 20.")
        self.assertEqual(extract_smarteditor_text(html), "첫 문단\n주차 정보")

    def test_merge_detail_prefers_detail_metadata(self):
        post = post_from_title_item("myblog", {"logNo": "123", "title": "old"}, "now")
        merged = merge_detail(
            post,
            """
            <meta property="og:title" content="새 제목">
            <meta property="og:description" content="요약">
            <p class="blog_date">2026. 04. 20.</p>
            <span class="se-fs-fs16">본문</span>
            """,
        )

        self.assertEqual(merged.title, "새 제목")
        self.assertEqual(merged.content_summary, "요약")
        self.assertEqual(merged.published_at, "2026. 04. 20.")
        self.assertEqual(merged.content_text, "본문")


class NaverBlogImporterAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_import_blog_fetches_title_list_and_details(self):
        importer = NaverBlogImporter()
        importer.fetch_title_items = AsyncMock(
            return_value=[
                {
                    "logNo": "123",
                    "title": "%EC%84%9C%EC%B4%8C+%EC%B9%B4%ED%8E%98",
                    "categoryName": "%EC%B9%B4%ED%8E%98",
                    "addDate": "2026. 04. 20.",
                }
            ]
        )
        importer.fetch_post_html = AsyncMock(
            return_value="""
            <meta property="og:title" content="서촌 카페 후기">
            <meta property="og:description" content="요약">
            <span class="se-fs-fs16">본문</span>
            """
        )

        result = await importer.import_blog("myblog", max_posts=10, include_body=True)

        self.assertEqual(result.target_blog_id, "myblog")
        self.assertEqual(result.found_count, 1)
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.items[0].title, "서촌 카페 후기")
        self.assertEqual(result.items[0].content_text, "본문")


if __name__ == "__main__":
    unittest.main()
