import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def login_and_save_state(auth_file: str = "data/auth_state.json"):
    """
    Opens a headful browser session to allow manual login to LinkedIn.
    Once successful, it saves the browser state (cookies, local storage) to a file
    so subsequent headless scrapes don't need to log in again.
    """
    Path(auth_file).parent.mkdir(parents=True, exist_ok=True)
    
    print("Starting Playwright with persistent context...")
    async with async_playwright() as p:
        # Use a local directory for user data to look more like a real browser
        user_data_dir = "/tmp/linkedin_profile"
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Apply stealth
        await Stealth().apply_stealth_async(page)
        
        await page.goto("https://www.linkedin.com/login")
        print(">>> Please log in manually. <<<")
        
        # Wait for feed
        try:
            await page.wait_for_url("**/feed/*", timeout=0)
            # Save state to our shared file
            await context.storage_state(path=auth_file)
            print(f"Login successful. Session saved to '{auth_file}'")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_state())
