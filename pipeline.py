import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.core.config import load_settings
from src.core.models import SenderContext
from src.core.state import StateManager
from src.core.workflow import app as keryx_pipeline
from src.tools.context import load_projects, load_resume
from src.tools.scraper import LinkedinScraper
from src.tools.sheets import SheetsManager
from src.tools.cleaner import clean_scraped_data
from src.tools.snapshot import SnapshotManager


def build_sender_context(settings) -> SenderContext:
    """Load resume and projects context into a SenderContext instance."""
    resume_text = load_resume(settings.resume_path)
    projects_text = load_projects(settings.projects_path)

    return SenderContext(
        sender_name="Your Name",
        sender_current_status="CS Student | Backend Engineering",
        sender_core_competencies=[
            "Python", "Go", "Distributed Systems", "LangChain", "gRPC"
        ],
        sender_highlight_projects=["Keryx", "Bluppi", "WizFlow"],
        ask_type="Backend Engineering Internship",
        resume_text=resume_text,
        projects_context=projects_text,
    )


def run_ai_pipeline(
    raw_profile_text: str,
    sender_context: SenderContext,
    raw_company_text: str | None = None,
) -> dict[str, str]:
    """Execute the LangGraph pipeline and extract final messages."""
    initial_state = {
        "raw_profile_text": raw_profile_text,
        "raw_company_text": raw_company_text,
        "platform": "LinkedIn",
        "sender_context": sender_context,
        "revision_count": 0,
    }

    final_state = None
    for output in keryx_pipeline.stream(initial_state):
        final_state = output

    connection_note = ""
    dm_message = ""

    if final_state:
        last_node = list(final_state.values())[-1]
        connection_note = last_node.get("connection_note", "")
        dm_message = last_node.get("dm_message", "")

        if not connection_note or not dm_message:
            for output in keryx_pipeline.stream(initial_state):
                for node_data in output.values():
                    if node_data.get("connection_note"):
                        connection_note = node_data["connection_note"]
                    if node_data.get("dm_message"):
                        dm_message = node_data["dm_message"]

    return {"connection_note": connection_note, "dm_message": dm_message}


async def process_target(
    url: str,
    company_url: str | None,
    scraper: LinkedinScraper,
    sender_context: SenderContext,
    state_mgr: StateManager,
    snapshot_mgr: SnapshotManager,
) -> dict[str, str] | None:
    """Scrape a single profile and run the AI pipeline.

    Scraped data is persisted via *snapshot_mgr* so that a subsequent run
    (e.g. after an AI-pipeline failure) can skip the expensive Playwright
    scraping entirely.
    """
    if state_mgr.is_processed(url):
        print(f"  ⏭ Already processed: {url}")
        cached = state_mgr.get_cached_result(url)
        return cached

    print(f"\n{'='*60}")
    print(f"Processing: {url}")
    print(f"{'='*60}")

    try:
        # ── Profile scraping (with snapshot cache) ──────────────
        if snapshot_mgr.has_profile(url, company_url):
            print("▸ Loading profile from snapshot...")
            scraped = snapshot_mgr.load_profile(url, company_url)
        else:
            print("▸ Scraping profile...")
            scraped = await scraper.scrape_full_profile(url)
            saved_to = snapshot_mgr.save_profile(url, company_url, scraped)
            print(f"  ✓ Snapshot saved → {saved_to}")

        # ── Company scraping (with snapshot cache) ─────────────
        scraped_company = None
        if company_url:
            if snapshot_mgr.has_company(company_url):
                print(f"▸ Loading company profile from snapshot...")
                scraped_company = snapshot_mgr.load_company(company_url)
            else:
                print(f"▸ Scraping company profile: {company_url}")
                scraped_company = await scraper.scrape_full_company(company_url)
                saved_to = snapshot_mgr.save_company(company_url, scraped_company)
                print(f"  ✓ Snapshot saved → {saved_to}")

        # ── Algorithmic cleaning (strip LinkedIn UI noise) ─────
        print("▸ Cleaning scraped data...")
        cleaned_profile = clean_scraped_data(scraped)
        raw_text = "\n".join(
            [f"--- {k} ---\n{v}" for k, v in cleaned_profile.items()]
        )

        raw_company_text = None
        if scraped_company:
            cleaned_company = clean_scraped_data(scraped_company)
            raw_company_text = "\n".join(
                [f"--- {k} ---\n{v}" for k, v in cleaned_company.items()]
            )

        # ── AI pipeline ────────────────────────────────────────
        print("▸ Running AI pipeline...")
        result = run_ai_pipeline(raw_text, sender_context, raw_company_text)

        state_mgr.mark_success(
            url, result["connection_note"], result["dm_message"]
        )

        print(f"\n  ✓ Connection Note ({len(result['connection_note'])} chars):")
        print(f"    {result['connection_note'][:100]}...")
        print(f"  ✓ DM Message ({len(result['dm_message'].split())} words)")

        return result

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        state_mgr.mark_failed(url, str(e))
        return None


async def main() -> None:
    load_dotenv()
    settings = load_settings()

    print("╔══════════════════════════════════════╗")
    print("║       KERYX OUTREACH PIPELINE        ║")
    print("╚══════════════════════════════════════╝")

    sender_context = build_sender_context(settings)
    state_mgr = StateManager(settings.cache_db_path)
    snapshot_mgr = SnapshotManager(settings.snapshot_dir)
    scraper = LinkedinScraper(
        auth_file=settings.auth_state_path, headless=settings.headless
    )

    try:
        sheets = SheetsManager(settings)
        pending_targets = sheets.fetch_pending_targets()
        print(f"\n→ Found {len(pending_targets)} pending targets in Google Sheets")
    except Exception as e:
        print(f"\n⚠ Google Sheets unavailable ({e}). Falling back to manual mode.")
        url = input("Enter LinkedIn Profile URL: ").strip()
        if not url:
            print("No URL provided. Exiting.")
            return
        pending_targets = [{"LinkedIn URL": url, "Name": "Manual"}]
        sheets = None

    batch_results: list[dict[str, str]] = []

    for target in pending_targets:
        url = str(target.get("User Linkedin URL", "")).strip()
        company_url = str(target.get("Company Linkedin URL", "")).strip()
        name = str(target.get("Name", "Unknown")).strip()

        if not url:
            continue

        if not company_url:
            company_url = None

        result = await process_target(url, company_url, scraper, sender_context, state_mgr, snapshot_mgr)

        if result:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            batch_results.append({
                "user_linkedin_url": url,
                "company_linkedin_url": company_url if company_url else "",
                "name": name,
                "connection_note": result["connection_note"],
                "dm_message": result["dm_message"],
                "char_count": str(len(result["connection_note"])),
                "word_count": str(len(result["dm_message"].split())),
                "status": "Done",
                "processed_at": now,
            })

    if sheets and batch_results:
        print(f"\n→ Batch updating {len(batch_results)} results to Google Sheets...")
        sheets.batch_update_results(batch_results)
        print("  ✓ Sheets updated")

    print(f"\n{'='*60}")
    print(f"Pipeline complete. Processed {len(batch_results)} targets.")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())