import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def login_and_save_state(auth_file: str = "data/auth_state.json"):
    """
    Opens a headful browser session to allow manual login to LinkedIn.
    Once successful, it saves the browser state (cookies, local storage) to a file
    so subsequent headless scrapes don't need to log in again.
    """
    Path(auth_file).parent.mkdir(parents=True, exist_ok=True)
    
    print("Starting Playwright for manual authentication...")
    async with async_playwright() as p:
        # We always want headful for manual login
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Apply stealth to evade basic bot detection even during login
        await stealth_async(page)
        
        await page.goto("https://www.linkedin.com/login")
        print(">>> Please log in using the browser window. <<<")
        print("Waiting for you to reach the LinkedIn feed...")
        
        # Wait indefinitely for the feed page which indicates successful login
        await page.wait_for_url("**/feed/*", timeout=0)
        
        # Save state
        await context.storage_state(path=auth_file)
        print(f"Login successful. Session state saved to '{auth_file}'")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_and_save_state())
