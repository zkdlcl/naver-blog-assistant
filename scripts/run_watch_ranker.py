import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_config
from core.naver_blog_monitor import NaverBlogMonitor
from core.storage import store_from_data_dir
from core.watch_ranker import check_watch_keywords, run_watch_loop


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Check saved watch keywords and store rank history.")
    parser.add_argument("--loop", action="store_true", help="Run continuously using WATCH_RANK_INTERVAL_MINUTES.")
    parser.add_argument("--interval-minutes", type=int, default=None, help="Override loop interval in minutes.")
    args = parser.parse_args()

    config = load_config()
    store = store_from_data_dir(config.app_data_dir)
    monitor = NaverBlogMonitor()

    if args.loop:
        interval = args.interval_minutes or config.watch_rank_interval_minutes
        print(f"Starting watch keyword rank loop every {interval} minutes.")
        await run_watch_loop(config, store, monitor, interval_minutes=args.interval_minutes)
        return

    run = await check_watch_keywords(config, store, monitor)
    print(f"Checked {run.keyword_count} watch keywords and saved {run.result_count} rank results.")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
