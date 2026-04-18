import asyncio
import json
import random
from pathlib import Path

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.tools.human_behavior import human_scroll, simulated_mouse_move


class LinkedinScraper:
    def __init__(self, auth_file: Path = Path("data/auth_state.json"), headless: bool = False) -> None:
        self.auth_file = auth_file
        self.headless = headless

    async def _click_see_more(self, page) -> None:
        try:
            locators = [
                "button:has-text('see more')",
                "button:has-text('Show all')",
                "button:has-text('see all')",
            ]
            for loc in locators:
                buttons = await page.locator(loc).all()
                for button in buttons:
                    if await button.is_visible():
                        await simulated_mouse_move(page)
                        await button.click()
                        await asyncio.sleep(random.uniform(1.0, 2.0))
        except Exception:
            pass

    async def _clean_dom(self, page) -> None:
        try:
            await page.evaluate("""
                () => {
                    const selectors = [
                        'header', '#global-nav', 'nav', 'footer',
                        '.msg-overlay-list-bubble',
                        'aside', '.scaffold-layout__aside',
                        '.pv-recommendations-section',
                        '.artdeco-toast-item'
                    ];
                    selectors.forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                }
            """)
        except Exception:
            pass

    async def _extract_subpage(
        self, page, url: str, section_name: str, deep_scroll: bool = False
    ) -> str:
        print(f"  → Fetching [{section_name}] {url}")
        await page.goto(url)
        await simulated_mouse_move(page)
        await asyncio.sleep(random.uniform(2.0, 3.5))

        max_scrolls = 6 if deep_scroll else 3
        await human_scroll(page, max_scrolls=max_scrolls)
        await self._click_see_more(page)
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

    async def get_sender_profile(self, sender_url: str, cache_path: Path) -> dict[str, str]:
        """Fetch sender's own LinkedIn profile, using local cache if available."""
        if cache_path.exists():
            print(f"  ► Loading sender profile from cache: {cache_path}")
            return json.loads(cache_path.read_text(encoding="utf-8"))

        print(f"  ► Sender profile cache not found. Scraping target: {sender_url}")
        data = await self.scrape_full_profile(sender_url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ Cached sender profile to: {cache_path}")
        return data

    async def scrape_full_profile(self, profile_url: str) -> dict[str, str]:
        """Scrape all sections of a LinkedIn personal profile."""
        if not self.auth_file.exists():
            print(f"  ► Auth file missing at {self.auth_file}. Starting manual login...")
            from src.tools.login import login_and_save_state
            await login_and_save_state(self.auth_file)

        if not profile_url.endswith("/"):
            profile_url += "/"

        extracted_data: dict[str, str] = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                storage_state=str(self.auth_file),
                viewport={"width": 1280, "height": 800},
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
                    text = await self._extract_subpage(
                        page, target_url, section, deep_scroll=deep
                    )
                    if text:
                        extracted_data[section] = text
                except Exception as e:
                    print(f"  ✗ Failed to fetch {section}: {e}")
                    extracted_data[section] = f"ERROR: {e}"

            await browser.close()
            return extracted_data

    async def scrape_full_company(self, company_url: str) -> dict[str, str]:
        """Scrape About and Posts from a LinkedIn company page."""
        if not self.auth_file.exists():
            print(f"  ► Auth file missing at {self.auth_file}. Starting manual login...")
            from src.tools.login import login_and_save_state
            await login_and_save_state(self.auth_file)

        if not company_url.endswith("/"):
            company_url += "/"

        extracted_data: dict[str, str] = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                storage_state=str(self.auth_file),
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            endpoints = {"About": "about/", "Posts": "posts/?feedView=all"}

            for section, subpath in endpoints.items():
                target_url = company_url + subpath
                try:
                    text = await self._extract_subpage(
                        page, target_url, section, deep_scroll=(section == "Posts")
                    )
                    if text:
                        extracted_data[section] = text
                except Exception as e:
                    print(f"  ✗ Failed to fetch {section}: {e}")
                    extracted_data[section] = f"ERROR: {e}"

            await browser.close()
            return extracted_data
