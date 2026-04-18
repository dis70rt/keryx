import asyncio
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def login_and_save_state(auth_file: Path | str = "data/auth_state.json") -> None:
    """
    Open Playwright in headful mode (with a persistent context).
    Allow the user to log in manually, then save state to `auth_file`.
    """
    auth_path = Path(auth_file)
    auth_path.parent.mkdir(parents=True, exist_ok=True)

    print("  ► Starting Playwright with persistent context for login...")
    async with async_playwright() as p:
        # Use a local directory for user data
        user_data_dir = "/tmp/linkedin_profile"
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        await Stealth().apply_stealth_async(page)

        await page.goto("https://www.linkedin.com/login")
        print("  ► >>> Please log in manually in the opened browser window. <<<")

        try:
            # Wait until we see evidence of successful login (like the feed URL)
            await page.wait_for_url("**/feed/*", timeout=0)
            await context.storage_state(path=str(auth_path))
            print(f"  ✓ Login successful! Saved state to -> {auth_path}")
        finally:
            await context.close()


if __name__ == "__main__":
    asyncio.run(login_and_save_state())
