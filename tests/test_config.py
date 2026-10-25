import os
import unittest
from unittest.mock import patch

from core.config import extract_blog_id, load_config, parse_keywords


class ConfigTests(unittest.TestCase):
    def test_extract_blog_id_from_url(self):
        self.assertEqual(extract_blog_id("https://blog.naver.com/myblog/123"), "myblog")

    def test_extract_blog_id_from_plain_id(self):
        self.assertEqual(extract_blog_id("myblog"), "myblog")

    def test_parse_keywords(self):
        self.assertEqual(parse_keywords("성수 맛집, 서울 데이트, "), ["성수 맛집", "서울 데이트"])

    def test_load_config_derives_target_blog_url(self):
        with patch.dict(
            os.environ,
            {
                "DISCORD_TOKEN": "token",
                "TARGET_BLOG_ID": "myblog",
                "TARGET_BLOG_URL": "",
                "TRACKED_KEYWORDS": "성수 맛집",
                "APP_DATA_DIR": "custom-data",
            },
            clear=False,
        ):
            config = load_config()

        self.assertEqual(config.target_blog_id, "myblog")
        self.assertEqual(config.target_blog_url, "https://blog.naver.com/myblog")
        self.assertEqual(config.tracked_keywords, ["성수 맛집"])
        self.assertEqual(str(config.app_data_dir), "custom-data")
        self.assertEqual(config.watch_rank_interval_minutes, 60)
        self.assertEqual(config.ai_provider, "groq")
        self.assertEqual(config.ai_model, "qwen/qwen3-32b")
        self.assertEqual(config.ai_base_url, "https://api.groq.com/openai/v1")


if __name__ == "__main__":
    unittest.main()
