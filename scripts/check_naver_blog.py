import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.naver_blog_monitor import NaverBlogMonitor, format_posts_for_discord


async def main() -> None:
    keyword = " ".join(sys.argv[1:]).strip() or "네이버 블로그"
    monitor = NaverBlogMonitor()
    posts = await monitor.search(keyword, limit=3)
    print(format_posts_for_discord(keyword, posts))


if __name__ == "__main__":
    asyncio.run(main())
