run:
	uv run python pipeline.py

login:
	uv run python src/tools/login.py

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

scrape:
	docker compose exec agent python pipeline.py
