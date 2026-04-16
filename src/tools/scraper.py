import asyncio
import random
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

class LinkedinScraper:
    def __init__(self, auth_file: str = "data/auth_state.json", headless: bool = None):
        self.auth_file = auth_file
        if headless is None:
            self.headless = os.getenv("HEADLESS", "false").lower() == "true"
        else:
            self.headless = headless

    async def _simulated_mouse_move(self, page):
        """Simulate realistic, non-linear mouse movements."""
        start_x = random.randint(100, 800)
        start_y = random.randint(100, 500)
        target_x = random.randint(200, 900)
        target_y = random.randint(200, 800)
        
        steps = random.randint(10, 20)
        for i in range(steps):
            t = i / steps
            current_x = start_x + (target_x - start_x) * t + random.uniform(-15, 15)
            current_y = start_y + (target_y - start_y) * t + random.uniform(-15, 15)
            await page.mouse.move(current_x, current_y)
            await asyncio.sleep(random.uniform(0.01, 0.05))
        
        await page.mouse.move(target_x, target_y)

    async def _human_scroll(self, page, max_scrolls=5):
        """Scrolls down page progressively to trigger lazy loading."""
        try:
            total_height = await page.evaluate("document.body.scrollHeight")
        except:
            total_height = 3000
            
        current_scroll = 0
        scroll_count = 0
        
        while current_scroll < total_height and scroll_count < max_scrolls:
            scroll_step = random.randint(400, 800)
            current_scroll += scroll_step
            scroll_count += 1
            
            await self._simulated_mouse_move(page)
            await page.mouse.wheel(delta_x=0, delta_y=scroll_step)
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            try:
                new_height = await page.evaluate("document.body.scrollHeight")
                total_height = new_height
            except:
                pass

    async def _click_see_more(self, page):
        """Finds and clicks 'See more' to expand text."""
        try:
            locators = ["button:has-text('see more')", "button:has-text('Show all')", "button:has-text('see all')"]
            for loc in locators:
                buttons = await page.locator(loc).all()
                for button in buttons:
                    if await button.is_visible():
                        await self._simulated_mouse_move(page)
                        await button.click()
                        await asyncio.sleep(random.uniform(1.0, 2.0))
        except Exception:
            pass

    async def _clean_dom(self, page):
        """Removes noisy UI elements like navbars, footers locally to clean data for LLM."""
        try:
            await page.evaluate("""
                () => {
                    const selectors = [
                        'header', '#global-nav', 'nav', 'footer', 
                        '.msg-overlay-list-bubble', 
                        'aside', '.scaffold-layout__aside', // right sidebars
                        '.pv-recommendations-section', // People you may know
                        '.artdeco-toast-item' // alerts
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                }
            """)
        except Exception:
            pass

    async def _extract_subpage(self, page, url: str, section_name: str, deep_scroll=False) -> str:
        """Navigates to a specific subpage, safely cleans it, and extracts the core text."""
        print(f"Fetching [{section_name}] -> {url} ...")
        await page.goto(url)
        await self._simulated_mouse_move(page)
        await asyncio.sleep(random.uniform(2.0, 3.5))
        
        max_scrolls = 6 if deep_scroll else 3
        await self._human_scroll(page, max_scrolls=max_scrolls)
        await self._click_see_more(page)
        
        print(f"Cleaning UI noise for {section_name}...")
        await self._clean_dom(page)
        
        if "overlay" in url:
            locator = page.locator(".artdeco-modal__content, .pv-contact-info")
        else:
            locator = page.locator("main.scaffold-layout__main")
            
        if await locator.count() > 0:
            text = await locator.first.inner_text()
        else:
            text = await page.locator("body").inner_text()
            
        return text.strip()


    async def scrape_full_profile(self, profile_url: str) -> dict:
        """Scrapes the main profile and deeply iterates through all detailed sections."""
        if not Path(self.auth_file).exists():
            raise FileNotFoundError(f"Auth file missing at {self.auth_file}. Run login.py.")

        if not profile_url.endswith("/"):
            profile_url += "/"

        extracted_data = {}

        async with async_playwright() as p:
            print(f"Launching browser (Headless: {self.headless})...")
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                storage_state=self.auth_file,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            endpoints = {
                "Main Profile": "",
                "Contact Info": "overlay/contact-info/",
                "Experience": "details/experience/",
                "Education": "details/education/",
                "Projects": "details/projects/",
                "Skills": "details/skills/",
                "Certifications": "details/certifications/",
                "Recent Posts": "recent-activity/all/",
            }
            
            for section, subpath in endpoints.items():
                deep = section in ["Recent Posts", "Main Profile"]
                target_url = profile_url + subpath
                
                try:
                    text = await self._extract_subpage(page, target_url, section, deep_scroll=deep)
                    if text:
                        extracted_data[section] = text
                except Exception as e:
                    print(f"Failed to fetch {section}: {e}")
                    extracted_data[section] = f"ERROR: {e}"

            await browser.close()
            return extracted_data

    async def scrape_full_company(self, company_url: str) -> dict:
        """Scrapes company 'About' and 'Posts'."""
        if not Path(self.auth_file).exists():
            raise FileNotFoundError(f"Auth file missing at {self.auth_file}. Run login.py.")

        if not company_url.endswith("/"):
            company_url += "/"

        extracted_data = {}

        async with async_playwright() as p:
            print(f"Launching browser (Headless: {self.headless})...")
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context(
                storage_state=self.auth_file,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            endpoints = {
                "About": "about/",
                "Posts": "posts/?feedView=all"
            }
            
            for section, subpath in endpoints.items():
                target_url = company_url + subpath
                try:
                    text = await self._extract_subpage(page, target_url, section, deep_scroll=(section == "Posts"))
                    if text:
                        extracted_data[section] = text
                except Exception as e:
                    print(f"Failed to fetch {section}: {e}")
                    extracted_data[section] = f"ERROR: {e}"

            await browser.close()
            return extracted_data

if __name__ == "__main__":
    async def test():
        scraper = LinkedinScraper()
        url = input("Enter LinkedIn URL (Profile or Company): ").strip()
        
        try:
            if "/company/" in url:
                print("Detected COMPANY URL...")
                data = await scraper.scrape_full_company(url)
                label = "COMPANY"
                filename = "data/company_extracted"
            else:
                print("Detected PROFILE URL...")
                data = await scraper.scrape_full_profile(url)
                label = "PROFILE"
                filename = "data/raw_extracted"
            
            print("\n" + "="*50)
            print(f"{label} EXTRACTION SUCCESSFUL")
            print("="*50)
            
            out_text = []
            for sec, content in data.items():
                out_text.append(f"====== {sec.upper()} ======\n{content}\n")
            
            final_output = "\n".join(out_text)
            print(final_output[:1000] + "\n... (truncated for terminal) ...\n")
            
            out_file = Path(f"{filename}.txt")
            out_file.parent.mkdir(exist_ok=True, parents=True)
            out_file.write_text(final_output, encoding="utf-8")
            
            # Save JSON for programmatic access
            out_json = Path(f"{filename}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            print(f"-> Full text data saved to {out_file}")
            print(f"-> Full JSON data saved to {out_json}")
            
        except Exception as e:
            print(f"Scraping failed: {e}")
            
    asyncio.run(test())
