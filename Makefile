.PHONY: test format run

run:
	uv run python -m cmd.client.main run

test:
	uv run pytest -sv

format:
	uv run ruff check . --fix
	uv run ruff format .