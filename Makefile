# For the real index, set PYPI_URL to https://upload.pypi.org/legacy/
# like in `make publish PYPI_URL=https://upload.pypi.org/legacy/`
TEST_PYPI_URL=https://test.pypi.org/legacy/

VERSION := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/brikz/__init__.py)
PY_SOURCES := $(shell find src/brikz/ -name '*.py')
TEST_SOURCES := $(shell find tests/ -type f)
WHEEL := dist/brikz-$(VERSION)-py3-none-any.whl
SDIST := dist/brikz-$(VERSION).tar.gz

PYTEST_ARGS ?= -q

sync:
	uv sync

$(WHEEL) $(SDIST) &: $(PY_SOURCES) pyproject.toml README.md LICENSE
	uv build

build: $(WHEEL) $(SDIST)

test:
	uv run pytest $(PYTEST_ARGS)

htmlcov/index.html: $(PY_SOURCES) $(TEST_SOURCES) pyproject.toml
	rm -rf htmlcov/
	uv run pytest -q --cov --cov-report=html --cov-report=term-missing
	@echo "Go to file://$(PWD)/htmlcov/index.html"

test-cov:  htmlcov/index.html

test-cov-http:  test-cov
	uv run python3 -m http.server 8009 -b 127.0.0.1 -d htmlcov/

format:
	uv run ruff format .

lint:
	uv run ruff check $(LINT_FIX) .
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


.PHONY: sync build test test-cov test-cov-http format lint publish clean clean-all
