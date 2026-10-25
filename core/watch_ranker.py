from __future__ import annotations

import asyncio
from dataclasses import dataclass

from core.config import AppConfig
from core.naver_blog_monitor import DEFAULT_RANK_SURFACES, BlogRankResult, NaverBlogMonitor
from core.storage import RankHistoryStore


@dataclass(frozen=True)
class WatchRankRun:
    keyword_count: int
    result_count: int
    results: list[BlogRankResult]


async def check_watch_keywords(
    config: AppConfig,
    store: RankHistoryStore,
    monitor: NaverBlogMonitor,
    *,
    limit: int = 30,
) -> WatchRankRun:
    if not config.has_target_blog:
        raise ValueError("TARGET_BLOG_ID or TARGET_BLOG_URL is not configured.")

    watch_keywords = store.watch_keywords()
    all_results: list[BlogRankResult] = []

    for item in watch_keywords:
        results = await monitor.rank_keyword_all(
            item["keyword"],
            config.target_blog_id,
            limit=limit,
            surfaces=DEFAULT_RANK_SURFACES,
        )
        store.save_results(results)
        all_results.extend(results)

    return WatchRankRun(
        keyword_count=len(watch_keywords),
        result_count=len(all_results),
        results=all_results,
    )


async def run_watch_loop(
    config: AppConfig,
    store: RankHistoryStore,
    monitor: NaverBlogMonitor,
    *,
    interval_minutes: int | None = None,
) -> None:
    interval_seconds = max(1, interval_minutes or config.watch_rank_interval_minutes) * 60

    while True:
        await check_watch_keywords(config, store, monitor)
        await asyncio.sleep(interval_seconds)
