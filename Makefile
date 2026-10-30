.PHONY: test format run

test:
	uv run pytest -sv --ignore=benchmarks

format:
	uv run ruff check . --exclude benchmarks --fix
	uv run ruff format . --exclude benchmarks