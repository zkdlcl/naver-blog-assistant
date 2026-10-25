import unittest
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from core.naver_blog_importer import ImportedBlogPost
from core.naver_blog_monitor import BlogPost, BlogRankResult
from core.storage import RankHistoryStore


class RankHistoryStoreTests(unittest.TestCase):
    def test_initialize_migrates_legacy_my_posts_schema(self):
        with TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "history.sqlite3"
            with sqlite3.connect(db_path) as connection:
                connection.executescript(
                    """
                    CREATE TABLE my_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE post_keywords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER NOT NULL,
                        keyword TEXT NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(post_id, keyword)
                    );
                    INSERT INTO my_posts (title, url)
                    VALUES ('기존 글', 'https://blog.naver.com/myblog/123');
                    INSERT INTO post_keywords (post_id, keyword)
                    VALUES (1, '서촌 카페');
                    """
                )

            store = RankHistoryStore(db_path)
            post = store.my_post(1)

        assert post is not None
        self.assertEqual(post["blog_id"], "myblog")
        self.assertEqual(post["post_id"], "123")
        self.assertTrue(post["content_hash"])
        self.assertEqual(post["keywords"][0]["keyword_type"], "target")
        self.assertEqual(post["content_text"], "")
        self.assertEqual(post["content_length"], 0)

    def test_save_and_read_recent_results(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            post = BlogPost(
                id="post-id",
                title="제목",
                url="https://blog.naver.com/myblog/123",
                summary="",
                collected_at="now",
            )
            store.save_results(
                [
                    BlogRankResult("키워드", "myblog", "desktop", 1, post, 30, "now"),
                    BlogRankResult("키워드", "myblog", "mobile", None, None, 30, "now"),
                ]
            )

            rows = store.recent(keyword="키워드")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["keyword"], "키워드")
        self.assertIn(rows[0]["surface"], {"desktop", "mobile"})

    def test_add_list_and_delete_watch_keyword(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            item = store.add_watch_keyword(" 예시 키워드 ")
            same_item = store.add_watch_keyword("예시 키워드")

            rows = store.watch_keywords()
            deleted = store.delete_watch_keyword(item["id"])
            rows_after_delete = store.watch_keywords()

        self.assertEqual(item["keyword"], "예시 키워드")
        self.assertEqual(same_item["id"], item["id"])
        self.assertEqual(len(rows), 1)
        self.assertTrue(deleted)
        self.assertEqual(rows_after_delete, [])

    def test_trend_returns_keyword_rows_in_chronological_order(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            post = BlogPost("post-id", "제목", "https://blog.naver.com/myblog/123", "", "now")
            store.save_results([BlogRankResult("키워드", "myblog", "desktop", 2, post, 30, "first")])
            store.save_results([BlogRankResult("키워드", "myblog", "desktop", 1, post, 30, "second")])

            rows = store.trend("키워드")

        self.assertEqual([row["rank"] for row in rows], [2, 1])

    def test_watch_keyword_summaries_include_latest_results(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            store.add_watch_keyword("키워드")
            post = BlogPost("post-id", "제목", "https://blog.naver.com/myblog/123", "", "now")
            store.save_results(
                [
                    BlogRankResult("키워드", "myblog", "desktop", 3, post, 30, "first"),
                    BlogRankResult("키워드", "myblog", "mobile", None, None, 30, "first"),
                ]
            )

            summaries = store.watch_keyword_summaries()

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["keyword"], "키워드")
        self.assertIsNotNone(summaries[0]["last_checked_at"])
        self.assertEqual(len(summaries[0]["latest_results"]), 2)
        self.assertEqual(len(summaries[0]["changes"]), 2)

    def test_watch_keyword_summaries_include_rank_changes(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            store.add_watch_keyword("키워드")
            post = BlogPost("post-id", "제목", "https://blog.naver.com/myblog/123", "", "now")
            store.save_results([BlogRankResult("키워드", "myblog", "desktop", 5, post, 30, "first")])
            store.save_results([BlogRankResult("키워드", "myblog", "desktop", 2, post, 30, "second")])

            summaries = store.watch_keyword_summaries()

        self.assertEqual(summaries[0]["changes"][0]["direction"], "up")
        self.assertEqual(summaries[0]["changes"][0]["delta"], 3)

    def test_my_post_summaries_order_by_latest_published_at(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            store.add_my_post(
                url="https://blog.naver.com/myblog/1",
                title="오래된 글",
                published_at="2025. 9. 15. 15:05",
            )
            store.add_my_post(
                url="https://blog.naver.com/myblog/2",
                title="최신 글",
                published_at="2026. 4. 16. 21:50",
            )
            store.add_my_post(
                url="https://blog.naver.com/myblog/3",
                title="중간 글",
                published_at="2026-03-12",
            )

            summaries = store.my_post_summaries()

        self.assertEqual([item["title"] for item in summaries], ["최신 글", "중간 글", "오래된 글"])

    def test_my_post_summaries_order_relative_published_at_by_import_time(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            store.add_my_post(
                url="https://blog.naver.com/myblog/1",
                title="예전 글",
                published_at="2021. 8. 9. 0:47",
                imported_at="2026-04-21T10:00:00+00:00",
            )
            store.add_my_post(
                url="https://blog.naver.com/myblog/2",
                title="어제 글",
                published_at="2026. 4. 20. 20:00",
                imported_at="2026-04-21T10:00:00+00:00",
            )
            store.add_my_post(
                url="https://blog.naver.com/myblog/3",
                title="방금 글",
                published_at="2시간 전",
                imported_at="2026-04-21T10:00:00+00:00",
            )

            summaries = store.my_post_summaries()

        self.assertEqual([item["title"] for item in summaries], ["방금 글", "어제 글", "예전 글"])

    def test_add_my_post_with_keyword_summaries(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            item = store.add_my_post(
                url="https://blog.naver.com/myblog/123",
                title="서촌 카페 후기",
                keywords=["서촌 카페", "스태픽스"],
                category="카페",
                published_at="2026-04-20",
                content_summary="주차와 메뉴를 정리한 후기",
            )
            post = BlogPost("post-id", "서촌 카페 후기", "https://blog.naver.com/myblog/123", "", "now")
            store.save_post_rank_results(
                item["id"],
                [BlogRankResult("서촌 카페", "myblog", "desktop", 2, post, 30, "now")],
            )

            summaries = store.my_post_summaries()

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["title"], "서촌 카페 후기")
        self.assertEqual(summaries[0]["blog_id"], "myblog")
        self.assertEqual(summaries[0]["post_id"], "123")
        self.assertEqual(summaries[0]["category"], "카페")
        self.assertEqual(summaries[0]["published_at"], "2026-04-20")
        self.assertEqual(summaries[0]["content_summary"], "주차와 메뉴를 정리한 후기")
        self.assertTrue(summaries[0]["content_hash"])
        self.assertEqual(len(summaries[0]["keywords"]), 2)
        self.assertEqual(summaries[0]["keywords"][0]["keyword_type"], "target")
        self.assertEqual(summaries[0]["keyword_summaries"][0]["keyword"], "서촌 카페")
        self.assertEqual(summaries[0]["keyword_summaries"][0]["latest_results"][0]["rank"], 2)

    def test_update_my_post_and_manage_keywords(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            item = store.add_my_post(
                url="https://m.blog.naver.com/myblog/123",
                title="서촌 카페 후기",
                keywords=["서촌 카페"],
            )
            first_hash = item["content_hash"]

            updated = store.update_my_post(
                item["id"],
                title="서촌 카페 주차 후기",
                category="카페",
                published_at="2026-04-20",
                content_summary="주차 중심 후기",
                keywords=["서촌 카페", "서촌 주차 카페"],
            )
            added_keyword = store.add_post_keyword(item["id"], "스태픽스", "target")
            assert added_keyword is not None
            deleted = store.delete_post_keyword(item["id"], added_keyword["id"])
            final = store.my_post(item["id"])

        assert updated is not None
        assert final is not None
        self.assertEqual(updated["url"], "https://blog.naver.com/myblog/123")
        self.assertEqual(updated["title"], "서촌 카페 주차 후기")
        self.assertEqual(updated["category"], "카페")
        self.assertEqual(updated["published_at"], "2026-04-20")
        self.assertEqual(updated["content_summary"], "주차 중심 후기")
        self.assertEqual(updated["blog_id"], "myblog")
        self.assertEqual(updated["post_id"], "123")
        self.assertNotEqual(updated["content_hash"], first_hash)
        self.assertTrue(deleted)
        self.assertEqual([item["keyword"] for item in final["keywords"]], ["서촌 카페", "서촌 주차 카페"])

    def test_import_my_blog_posts_upserts_body_text(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            first = ImportedBlogPost(
                title="서촌 카페 후기",
                url="https://blog.naver.com/myblog/123",
                blog_id="myblog",
                post_id="123",
                category="카페",
                published_at="2026. 04. 20.",
                content_summary="요약",
                content_text="첫 문단\n주차 정보",
                imported_at="now",
            )
            second = ImportedBlogPost(
                title="서촌 카페 수정 후기",
                url="https://m.blog.naver.com/myblog/123",
                blog_id="myblog",
                post_id="123",
                category="카페",
                published_at="2026. 04. 20.",
                content_summary="수정 요약",
                content_text="수정 본문",
                imported_at="later",
            )

            first_result = store.import_my_blog_posts([first])
            first_post = store.my_post_summaries()[0]
            second_result = store.import_my_blog_posts([second])
            second_post = store.my_post_summaries()[0]
            skipped_result = store.import_my_blog_posts([second], update_existing=False)
            skipped_post = store.my_post_summaries()[0]

        self.assertEqual(first_result["created_count"], 1)
        self.assertEqual(first_result["updated_count"], 0)
        self.assertEqual(first_post["content_text"], "첫 문단\n주차 정보")
        self.assertEqual(first_post["content_length"], len("첫 문단\n주차 정보"))
        self.assertEqual(first_post["imported_at"], "now")
        self.assertEqual(second_result["created_count"], 0)
        self.assertEqual(second_result["updated_count"], 1)
        self.assertEqual(second_result["skipped_count"], 0)
        self.assertEqual(second_post["title"], "서촌 카페 수정 후기")
        self.assertEqual(second_post["url"], "https://blog.naver.com/myblog/123")
        self.assertEqual(second_post["content_text"], "수정 본문")
        self.assertEqual(skipped_result["created_count"], 0)
        self.assertEqual(skipped_result["updated_count"], 0)
        self.assertEqual(skipped_result["skipped_count"], 1)
        self.assertEqual(skipped_post["title"], "서촌 카페 수정 후기")

    def test_owner_post_contexts_returns_analysis_fields(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            post = store.add_my_post(
                url="https://blog.naver.com/myblog/123",
                title="서촌 카페 후기",
                keywords=["서촌 카페"],
                category="카페",
                published_at="2026. 04. 20.",
                content_summary="주차와 메뉴 요약",
                content_text="본문에는 주차, 메뉴, 가격 정보가 있습니다.",
            )
            store.add_my_post(
                url="https://blog.naver.com/myblog/124",
                title="삭제할 글",
                keywords=["삭제 키워드"],
            )
            store.delete_my_post(2)

            contexts = store.owner_post_contexts()

        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0]["id"], post["id"])
        self.assertEqual(contexts[0]["title"], "서촌 카페 후기")
        self.assertEqual(contexts[0]["content_text"], "본문에는 주차, 메뉴, 가격 정보가 있습니다.")
        self.assertEqual(contexts[0]["keywords"], ["서촌 카페"])

    def test_delete_my_post_hides_it(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "history.sqlite3")
            item = store.add_my_post(
                url="https://blog.naver.com/myblog/123",
                title="서촌 카페 후기",
                keywords=["서촌 카페"],
            )
            deleted = store.delete_my_post(item["id"])
            summaries = store.my_post_summaries()

        self.assertTrue(deleted)
        self.assertEqual(summaries, [])


if __name__ == "__main__":
    unittest.main()
