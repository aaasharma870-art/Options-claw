"""Interactive selector discovery tool.

Launches a browser pointed at Option Alpha so you can inspect the UI
and record CSS selectors for ui_selectors.json.

Usage:
    python selector_discovery.py                    # Opens OA login page
    python selector_discovery.py /bots              # Opens bots page
    python selector_discovery.py /bots/12345        # Opens specific bot

How to use:
1. The browser opens with Playwright Inspector
2. Navigate to the page you want to map
3. Click elements — the inspector shows their selectors
4. Copy selectors into ui_selectors.json
5. Close the browser when done
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import OA_BASE_URL, SESSION_COOKIES_PATH


async def discover(path: str = "/"):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed. Run:")
        print("  pip install playwright && playwright install chromium")
        return

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})

        # Restore cookies if available
        if SESSION_COOKIES_PATH.exists():
            import json
            cookies = json.loads(SESSION_COOKIES_PATH.read_text())
            await context.add_cookies(cookies)
            print(f"Loaded {len(cookies)} session cookies")

        page = await context.new_page()

        url = f"{OA_BASE_URL}{path}" if path.startswith("/") else path
        print(f"Navigating to: {url}")
        await page.goto(url)

        print("\nPlaywright Inspector is open.")
        print("- Click elements to see their selectors")
        print("- Use the 'Pick locator' button (crosshair icon)")
        print("- Copy selectors into tier2_playwright/ui_selectors.json")
        print("- Close the browser when done\n")

        await page.pause()  # Opens interactive inspector

        # Save cookies after session
        cookies = await context.cookies()
        SESSION_COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        import json
        SESSION_COOKIES_PATH.write_text(json.dumps(cookies, indent=2))
        print("Session cookies saved")

        await browser.close()


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/"
    asyncio.run(discover(path))


if __name__ == "__main__":
    main()
