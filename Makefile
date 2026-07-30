# For the real index, set PYPI_URL to https://upload.pypi.org/legacy/
# like in `make publish PYPI_URL=https://upload.pypi.org/legacy/`
TEST_PYPI_URL=https://test.pypi.org/legacy/

VERSION := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/brikz/__init__.py)
PY_SOURCES := $(shell find src/brikz/ -name '*.py')
WHEEL := dist/brikz-$(VERSION)-py3-none-any.whl
SDIST := dist/brikz-$(VERSION).tar.gz

init:
	uv venv

sync:
	uv sync

$(WHEEL) $(SDIST) &: $(PY_SOURCES) pyproject.toml
	uv build

build: $(WHEEL) $(SDIST)

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
	find . -type d -name __pycache__ -exec rm -rf {} +


.PHONY: init sync build publish clean
