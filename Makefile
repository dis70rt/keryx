login:
	uv run python src/tools/login.py

up:
	docker compose up -d

down:
	docker compose down

scrape:
	docker compose exec agent python src/tools/scraper.py

scrape-company:
	docker compose exec agent python src/tools/company_scraper.py

build:
	docker compose build
