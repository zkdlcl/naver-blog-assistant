import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

from core.browser_helper import (
    DEFAULT_USER_AGENT,
    BrowserSettings,
    build_extra_http_headers,
    build_launch_args,
    new_browser_context,
)


class BrowserSettingsTests(unittest.TestCase):
    def test_defaults_are_suitable_for_korean_portal_monitoring(self):
        settings = BrowserSettings()

        self.assertEqual(settings.browser_name, "chromium")
        self.assertTrue(settings.headless)
        self.assertEqual(settings.locale, "ko-KR")
        self.assertEqual(settings.timezone_id, "Asia/Seoul")
        self.assertEqual(settings.user_agent, DEFAULT_USER_AGENT)
        self.assertEqual(settings.viewport, {"width": 1366, "height": 768})

    def test_env_overrides_headless_and_user_agent(self):
        with patch.dict(
            os.environ,
            {
                "BROWSER_HEADLESS": "false",
                "BROWSER_USER_AGENT": "Custom UA",
                "BROWSER_VIEWPORT_WIDTH": "390",
                "BROWSER_VIEWPORT_HEIGHT": "844",
            },
            clear=False,
        ):
            settings = BrowserSettings()

        self.assertFalse(settings.headless)
        self.assertEqual(settings.user_agent, "Custom UA")
        self.assertEqual(settings.viewport, {"width": 390, "height": 844})


class BrowserContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_browser_context_applies_headers_and_timeouts(self):
        browser = Mock()
        context = Mock()
        context.set_default_navigation_timeout = Mock()
        context.set_default_timeout = Mock()
        browser.new_context = AsyncMock(return_value=context)
        settings = BrowserSettings()

        result = await new_browser_context(browser, settings)

        self.assertIs(result, context)
        browser.new_context.assert_awaited_once_with(
            user_agent=settings.user_agent,
            locale=settings.locale,
            timezone_id=settings.timezone_id,
            viewport=settings.viewport,
            extra_http_headers=build_extra_http_headers(),
            storage_state=None,
        )
        context.set_default_navigation_timeout.assert_called_once_with(settings.navigation_timeout_ms)
        context.set_default_timeout.assert_called_once_with(settings.navigation_timeout_ms)


class BrowserFingerprintTests(unittest.TestCase):
    def test_chromium_launch_args_include_basic_container_flags(self):
        args = build_launch_args()

        self.assertIn("--disable-dev-shm-usage", args)
        self.assertIn("--no-sandbox", args)

    def test_accept_language_prefers_korean(self):
        headers = build_extra_http_headers()

        self.assertIn("ko-KR", headers["Accept-Language"])


if __name__ == "__main__":
    unittest.main()
