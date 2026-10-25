from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Sequence

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_VIEWPORT = {"width": 1366, "height": 768}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class BrowserSettings:
    browser_name: str = field(default_factory=lambda: os.getenv("BROWSER_NAME", "chromium"))
    headless: bool = field(default_factory=lambda: _env_bool("BROWSER_HEADLESS", True))
    slow_mo_ms: int = field(default_factory=lambda: int(os.getenv("BROWSER_SLOW_MO_MS", "0")))
    locale: str = field(default_factory=lambda: os.getenv("BROWSER_LOCALE", "ko-KR"))
    timezone_id: str = field(default_factory=lambda: os.getenv("BROWSER_TIMEZONE", "Asia/Seoul"))
    user_agent: str = field(default_factory=lambda: os.getenv("BROWSER_USER_AGENT", DEFAULT_USER_AGENT))
    navigation_timeout_ms: int = field(
        default_factory=lambda: int(os.getenv("BROWSER_NAVIGATION_TIMEOUT_MS", "30000"))
    )
    viewport_width: int = field(default_factory=lambda: int(os.getenv("BROWSER_VIEWPORT_WIDTH", "1366")))
    viewport_height: int = field(default_factory=lambda: int(os.getenv("BROWSER_VIEWPORT_HEIGHT", "768")))

    @property
    def viewport(self) -> dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}


@dataclass
class BrowserSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


def build_launch_args() -> list[str]:
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
    ]


def build_extra_http_headers() -> dict[str, str]:
    return {
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }


async def _launch_browser(playwright: Playwright, settings: BrowserSettings) -> Browser:
    browser_type = getattr(playwright, settings.browser_name, None)
    if browser_type is None:
        valid_names = "chromium, firefox, webkit"
        raise ValueError(f"Unsupported browser name: {settings.browser_name}. Use one of: {valid_names}.")

    return await browser_type.launch(
        headless=settings.headless,
        slow_mo=settings.slow_mo_ms,
        args=build_launch_args() if settings.browser_name == "chromium" else None,
    )


async def new_browser_context(
    browser: Browser,
    settings: BrowserSettings | None = None,
    *,
    storage_state: str | dict | None = None,
) -> BrowserContext:
    settings = settings or BrowserSettings()
    context = await browser.new_context(
        user_agent=settings.user_agent,
        locale=settings.locale,
        timezone_id=settings.timezone_id,
        viewport=settings.viewport,
        extra_http_headers=build_extra_http_headers(),
        storage_state=storage_state,
    )
    context.set_default_navigation_timeout(settings.navigation_timeout_ms)
    context.set_default_timeout(settings.navigation_timeout_ms)
    return context


@asynccontextmanager
async def browser_session(
    settings: BrowserSettings | None = None,
    *,
    storage_state: str | dict | None = None,
) -> AsyncIterator[BrowserSession]:
    settings = settings or BrowserSettings()
    playwright = await async_playwright().start()
    browser: Browser | None = None
    context: BrowserContext | None = None

    try:
        browser = await _launch_browser(playwright, settings)
        context = await new_browser_context(browser, settings, storage_state=storage_state)
        page = await context.new_page()
        yield BrowserSession(playwright=playwright, browser=browser, context=context, page=page)
    finally:
        if context is not None:
            await context.close()
        if browser is not None:
            await browser.close()
        await playwright.stop()


async def open_page(
    url: str,
    *,
    wait_until: str = "domcontentloaded",
    settings: BrowserSettings | None = None,
    storage_state: str | dict | None = None,
) -> str:
    async with browser_session(settings=settings, storage_state=storage_state) as session:
        await session.page.goto(url, wait_until=wait_until)
        return await session.page.title()


async def open_pages(
    urls: Sequence[str],
    *,
    wait_until: str = "domcontentloaded",
    settings: BrowserSettings | None = None,
    storage_state: str | dict | None = None,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    async with browser_session(settings=settings, storage_state=storage_state) as session:
        for url in urls:
            await session.page.goto(url, wait_until=wait_until)
            results.append((url, await session.page.title()))
    return results
