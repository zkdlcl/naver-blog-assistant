import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.config import AppConfig
from core.naver_blog_monitor import BlogPost, BlogRankResult
from core.storage import RankHistoryStore
from core.watch_ranker import check_watch_keywords


class FakeMonitor:
    async def rank_keyword_all(self, keyword, target_blog_id, *, limit, surfaces):
        post = BlogPost(
            id="post-id",
            title=f"{keyword} 글",
            url=f"https://blog.naver.com/{target_blog_id}/123",
            summary="",
            collected_at="now",
        )
        return [
            BlogRankResult(keyword, target_blog_id, surface, 1, post, limit, "now")
            for surface in surfaces
        ]


def make_test_config(app_data_dir: Path) -> AppConfig:
    return AppConfig(
        discord_token="",
        target_blog_id="myblog",
        target_blog_url="https://blog.naver.com/myblog",
        tracked_keywords=[],
        app_password="",
        app_host="127.0.0.1",
        app_port=8000,
        app_data_dir=app_data_dir,
        watch_rank_interval_minutes=60,
        ai_provider="groq",
        ai_api_key="",
        ai_model="qwen/qwen3-32b",
        ai_base_url="https://api.groq.com/openai/v1",
    )


class WatchRankerTests(unittest.IsolatedAsyncioTestCase):
    async def test_check_watch_keywords_saves_rank_history(self):
        with TemporaryDirectory() as temp_dir:
            store = RankHistoryStore(Path(temp_dir) / "test.sqlite3")
            store.add_watch_keyword("예시 키워드")

            run = await check_watch_keywords(make_test_config(Path(temp_dir)), store, FakeMonitor())
            rows = store.recent(keyword="예시 키워드")

        self.assertEqual(run.keyword_count, 1)
        self.assertEqual(run.result_count, 5)
        self.assertEqual(len(rows), 5)


if __name__ == "__main__":
    unittest.main()
