# For the real index, set PYPI_URL to https://upload.pypi.org/legacy/
# like in `make publish PYPI_URL=https://upload.pypi.org/legacy/`
TEST_PYPI_URL=https://test.pypi.org/legacy/

VERSION := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/brikz/__init__.py)
PY_SOURCES := $(shell find src/brikz/ -name '*.py')
WHEEL := dist/brikz-$(VERSION)-py3-none-any.whl
SDIST := dist/brikz-$(VERSION).tar.gz

sync:
	uv sync

$(WHEEL) $(SDIST) &: $(PY_SOURCES) pyproject.toml
	uv build

build: $(WHEEL) $(SDIST)

test:
	uv run pytest

test-cov:
	rm -rf htmlcov/
	uv run pytest -q --cov --cov-report=html --cov-report=term-missing

test-cov-http:  test-cov
	python3 -m http.server 8000 -d htmlcov/

lint:
	uv run ruff check .
	uv run basedpyright

publish: clean build  # older dist files break the uplaod, so clean first
ifdef PYPI_URL
	@read -p "Publish to REAL $(PYPI_URL)? [y/N] " confirm && [ "$$confirm" = "y" ]
	uv publish --publish-url $(PYPI_URL) --token $(PYPI_API_TOKEN)
else
	@read -p "Publish to $(TEST_PYPI_URL)? [y/N] " confirm && [ "$$confirm" = "y" ]
	uv publish --publish-url $(TEST_PYPI_URL) --token $(TEST_PYPI_API_TOKEN)
endif

clean:
	rm -rf dist/
	rm -rf htmlcov/
	rm -f .coverage

clean-all:  clean
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	rm -rf .venv


.PHONY: init sync test test-cov lint build publish clean clean-all
