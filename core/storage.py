from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from core.naver_blog_importer import ImportedBlogPost
from core.naver_blog_monitor import BlogRankResult, blog_id_from_post_url, canonicalize_naver_blog_url


SCHEMA = """
CREATE TABLE IF NOT EXISTS rank_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    target_blog_id TEXT NOT NULL,
    surface TEXT NOT NULL,
    rank INTEGER,
    checked_count INTEGER NOT NULL,
    post_title TEXT,
    post_url TEXT,
    collected_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rank_history_keyword_created
ON rank_history(keyword, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rank_history_surface_created
ON rank_history(surface, created_at DESC);

CREATE TABLE IF NOT EXISTS watch_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watch_keywords_enabled_created
ON watch_keywords(enabled, created_at DESC);

CREATE TABLE IF NOT EXISTS my_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    blog_id TEXT NOT NULL DEFAULT '',
    post_id TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    published_at TEXT NOT NULL DEFAULT '',
    content_summary TEXT NOT NULL DEFAULT '',
    content_text TEXT NOT NULL DEFAULT '',
    content_length INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_my_posts_enabled_created
ON my_posts(enabled, created_at DESC);

CREATE TABLE IF NOT EXISTS post_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    keyword_type TEXT NOT NULL DEFAULT 'target',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(post_id, keyword),
    FOREIGN KEY(post_id) REFERENCES my_posts(id)
);

CREATE INDEX IF NOT EXISTS idx_post_keywords_post_enabled
ON post_keywords(post_id, enabled, created_at DESC);

CREATE TABLE IF NOT EXISTS post_rank_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    surface TEXT NOT NULL,
    rank INTEGER,
    checked_count INTEGER NOT NULL,
    result_url TEXT NOT NULL,
    matched_title TEXT,
    matched_url TEXT,
    collected_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(post_id) REFERENCES my_posts(id)
);

CREATE INDEX IF NOT EXISTS idx_post_rank_history_post_keyword_created
ON post_rank_history(post_id, keyword, created_at DESC);
"""

MY_POST_COLUMN_MIGRATIONS = {
    "blog_id": "ALTER TABLE my_posts ADD COLUMN blog_id TEXT NOT NULL DEFAULT ''",
    "post_id": "ALTER TABLE my_posts ADD COLUMN post_id TEXT NOT NULL DEFAULT ''",
    "category": "ALTER TABLE my_posts ADD COLUMN category TEXT NOT NULL DEFAULT ''",
    "published_at": "ALTER TABLE my_posts ADD COLUMN published_at TEXT NOT NULL DEFAULT ''",
    "content_summary": "ALTER TABLE my_posts ADD COLUMN content_summary TEXT NOT NULL DEFAULT ''",
    "content_text": "ALTER TABLE my_posts ADD COLUMN content_text TEXT NOT NULL DEFAULT ''",
    "content_length": "ALTER TABLE my_posts ADD COLUMN content_length INTEGER NOT NULL DEFAULT 0",
    "content_hash": "ALTER TABLE my_posts ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''",
    "imported_at": "ALTER TABLE my_posts ADD COLUMN imported_at TEXT NOT NULL DEFAULT ''",
    "updated_at": "ALTER TABLE my_posts ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
}

POST_KEYWORD_COLUMN_MIGRATIONS = {
    "keyword_type": "ALTER TABLE post_keywords ADD COLUMN keyword_type TEXT NOT NULL DEFAULT 'target'",
}


def rank_change(surface: str, latest: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    latest_rank = latest["rank"]
    previous_rank = previous["rank"] if previous else None

    if previous is None:
        direction = "new"
        delta = None
    elif latest_rank == previous_rank:
        direction = "same"
        delta = 0
    elif latest_rank is None:
        direction = "lost"
        delta = None
    elif previous_rank is None:
        direction = "entered"
        delta = None
    else:
        delta = previous_rank - latest_rank
        direction = "up" if delta > 0 else "down"

    return {
        "surface": surface,
        "rank": latest_rank,
        "previous_rank": previous_rank,
        "direction": direction,
        "delta": delta,
        "created_at": latest["created_at"],
    }


class RankHistoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            self._ensure_columns(connection, "my_posts", MY_POST_COLUMN_MIGRATIONS)
            self._ensure_columns(connection, "post_keywords", POST_KEYWORD_COLUMN_MIGRATIONS)
            self._backfill_post_identity(connection)

    def _ensure_columns(
        self,
        connection: sqlite3.Connection,
        table: str,
        migrations: dict[str, str],
    ) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for column, statement in migrations.items():
            if column not in existing:
                connection.execute(statement)

    def _backfill_post_identity(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT id, title, url, category, published_at, content_summary, content_text
            FROM my_posts
            WHERE blog_id = '' OR post_id = '' OR content_hash = ''
            """
        ).fetchall()
        for row in rows:
            url = row["url"]
            connection.execute(
                """
                UPDATE my_posts
                SET blog_id = ?,
                    post_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    blog_id_from_post_url(url),
                    post_id_from_post_url(url),
                    row["id"],
                ),
            )
            self._refresh_post_content_hash(connection, int(row["id"]))

    def save_results(self, results: list[BlogRankResult]) -> None:
        if not results:
            return

        rows = []
        for result in results:
            rows.append(
                (
                    result.keyword,
                    result.target_blog_id,
                    result.surface,
                    result.rank,
                    result.checked_count,
                    result.post.title if result.post else None,
                    result.post.url if result.post else None,
                    result.collected_at,
                )
            )

        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO rank_history (
                    keyword,
                    target_blog_id,
                    surface,
                    rank,
                    checked_count,
                    post_title,
                    post_url,
                    collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def recent(self, *, keyword: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        params: list[Any] = []
        where = ""

        if keyword:
            where = "WHERE keyword = ?"
            params.append(keyword)

        params.append(limit)

        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    keyword,
                    target_blog_id,
                    surface,
                    rank,
                    checked_count,
                    post_title,
                    post_url,
                    collected_at,
                    created_at
                FROM rank_history
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [dict(row) for row in rows]

    def trend(self, keyword: str, *, limit: int = 200) -> list[dict[str, Any]]:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise ValueError("keyword must not be empty")

        limit = max(1, min(limit, 500))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM (
                    SELECT
                        id,
                        keyword,
                        target_blog_id,
                        surface,
                        rank,
                        checked_count,
                        post_title,
                        post_url,
                        collected_at,
                        created_at
                    FROM rank_history
                    WHERE keyword = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                ORDER BY created_at ASC, id ASC
                """,
                (normalized_keyword, limit),
            ).fetchall()

        return [dict(row) for row in rows]

    def watch_keywords(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, keyword, enabled, created_at
                FROM watch_keywords
                WHERE enabled = 1
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def watch_keyword_summaries(self) -> list[dict[str, Any]]:
        keywords = self.watch_keywords()
        with self.connect() as connection:
            for keyword in keywords:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM (
                        SELECT
                            id,
                            keyword,
                            target_blog_id,
                            surface,
                            rank,
                            checked_count,
                            post_title,
                            post_url,
                            collected_at,
                            created_at
                        FROM rank_history
                        WHERE keyword = ?
                        ORDER BY created_at DESC, id DESC
                        LIMIT 50
                    )
                    ORDER BY created_at DESC, id DESC
                    """,
                    (keyword["keyword"],),
                ).fetchall()

                latest_by_surface: dict[str, dict[str, Any]] = {}
                previous_by_surface: dict[str, dict[str, Any]] = {}
                for row in rows:
                    item = dict(row)
                    surface = item["surface"]
                    if surface not in latest_by_surface:
                        latest_by_surface[surface] = item
                        continue
                    if surface not in previous_by_surface:
                        previous_by_surface[surface] = item

                keyword["latest_results"] = list(latest_by_surface.values())
                keyword["previous_results"] = list(previous_by_surface.values())
                keyword["changes"] = [
                    rank_change(surface, latest_by_surface[surface], previous_by_surface.get(surface))
                    for surface in latest_by_surface
                ]
                latest_times = [
                    item["created_at"]
                    for item in latest_by_surface.values()
                    if item.get("created_at")
                ]
                keyword["last_checked_at"] = max(latest_times) if latest_times else None

        return keywords

    def add_watch_keyword(self, keyword: str) -> dict[str, Any]:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise ValueError("keyword must not be empty")

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO watch_keywords (keyword)
                VALUES (?)
                ON CONFLICT(keyword) DO UPDATE SET enabled = 1
                """,
                (normalized_keyword,),
            )
            row = connection.execute(
                """
                SELECT id, keyword, enabled, created_at
                FROM watch_keywords
                WHERE keyword = ?
                """,
                (normalized_keyword,),
            ).fetchone()

        assert row is not None
        return dict(row)

    def delete_watch_keyword(self, keyword_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE watch_keywords
                SET enabled = 0
                WHERE id = ? AND enabled = 1
                """,
                (keyword_id,),
            )

        return cursor.rowcount > 0

    def add_my_post(
        self,
        *,
        url: str,
        title: str = "",
        keywords: list[str] | None = None,
        category: str = "",
        published_at: str = "",
        content_summary: str = "",
        content_text: str = "",
        imported_at: str = "",
    ) -> dict[str, Any]:
        normalized_url = canonicalize_naver_blog_url(url.strip())
        if not normalized_url:
            raise ValueError("url must not be empty")

        normalized_title = title.strip() or normalized_url
        normalized_category = category.strip()
        normalized_published_at = published_at.strip()
        normalized_summary = content_summary.strip()
        normalized_content_text = content_text.strip()
        normalized_imported_at = imported_at.strip()
        normalized_keywords = [
            keyword.strip()
            for keyword in (keywords or [])
            if keyword.strip()
        ]

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO my_posts (
                    title,
                    url,
                    blog_id,
                    post_id,
                    category,
                    published_at,
                    content_summary,
                    content_text,
                    content_length,
                    imported_at,
                    content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    blog_id = excluded.blog_id,
                    post_id = excluded.post_id,
                    category = excluded.category,
                    published_at = excluded.published_at,
                    content_summary = excluded.content_summary,
                    content_text = excluded.content_text,
                    content_length = excluded.content_length,
                    imported_at = excluded.imported_at,
                    enabled = 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    normalized_title,
                    normalized_url,
                    blog_id_from_post_url(normalized_url),
                    post_id_from_post_url(normalized_url),
                    normalized_category,
                    normalized_published_at,
                    normalized_summary,
                    normalized_content_text,
                    len(normalized_content_text),
                    normalized_imported_at,
                ),
            )
            post = connection.execute(
                """
                SELECT id, title, url, enabled, created_at
                FROM my_posts
                WHERE url = ?
                """,
                (normalized_url,),
            ).fetchone()
            assert post is not None
            post_id = int(post["id"])
            for keyword in normalized_keywords:
                self._add_post_keyword(connection, post_id, keyword, "target")
            self._refresh_post_content_hash(connection, post_id)

        return self.my_post(post_id) or dict(post)

    def update_my_post(
        self,
        post_id: int,
        *,
        url: str | None = None,
        title: str | None = None,
        category: str | None = None,
        published_at: str | None = None,
        content_summary: str | None = None,
        content_text: str | None = None,
        imported_at: str | None = None,
        keywords: list[str] | None = None,
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, url, category, published_at, content_summary, content_text, imported_at
                FROM my_posts
                WHERE id = ? AND enabled = 1
                """,
                (post_id,),
            ).fetchone()
            if row is None:
                return None

            next_url = canonicalize_naver_blog_url(url.strip()) if url is not None else row["url"]
            if not next_url:
                raise ValueError("url must not be empty")
            next_title = title.strip() if title is not None else row["title"]
            if not next_title:
                next_title = next_url
            next_category = category.strip() if category is not None else row["category"]
            next_published_at = published_at.strip() if published_at is not None else row["published_at"]
            next_summary = content_summary.strip() if content_summary is not None else row["content_summary"]
            next_content_text = content_text.strip() if content_text is not None else row["content_text"]
            next_imported_at = imported_at.strip() if imported_at is not None else row["imported_at"]

            connection.execute(
                """
                UPDATE my_posts
                SET title = ?,
                    url = ?,
                    blog_id = ?,
                    post_id = ?,
                    category = ?,
                    published_at = ?,
                    content_summary = ?,
                    content_text = ?,
                    content_length = ?,
                    imported_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND enabled = 1
                """,
                (
                    next_title,
                    next_url,
                    blog_id_from_post_url(next_url),
                    post_id_from_post_url(next_url),
                    next_category,
                    next_published_at,
                    next_summary,
                    next_content_text,
                    len(next_content_text),
                    next_imported_at,
                    post_id,
                ),
            )

            if keywords is not None:
                connection.execute(
                    "UPDATE post_keywords SET enabled = 0 WHERE post_id = ?",
                    (post_id,),
                )
                for keyword in keywords:
                    self._add_post_keyword(connection, post_id, keyword, "target")

            self._refresh_post_content_hash(connection, post_id)

        return self.my_post(post_id)

    def my_post(self, post_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    title,
                    url,
                    blog_id,
                    post_id,
                    category,
                    published_at,
                    content_summary,
                    content_text,
                    content_length,
                    content_hash,
                    imported_at,
                    enabled,
                    created_at,
                    updated_at
                FROM my_posts
                WHERE id = ? AND enabled = 1
                """,
                (post_id,),
            ).fetchone()
            if row is None:
                return None
            post = dict(row)
            post["keywords"] = self._post_keywords(connection, post_id)

        return post

    def my_post_summaries(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    url,
                    blog_id,
                    post_id,
                    category,
                    published_at,
                    content_summary,
                    content_text,
                    content_length,
                    content_hash,
                    imported_at,
                    enabled,
                    created_at,
                    updated_at
                FROM my_posts
                WHERE enabled = 1
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

            posts = []
            for row in rows:
                post = dict(row)
                post["keywords"] = self._post_keywords(connection, int(post["id"]))
                post["keyword_summaries"] = [
                    self._post_keyword_summary(connection, int(post["id"]), keyword["keyword"])
                    for keyword in post["keywords"]
                ]
                posts.append(post)

        return sorted(posts, key=post_summary_sort_key, reverse=True)

    def owner_post_contexts(self, *, limit: int = 1000) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 2000))
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    title,
                    url,
                    category,
                    published_at,
                    content_summary,
                    content_text
                FROM my_posts
                WHERE enabled = 1
                ORDER BY imported_at DESC, created_at DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

            posts = []
            for row in rows:
                post = dict(row)
                post["keywords"] = [
                    item["keyword"]
                    for item in self._post_keywords(connection, int(post["id"]))
                ]
                posts.append(post)

        return posts

    def _post_keywords(self, connection: sqlite3.Connection, post_id: int) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT id, keyword, keyword_type, enabled, created_at
            FROM post_keywords
            WHERE post_id = ? AND enabled = 1
            ORDER BY created_at ASC, id ASC
            """,
            (post_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _post_keyword_summary(
        self,
        connection: sqlite3.Connection,
        post_id: int,
        keyword: str,
    ) -> dict[str, Any]:
        rows = connection.execute(
            """
            SELECT *
            FROM (
                SELECT
                    id,
                    post_id,
                    keyword,
                    surface,
                    rank,
                    checked_count,
                    result_url,
                    matched_title,
                    matched_url,
                    collected_at,
                    created_at
                FROM post_rank_history
                WHERE post_id = ? AND keyword = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 50
            )
            ORDER BY created_at DESC, id DESC
            """,
            (post_id, keyword),
        ).fetchall()

        latest_by_surface: dict[str, dict[str, Any]] = {}
        previous_by_surface: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            surface = item["surface"]
            if surface not in latest_by_surface:
                latest_by_surface[surface] = item
                continue
            if surface not in previous_by_surface:
                previous_by_surface[surface] = item

        changes = [
            rank_change(surface, latest_by_surface[surface], previous_by_surface.get(surface))
            for surface in latest_by_surface
        ]
        latest_times = [
            item["created_at"]
            for item in latest_by_surface.values()
            if item.get("created_at")
        ]

        return {
            "keyword": keyword,
            "latest_results": list(latest_by_surface.values()),
            "previous_results": list(previous_by_surface.values()),
            "changes": changes,
            "last_checked_at": max(latest_times) if latest_times else None,
        }

    def add_post_keyword(
        self,
        post_id: int,
        keyword: str,
        keyword_type: str = "target",
    ) -> dict[str, Any] | None:
        with self.connect() as connection:
            post_exists = connection.execute(
                "SELECT id FROM my_posts WHERE id = ? AND enabled = 1",
                (post_id,),
            ).fetchone()
            if post_exists is None:
                return None
            row = self._add_post_keyword(connection, post_id, keyword, keyword_type)
            self._refresh_post_content_hash(connection, post_id)
            return dict(row)

    def _add_post_keyword(
        self,
        connection: sqlite3.Connection,
        post_id: int,
        keyword: str,
        keyword_type: str,
    ) -> sqlite3.Row:
        normalized_keyword = keyword.strip()
        if not normalized_keyword:
            raise ValueError("keyword must not be empty")
        normalized_type = keyword_type.strip() or "target"
        connection.execute(
            """
            INSERT INTO post_keywords (post_id, keyword, keyword_type)
            VALUES (?, ?, ?)
            ON CONFLICT(post_id, keyword) DO UPDATE SET
                keyword_type = excluded.keyword_type,
                enabled = 1
            """,
            (post_id, normalized_keyword, normalized_type),
        )
        row = connection.execute(
            """
            SELECT id, keyword, keyword_type, enabled, created_at
            FROM post_keywords
            WHERE post_id = ? AND keyword = ?
            """,
            (post_id, normalized_keyword),
        ).fetchone()
        assert row is not None
        return row

    def delete_post_keyword(self, post_id: int, keyword_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE post_keywords
                SET enabled = 0
                WHERE id = ? AND post_id = ? AND enabled = 1
                """,
                (keyword_id, post_id),
            )
            if cursor.rowcount:
                self._refresh_post_content_hash(connection, post_id)

        return cursor.rowcount > 0

    def import_my_blog_posts(
        self,
        posts: list[ImportedBlogPost],
        *,
        update_existing: bool = True,
    ) -> dict[str, Any]:
        created_count = 0
        updated_count = 0
        skipped_count = 0
        imported_ids: list[int] = []

        for post in posts:
            existed = self._post_exists_by_url(post.url)
            if existed and not update_existing:
                skipped_count += 1
                continue
            item = self.add_my_post(
                url=post.url,
                title=post.title,
                category=post.category,
                published_at=post.published_at,
                content_summary=post.content_summary,
                content_text=post.content_text,
                imported_at=post.imported_at,
            )
            imported_ids.append(int(item["id"]))
            if existed:
                updated_count += 1
            else:
                created_count += 1

        return {
            "imported_count": len(imported_ids),
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "post_ids": imported_ids,
        }

    def _post_exists_by_url(self, url: str) -> bool:
        normalized_url = canonicalize_naver_blog_url(url.strip())
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM my_posts WHERE url = ?",
                (normalized_url,),
            ).fetchone()
        return row is not None

    def save_post_rank_results(self, post_id: int, results: list[BlogRankResult]) -> None:
        if not results:
            return

        rows = []
        for result in results:
            rows.append(
                (
                    post_id,
                    result.keyword,
                    result.surface,
                    result.rank,
                    result.checked_count,
                    result.result_url,
                    result.post.title if result.post else None,
                    result.post.url if result.post else None,
                    result.collected_at,
                )
            )

        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO post_rank_history (
                    post_id,
                    keyword,
                    surface,
                    rank,
                    checked_count,
                    result_url,
                    matched_title,
                    matched_url,
                    collected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def delete_my_post(self, post_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE my_posts
                SET enabled = 0
                WHERE id = ? AND enabled = 1
                """,
                (post_id,),
            )

        return cursor.rowcount > 0

    def _refresh_post_content_hash(self, connection: sqlite3.Connection, post_id: int) -> None:
        row = connection.execute(
            """
            SELECT url, title, category, published_at, content_summary, content_text
            FROM my_posts
            WHERE id = ?
            """,
            (post_id,),
        ).fetchone()
        if row is None:
            return

        keywords = [
            item["keyword"]
            for item in self._post_keywords(connection, post_id)
        ]
        content_hash = self._content_hash(
            url=row["url"],
            title=row["title"],
            category=row["category"],
            published_at=row["published_at"],
            content_summary=row["content_summary"],
            content_text=row["content_text"],
            keywords=keywords,
        )
        connection.execute(
            """
            UPDATE my_posts
            SET content_hash = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (content_hash, post_id),
        )

    def _content_hash(
        self,
        *,
        url: str,
        title: str,
        category: str,
        published_at: str,
        content_summary: str,
        content_text: str,
        keywords: list[str],
    ) -> str:
        material = "\n".join(
            [
                url.strip(),
                title.strip(),
                category.strip(),
                published_at.strip(),
                content_summary.strip(),
                content_text.strip(),
                *sorted(keyword.strip() for keyword in keywords if keyword.strip()),
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


def post_id_from_post_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc in {"blog.naver.com", "m.blog.naver.com"} and len(parts) >= 2:
        return parts[1] if parts[1].isdigit() else ""
    return ""


def post_summary_sort_key(post: dict[str, Any]) -> tuple[str, str, int]:
    imported_at = str(post.get("imported_at") or "")
    created_at = str(post.get("created_at") or "")
    fallback_at = max(imported_at, created_at)
    published_at = parse_post_datetime(str(post.get("published_at") or ""), base=parse_post_datetime(fallback_at))
    return (
        published_at.isoformat() if published_at else fallback_at,
        fallback_at,
        int(post.get("id") or 0),
    )


def parse_post_datetime(value: str, *, base: datetime | None = None) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    normalized = normalized.replace("작성", "").strip()

    relative_match = re.fullmatch(r"(\d+)\s*(초|분|시간|일)\s*전", normalized)
    if relative_match:
        anchor = base or datetime.now()
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit == "초":
            return anchor - timedelta(seconds=amount)
        if unit == "분":
            return anchor - timedelta(minutes=amount)
        if unit == "시간":
            return anchor - timedelta(hours=amount)
        return anchor - timedelta(days=amount)

    if normalized == "어제":
        anchor = base or datetime.now()
        return anchor - timedelta(days=1)

    candidates = [
        normalized,
        normalized.replace(".", "-"),
        re.sub(r"\.\s*", "-", normalized).strip("- "),
        re.sub(r"\s+", " ", normalized),
    ]
    formats = (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y. %m. %d. %H:%M",
        "%Y. %m. %d.",
        "%Y. %m. %d",
        "%Y. %m. %d. %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y.%m.%d. %H:%M",
        "%Y.%m.%d.",
        "%Y.%m.%d",
    )
    for candidate in candidates:
        candidate = candidate.strip()
        for date_format in formats:
            try:
                return datetime.strptime(candidate, date_format)
            except ValueError:
                continue
    return None


def store_from_data_dir(data_dir: Path | str) -> RankHistoryStore:
    return RankHistoryStore(Path(data_dir) / "bms.sqlite3")
