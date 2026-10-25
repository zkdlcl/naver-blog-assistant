import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_config
from core.naver_blog_monitor import NaverBlogMonitor, format_rank_for_discord
from core.storage import store_from_data_dir


async def main() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / ".gitkeep").touch(exist_ok=True)

    config = load_config()
    print("BMS project init check")
    print(f"- data directory: {data_dir}")
    print(f"- discord token: {'set' if config.discord_token else 'missing'}")
    print(f"- target blog id: {config.target_blog_id or 'missing'}")
    print(f"- tracked keywords: {', '.join(config.tracked_keywords) if config.tracked_keywords else 'missing'}")
    store = store_from_data_dir(config.app_data_dir)
    print(f"- sqlite database: {store.db_path}")

    if config.has_target_blog and config.tracked_keywords:
        monitor = NaverBlogMonitor()
        result = await monitor.rank_keyword(config.tracked_keywords[0], config.target_blog_id, limit=10)
        print("- rank smoke check:")
        print(format_rank_for_discord(result))
    else:
        print("- rank smoke check: skipped because target blog or tracked keywords are missing")


if __name__ == "__main__":
    asyncio.run(main())
