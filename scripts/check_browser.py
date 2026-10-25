import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.browser_helper import BrowserSettings, open_page


def _summarize_error(exc: Exception) -> str:
    lines = str(exc).splitlines()
    missing_library = next((line for line in lines if "error while loading shared libraries" in line), None)
    if missing_library:
        return missing_library.strip()
    return lines[0] if lines else exc.__class__.__name__


async def main() -> None:
    settings = BrowserSettings()
    try:
        title = await open_page(
            "data:text/html,<title>playwright-ok</title><h1>ok</h1>",
            settings=settings,
        )
    except Exception as exc:
        print("Playwright browser check failed.")
        print(f"Reason: {_summarize_error(exc)}")
        print("If the error mentions a missing shared library, run: sudo venv/bin/playwright install-deps chromium")
        raise SystemExit(1) from exc

    print(f"Playwright browser check passed: {title}")


if __name__ == "__main__":
    asyncio.run(main())
