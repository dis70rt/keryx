import asyncio
import random
import os
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

class LinkedinScraper:
    def __init__(self, auth_file: str = "data/auth_state.json", headless: bool = None):
        self.auth_file = auth_file
        # Automatically use headless mode if running in Docker production
        if headless is None:
            self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        else:
            self.headless = headless

    async def _human_scroll(self, page):
        """Scrolls down the page randomly to mimic human reading."""
        scrolls = random.randint(3, 7)
        for _ in range(scrolls):
            scroll_y = random.randint(300, 700)
            await page.mouse.wheel(delta_x=0, delta_y=scroll_y)
            await asyncio.sleep(random.uniform(0.5, 2.0))

    async def _click_see_more(self, page):
        """Attempts to click 'See more' buttons to expand text sections before extracting."""
        try:
            # Look for common expansion phrases
            locators = ["button:has-text('see more')", "button:has-text('Show all')"]
            for loc in locators:
                buttons = await page.locator(loc).all()
                for button in buttons:
                    if await button.is_visible():
                        await button.click()
                        await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            # Continue even if clicking fails
            pass

    async def scrape_profile(self, profile_url: str) -> str:
        """
        Scrapes the given LinkedIn profile URL. Extracts raw text for LLM processing.
        """
        if not Path(self.auth_file).exists():
            raise FileNotFoundError(f"Auth file missing at {self.auth_file}. Please run login.py first.")

        async with async_playwright() as p:
            print(f"Launching browser (Headless: {self.headless})...")
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(storage_state=self.auth_file)
            page = await context.new_page()
            
            # Apply stealth plugins
            await stealth_async(page)
            
            # Perform a randomized initial delay
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            print(f"Navigating to {profile_url}...")
            await page.goto(profile_url)
            
            # Wait for main layout container
            try:
                await page.wait_for_selector("main.scaffold-layout__main", timeout=15000)
            except Exception:
                print("Main layout took too long, proceeding anyway...")

            # Mimic a human reading the profile
            await self._human_scroll(page)
            await self._click_see_more(page)
            await self._human_scroll(page)
            
            print("Extracting raw profile text for LLM processing...")
            # Extract raw text from the main profile container; fallback to body.
            main_locator = page.locator("main.scaffold-layout__main")
            if await main_locator.count() > 0:
                raw_text = await main_locator.inner_text()
            else:
                raw_text = await page.locator("body").inner_text()
            
            await browser.close()
            return raw_text

if __name__ == "__main__":
    async def test():
        scraper = LinkedinScraper()
        url = input("Enter LinkedIn profile URL to test scrape: ")
        
        try:
            text = await scraper.scrape_profile(url)
            print("\n" + "="*50)
            print("EXTRACTION SUCCESSFUL")
            print("="*50)
            print(text[:1000] + "\n...\n")
            print(f"[Total extracted characters: {len(text)}]")
        except Exception as e:
            print(f"Scraping failed: {e}")
            
    asyncio.run(test())
