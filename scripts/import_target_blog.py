from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import load_config
from core.naver_blog_importer import NaverBlogImporter
from core.storage import store_from_data_dir


async def run(max_posts: int, include_body: bool) -> int:
    config = load_config()
    if not config.has_target_blog:
        raise ValueError("TARGET_BLOG_ID or TARGET_BLOG_URL is not configured.")

    importer = NaverBlogImporter()
    result = await importer.import_blog(
        config.target_blog_id,
        max_posts=max_posts,
        include_body=include_body,
    )
    store = store_from_data_dir(config.app_data_dir)
    store_result = store.import_my_blog_posts(result.items, update_existing=False)

    print(
        "target_blog_id={target} found={found} imported={imported} "
        "created={created} skipped={skipped} failed={failed}".format(
            target=result.target_blog_id,
            found=result.found_count,
            imported=store_result["imported_count"],
            created=store_result["created_count"],
            skipped=store_result["skipped_count"],
            failed=result.failed_count,
        )
    )

    if result.failures:
        print("failures:")
        for failure in result.failures[:10]:
            print(f"- {failure['url']}: {failure['error']}")

    return 0 if result.failed_count == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Import new public posts from the configured target Naver blog.")
    parser.add_argument("--max-posts", type=int, default=1000)
    parser.add_argument("--no-body", action="store_true", help="Import post metadata without fetching body text.")
    args = parser.parse_args()
    return asyncio.run(run(max_posts=args.max_posts, include_body=not args.no_body))


if __name__ == "__main__":
    raise SystemExit(main())
