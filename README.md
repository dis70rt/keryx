# Keryx Outreach Agent

AI outreach automator. Extract info. Generate personalized message. 

## Workflow

### 1. Data Schema
`src/core/models.py`. Dataclasses for `TargetProfile`, `CompanyProfile`, `SenderContext`. 
`src/core/storage.py`. Save data to JSON. Embed Unix/human timestamp.

### 2. Manual Auth (Host OS)
Avoid bot ban. Save session cookies/storage. Run on host OS. Headful browser pop up.
```bash
uv run python src/tools/login.py
```
Login manual. Output go to `data/auth_state.json`.

### 3. Docker Scrape (Headless)
Container run Playwright stealth. Bind mount `data/` folder. Use `auth_state.json`. No new login.
```bash
docker compose up -d
docker compose exec agent python src/tools/scraper.py
```
Input LinkedIn URL. Script mimic human scroll. Click "See more" buttons. Extract raw DOM text for LLM parse.

### 4. Company Scrape
Extract company info (About, Posts).
```bash
docker compose exec agent python src/tools/company_scraper.py
```
Input Company LinkedIn URL. Output to `data/company_extracted.txt`.
