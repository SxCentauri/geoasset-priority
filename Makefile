.PHONY: install test run serve clean
install:
	pip install -r requirements-dev.txt
test:
	python -m pytest -q
run:
	cd src && python -m geoasset.pipeline
serve:
	cd web && python -m http.server 8000
clean:
	rm -rf outputs/* data/processed/* web/data.js .pytest_cache
