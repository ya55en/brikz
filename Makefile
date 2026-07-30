TEST_PYPI_URL=https://test.pypi.org/legacy/

init:
	uv venv

sync:
	uv sync

build:
	uv build

publish:
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
